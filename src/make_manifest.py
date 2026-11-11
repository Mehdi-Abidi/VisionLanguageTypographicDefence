"""
A6 — build the manifest: one CSV row per (image, cell, setting, defence), and
(optionally) actually generate the defended image files that don't exist yet.

Reads data/attack_set.csv (A2) and lists every rendered + defended version per
the naming convention confirmed directly from src/render.py and src/defences.py
(github.com/Mehdi-Abidi/VisionLanguageTypographicDefence, main, 2026-11-10):

    Raw render (render.py, no defence applied):
        images/{image_id}_{cell}_{setting}.png
        clean cell always uses setting "none": images/{image_id}_clean_none.png

    Defended version (defence != "none"):
        images/{image_id}_{cell}_{setting}_{defence}.png
        (this is exactly render.py's filename stem, with "_{defence}" appended —
        matches defences.save_ocr_inpaint's own naming for ocr_inpaint, confirmed
        by reading src/defences.py)

    defence == "none" is NOT a separate file — the manifest row just points at
    the raw render, same file render.py already wrote.

Manifest columns (agreed in ALL-1): image_id, cell, setting, defence, path

IMPORTANT: src/defences.py only exposes an in-memory apply_defence(array, name)
function (plus save_ocr_inpaint() for OCR specifically) — nothing in the repo
currently writes one defended PNG per manifest row for the classical defences.
That's why this script can generate them itself with --generate, rather than
just assuming the files are already there.

Usage:
    python src/make_manifest.py                                  # pilot: 20 tune images, 3 defences, CSV only
    python src/make_manifest.py --generate                       # also create every missing defended file
    python src/make_manifest.py --n 0 --split test --defences none  # full test set, no defence, CSV only
    python src/make_manifest.py --check-exists --images-dir images

Requires src/defences.py importable (same directory) for --generate. ocr_inpaint
additionally needs easyocr + torch installed — only imported lazily when that
defence is actually hit.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

# The 8 rendered versions (cells) every image gets, per A3 / render.py's CELLS.
CELLS = [
    "clean",
    "neutral_short",
    "neutral_long",
    "c_on",
    "i_on",
    "i_off",
    "c_off",
    "c_long",
]

DEFAULT_SETTING = "font16_high_object"


def render_path(image_id, cell, setting):
    """Path to the raw rendered file, before any defence. Matches render.py exactly."""
    cell_setting = "none" if cell == "clean" else setting
    return f"images/{image_id}_{cell}_{cell_setting}.png"


def defended_path(image_id, cell, setting, defence):
    """Path to the file after a defence is applied (defence != 'none')."""
    base = render_path(image_id, cell, setting)
    stem, ext = os.path.splitext(base)
    return f"{stem}_{defence}{ext}"


def resolved_path(image_id, cell, setting, defence):
    """What the manifest's 'path' column should say."""
    if defence == "none":
        return render_path(image_id, cell, setting)
    return defended_path(image_id, cell, setting, defence)


def load_attack_set(path, split, n):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if split and row.get("split") != split:
                continue
            rows.append(row)
    if n and n > 0:
        rows = rows[:n]
    return rows


def build_manifest(attack_set_rows, settings, defences):
    manifest_rows = []
    for row in attack_set_rows:
        image_id = row["image_id"]
        for setting in settings:
            for cell in CELLS:
                # clean only ever has one real "setting" (none) — don't repeat
                # it once per rendering setting if settings has more than one.
                if cell == "clean" and setting != settings[0]:
                    continue
                for defence in defences:
                    manifest_rows.append(
                        {
                            "image_id": image_id,
                            "cell": cell,
                            "setting": "none" if cell == "clean" else setting,
                            "defence": defence,
                            "path": resolved_path(image_id, cell, setting, defence),
                        }
                    )
    return manifest_rows


def generate_missing(manifest_rows, images_dir, skip_ocr=False):
    """Create any defended file (defence != 'none') that doesn't exist yet,
    using the real src/defences.py. Raw renders are NOT created here — those
    come from render.py (A3), run separately."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import defences  # noqa: E402  (local import: only needed for --generate)
    from PIL import Image

    made, skipped_missing_raw, skipped_existing, skipped_ocr = 0, 0, 0, 0

    for row in manifest_rows:
        if row["defence"] == "none":
            continue  # points at the raw render, nothing to generate

        out_path = Path(images_dir) / row["path"]
        if out_path.exists():
            skipped_existing += 1
            continue

        raw_path = Path(images_dir) / render_path(row["image_id"], row["cell"], row["setting"])
        if not raw_path.exists():
            print(f"  skip {out_path} — raw render missing: {raw_path}", file=sys.stderr)
            skipped_missing_raw += 1
            continue

        if row["defence"] == "ocr_inpaint":
            if skip_ocr:
                skipped_ocr += 1
                continue
            defences.save_ocr_inpaint(raw_path, out_path.parent)  # also writes the _mask.png
        else:
            arr = defences.load_rgb(raw_path)
            result = defences.apply_defence(arr, row["defence"])
            Image.fromarray(result).save(out_path)

        made += 1

    print(f"generated {made} files "
          f"({skipped_existing} already existed, {skipped_missing_raw} skipped — raw render missing"
          + (f", {skipped_ocr} ocr_inpaint skipped via --skip-ocr" if skip_ocr else "")
          + ")")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--attack-set", default="data/attack_set.csv", help="path to attack_set.csv")
    ap.add_argument("--split", default="tune", help="which split to pull images from (tune/test/spare), empty for all")
    ap.add_argument("--n", type=int, default=20, help="how many images to include (0 = all matching split)")
    ap.add_argument("--settings", default=DEFAULT_SETTING, help="comma-separated rendering settings")
    ap.add_argument(
        "--defences",
        default="none,blur_s2,ocr_inpaint",
        help="comma-separated defences (A6 pilot default: none,blur_s2,ocr_inpaint)",
    )
    ap.add_argument("--out", default="manifests/pilot.csv", help="where to write the manifest")
    ap.add_argument("--images-dir", default=".", help="root dir to resolve 'path' against")
    ap.add_argument("--check-exists", action="store_true", help="warn about any manifest row whose file is missing")
    ap.add_argument("--generate", action="store_true",
                     help="also create any missing defended file (needs the real src/defences.py + raw renders already on disk)")
    ap.add_argument("--skip-ocr", action="store_true", help="with --generate, skip ocr_inpaint rows (no easyocr/torch installed)")
    args = ap.parse_args()

    settings = [s.strip() for s in args.settings.split(",") if s.strip()]
    defences_list = [d.strip() for d in args.defences.split(",") if d.strip()]

    attack_set_rows = load_attack_set(args.attack_set, args.split, args.n)
    if not attack_set_rows:
        print(f"No rows found in {args.attack_set} for split={args.split!r}", file=sys.stderr)
        sys.exit(1)

    manifest_rows = build_manifest(attack_set_rows, settings, defences_list)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image_id", "cell", "setting", "defence", "path"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote {len(manifest_rows)} rows to {args.out} "
          f"({len(attack_set_rows)} images x {len(CELLS)} cells x {len(settings)} setting(s) x {len(defences_list)} defence(s))")

    if args.generate:
        generate_missing(manifest_rows, args.images_dir, skip_ocr=args.skip_ocr)

    if args.check_exists:
        missing = [row["path"] for row in manifest_rows if not (Path(args.images_dir) / row["path"]).exists()]
        if missing:
            print(f"\n{len(missing)} of {len(manifest_rows)} files are still missing, e.g.:", file=sys.stderr)
            for p in missing[:10]:
                print(f"  - {p}", file=sys.stderr)
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more", file=sys.stderr)
        else:
            print("All files present.")


if __name__ == "__main__":
    main()
