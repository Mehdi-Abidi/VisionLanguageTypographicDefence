"""
A6 — contact sheet: tile the 8 rendered versions of N images into one PNG,
one row per image, so you can eyeball the renderer's output for problems
(text outside the frame, box on the wrong object, unreadable neutral text,
wrong box size).

This only needs the RAW rendered files (no defence applied), same as the
task-board description: "tiles the 8 versions of one image in a row, N rows".

Usage:
    python src/contact_sheet.py                               # first 20 tune images, default setting
    python src/contact_sheet.py --n 20 --split tune
    python src/contact_sheet.py --ids 9914,42178 --out results/contact_sheet_check.png

NOTE: written from the file-naming convention in docs/README.md (no repo
access yet at time of writing — see the note at the top of make_manifest.py).
If a thumbnail is missing, the cell is rendered as a grey placeholder with a
red "MISSING" label instead of crashing, so you can still see what's there.
"""

import argparse
import csv
import os

from PIL import Image, ImageDraw, ImageFont

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
THUMB = 180       # thumbnail width/height in the sheet
LABEL_H = 22       # space for the cell-name / image-id label
PAD = 6


def render_path(image_id, cell, setting):
    if cell == "clean":
        return f"images/{image_id}_clean_none.png"
    return f"images/{image_id}_{cell}_{setting}.png"


def load_attack_set(path, split, n, ids):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if ids and row["image_id"] not in ids:
                continue
            if ids is None and split and row.get("split") != split:
                continue
            rows.append(row)
    if ids is None and n and n > 0:
        rows = rows[:n]
    return rows


def load_thumb(path, size):
    try:
        img = Image.open(path).convert("RGB")
        img.thumbnail((size, size))
        canvas = Image.new("RGB", (size, size), (235, 235, 235))
        canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
        return canvas, True
    except FileNotFoundError:
        canvas = Image.new("RGB", (size, size), (60, 60, 60))
        d = ImageDraw.Draw(canvas)
        d.text((8, size // 2 - 6), "MISSING", fill=(255, 80, 80))
        return canvas, False


def build_sheet(attack_set_rows, images_dir, setting, out_path):
    font = ImageFont.load_default()

    n_rows = len(attack_set_rows)
    n_cols = len(CELLS)
    id_col_w = 90

    sheet_w = id_col_w + n_cols * (THUMB + PAD)
    sheet_h = LABEL_H + n_rows * (THUMB + LABEL_H + PAD)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    for c, cell in enumerate(CELLS):
        x = id_col_w + c * (THUMB + PAD)
        draw.text((x + 4, 4), cell, fill=(0, 0, 0), font=font)

    missing_count = 0
    total_count = 0
    y = LABEL_H
    for row in attack_set_rows:
        image_id = row["image_id"]
        draw.text((4, y + THUMB // 2), f"id {image_id}", fill=(0, 0, 0), font=font)
        draw.text((4, y + THUMB // 2 + 12), row.get("category", ""), fill=(100, 100, 100), font=font)

        for c, cell in enumerate(CELLS):
            path = os.path.join(images_dir, render_path(image_id, cell, setting))
            thumb, found = load_thumb(path, THUMB)
            x = id_col_w + c * (THUMB + PAD)
            sheet.paste(thumb, (x, y))
            total_count += 1
            if not found:
                missing_count += 1

        y += THUMB + LABEL_H + PAD

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    sheet.save(out_path)
    return total_count, missing_count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--attack-set", default="data/attack_set.csv")
    ap.add_argument("--split", default="tune")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--ids", default=None, help="comma-separated image_ids instead of --split/--n")
    ap.add_argument("--setting", default=DEFAULT_SETTING)
    ap.add_argument("--images-dir", default=".", help="root dir the 'images/...' paths are relative to")
    ap.add_argument("--out", default="results/contact_sheet_pilot.png")
    args = ap.parse_args()

    ids = set(args.ids.split(",")) if args.ids else None
    rows = load_attack_set(args.attack_set, args.split, args.n, ids)
    if not rows:
        raise SystemExit(f"No rows found in {args.attack_set} for split={args.split!r} / ids={args.ids!r}")

    total, missing = build_sheet(rows, args.images_dir, args.setting, args.out)
    print(f"Wrote {args.out} ({len(rows)} images x {len(CELLS)} cells = {total} thumbnails, {missing} missing)")
    if missing:
        print("Some files were missing and rendered as grey MISSING placeholders — "
              "check --images-dir points at where the rendered PNGs actually live.")


if __name__ == "__main__":
    main()
