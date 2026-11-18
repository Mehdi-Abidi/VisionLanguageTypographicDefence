"""Ticket B9. The rendering grid for the defence-aware attacker search.

Takes the 50 tuning photos and the two cells B9 searches over, C-on and I-on, and renders them
under 36 settings: font size 16, 24 or 32, high or low contrast, DejaVu Sans Bold or the stylised
Comic Neue Bold, and the text written once, twice or three times, stacked in one box. Every
render then goes through the three defences B9 picks a setting for: blur sigma 2, JPEG 20 and
OCR-inpaint. The text always sits on the main object, as in the default rendering.

Settings are named font{px}_{contrast}_object_{font}_x{repeat}, for example
font24_low_object_comic_x2. Paths follow make_manifest.py.

Writes manifests/attacker_search.csv (10,800 rows, defended images only). With --images it also
renders the images and applies the defences.

Usage:
    python src/make_attacker_set.py
    python src/make_attacker_set.py --images --out /kaggle/working
"""
import argparse
import csv
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_manifest as mm

ROOT = Path(__file__).resolve().parents[1]
FONTS = {"dejavu": None, "comic": str(ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf")}
SIZES = (16, 24, 32)
CONTRASTS = ("high", "low")
REPEATS = (1, 2, 3)
CELLS = ("c_on", "i_on")
DEFENCES = ("blur_s2", "jpeg_q20", "ocr_inpaint")


def setting_name(size: int, contrast: str, font: str, repeat: int) -> str:
    return f"font{size}_{contrast}_object_{font}_x{repeat}"


def grid() -> list:
    return [{"setting": setting_name(s, c, f, r), "size": s, "contrast": c, "font": f, "repeat": r}
            for s, c, f, r in itertools.product(SIZES, CONTRASTS, FONTS, REPEATS)]


def tune_photos(attack_csv: Path) -> list:
    with open(attack_csv, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["split"] == "tune"]


def manifest_rows(photos: list) -> list:
    return [{"image_id": p["image_id"], "cell": cell, "setting": g["setting"], "defence": d,
             "path": mm.resolved_path(p["image_id"], cell, g["setting"], d)}
            for p in photos for cell in CELLS for g in grid() for d in DEFENCES]


def make_images(photos: list, rows: list, out: Path, cache: Path, settings: list = None) -> None:
    import render as R

    settings = grid() if settings is None else settings
    (out / "images").mkdir(parents=True, exist_ok=True)
    for k, p in enumerate(photos, 1):
        photo = R.load_photo(p["file_name"], cache)
        box = tuple(float(p[c]) for c in ("box_x", "box_y", "box_w", "box_h"))
        photo, box = R.resize_short_side(photo, box)
        for g in settings:
            texts = R.cell_texts(p, g["size"], 0)
            for cell in CELLS:
                path = out / mm.render_path(p["image_id"], cell, g["setting"])
                if not path.exists():
                    text, size_like = texts[cell]
                    R.render(photo, text, g["size"], g["contrast"], "object", box, size_like,
                             font_path=FONTS[g["font"]], repeat=g["repeat"]).save(path)
        if k % 10 == 0 or k == len(photos):
            print(f"{k}/{len(photos)} photos rendered")
    mm.generate_missing(rows, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attack-set", type=Path, default=Path("data/attack_set.csv"))
    parser.add_argument("--manifest-out", type=Path, default=Path("manifests/attacker_search.csv"))
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("."))
    parser.add_argument("--cache", type=Path, default=Path("data/raw/val2017"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    photos = tune_photos(args.attack_set)
    photos = photos[:args.limit] if args.limit else photos
    rows = manifest_rows(photos)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(photos)} tune photos x {len(CELLS)} cells x {len(grid())} settings x {len(DEFENCES)} defences "
          f"= {len(rows)} manifest rows")
    if args.images:
        make_images(photos, rows, args.out, args.cache)


if __name__ == "__main__":
    main()
