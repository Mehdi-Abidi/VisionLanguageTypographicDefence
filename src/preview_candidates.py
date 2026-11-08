"""Make a contact sheet of candidate images with their largest-object box drawn.

Fetches the photos from the COCO server, so no local image download is needed.

Usage:
    python src/preview_candidates.py                 # 24 random images, seed 0
    python src/preview_candidates.py --n 48 --seed 3
    python src/preview_candidates.py --supercategory animal
"""
import argparse
import csv
import io
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COCO_URL = "http://images.cocodataset.org/val2017/{}"
TILE = 300


def fetch(file_name: str) -> Image.Image:
    with urllib.request.urlopen(COCO_URL.format(file_name), timeout=30) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("data/coco_candidates.csv"))
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--supercategory", default=None)
    parser.add_argument("--out", type=Path, default=Path("results/preview_candidates.png"))
    args = parser.parse_args()

    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.supercategory:
        rows = [r for r in rows if r["supercategory"] == args.supercategory]
    random.seed(args.seed)
    rows = random.sample(rows, min(args.n, len(rows)))

    cols = 6
    sheet_rows = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TILE, sheet_rows * TILE), "white")
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    for i, r in enumerate(rows):
        im = fetch(r["file_name"])
        scale = TILE / max(im.width, im.height)
        im = im.resize((int(im.width * scale), int(im.height * scale)))
        draw = ImageDraw.Draw(im)
        x, y, w, h = (float(r[k]) * scale for k in ("box_x", "box_y", "box_w", "box_h"))
        draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
        label = f'{r["category"]} {float(r["box_area_fraction"]):.0%}'
        if "on_topic_target" in r:
            label = f'{r["category"]} -> {r["on_topic_target"]} ({r["split"]})'
        draw.rectangle([0, 0, 8 + draw.textlength(label, font=font), 22], fill="black")
        draw.text((4, 3), label, fill="white", font=font)
        sheet.paste(im, ((i % cols) * TILE, (i // cols) * TILE))
        print(f"{i + 1}/{len(rows)} {r['file_name']} {label}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()
