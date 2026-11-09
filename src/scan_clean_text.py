"""Run EasyOCR on every clean photo in the attack set and record any text already in it.

Photos are resized to the same 512 px short side the models see. Nothing in
attack_set.csv is changed. The output lists what was read so photos with text
can be swapped for spares by hand.

Usage:
    python src/scan_clean_text.py
    python src/scan_clean_text.py --sheet results/clean_text_flagged.png
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from defences import read_text
from render import load_photo, resize_short_side


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("data/attack_set.csv"))
    parser.add_argument("--cache", type=Path, default=Path("data/raw/val2017"))
    parser.add_argument("--out", type=Path, default=Path("data/clean_text_scan.csv"))
    parser.add_argument("--sheet", type=Path, default=Path("results/clean_text_flagged.png"))
    parser.add_argument("--min-letters", type=int, default=2)
    args = parser.parse_args()

    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results, flagged = [], []
    for k, row in enumerate(rows, 1):
        photo = load_photo(row["file_name"], args.cache)
        photo, _ = resize_short_side(photo, (0, 0, 0, 0))
        words = [w for w in read_text(np.asarray(photo))
                 if w["kept"] and sum(c.isalnum() for c in w["text"]) >= args.min_letters]
        has_text = bool(words)
        results.append({
            "image_id": row["image_id"],
            "split": row["split"],
            "category": row["category"],
            "has_text": int(has_text),
            "n_words": len(words),
            "max_confidence": max((w["confidence"] for w in words), default=0),
            "words": " | ".join(f"{w['text']} ({w['confidence']:.2f})" for w in words),
        })
        if has_text:
            flagged.append((row, photo, words))
        print(f"{k}/{len(rows)} {row['image_id']:>6} {row['split']:5s} {row['category']:14s} "
              + (results[-1]["words"] if has_text else "-"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    by_split = {}
    for r in results:
        by_split.setdefault(r["split"], [0, 0])
        by_split[r["split"]][0] += 1
        by_split[r["split"]][1] += r["has_text"]
    print("\nphotos with text, by split:", {s: f"{t} of {n}" for s, (n, t) in by_split.items()})
    print("saved", args.out)

    if flagged and args.sheet:
        tile, cols = 320, 5
        font = ImageFont.load_default(size=14)
        sheet = Image.new("RGB", (cols * tile, ((len(flagged) + cols - 1) // cols) * (tile + 40)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (row, photo, words) in enumerate(flagged):
            im = photo.copy()
            d = ImageDraw.Draw(im)
            for w in words:
                d.polygon([tuple(p) for p in w["box"]], outline=(255, 0, 0), width=4)
            im.thumbnail((tile, tile))
            x, y = (i % cols) * tile, (i // cols) * (tile + 40)
            sheet.paste(im, (x, y))
            label = f"{row['image_id']} {row['category']} ({row['split']})"
            read = ", ".join(w["text"] for w in words)[:44]
            draw.text((x + 4, y + im.height + 2), label, fill="black", font=font)
            draw.text((x + 4, y + im.height + 19), read, fill=(170, 0, 0), font=font)
        args.sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.sheet)
        print("saved", args.sheet)


if __name__ == "__main__":
    main()
