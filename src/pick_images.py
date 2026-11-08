"""Ticket A1. Pick COCO val2017 images that have one dominant object.

Reads instances_val2017.json, finds the largest object box in each image,
keeps the image if that box covers at least THRESHOLD of the image area,
and writes data/coco_candidates.csv.

Usage:
    python src/pick_images.py --annotations data/raw/coco_annotations/annotations/instances_val2017.json
    python src/pick_images.py --threshold 0.15
"""
import argparse
import csv
import json
from pathlib import Path


def pick(annotations_path: Path, threshold: float) -> list[dict]:
    with open(annotations_path, encoding="utf-8") as f:
        coco = json.load(f)

    categories = {c["id"]: c for c in coco["categories"]}
    images = {im["id"]: im for im in coco["images"]}

    largest = {}
    for ann in coco["annotations"]:
        if ann.get("iscrowd", 0):
            continue
        w, h = ann["bbox"][2], ann["bbox"][3]
        area = w * h
        best = largest.get(ann["image_id"])
        if best is None or area > best["area"]:
            largest[ann["image_id"]] = {"area": area, "ann": ann}

    rows = []
    for image_id, best in largest.items():
        im = images[image_id]
        fraction = best["area"] / (im["width"] * im["height"])
        if fraction < threshold:
            continue
        cat = categories[best["ann"]["category_id"]]
        x, y, w, h = best["ann"]["bbox"]
        rows.append({
            "image_id": image_id,
            "file_name": im["file_name"],
            "width": im["width"],
            "height": im["height"],
            "category": cat["name"],
            "supercategory": cat["supercategory"],
            "box_x": round(x, 1),
            "box_y": round(y, 1),
            "box_w": round(w, 1),
            "box_h": round(h, 1),
            "box_area_fraction": round(fraction, 4),
        })
    rows.sort(key=lambda r: r["image_id"])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotations", type=Path,
                        default=Path("data/raw/coco_annotations/annotations/instances_val2017.json"))
    parser.add_argument("--threshold", type=float, default=0.20,
                        help="minimum share of the image covered by the largest box (default 0.20)")
    parser.add_argument("--out", type=Path, default=Path("data/coco_candidates.csv"))
    args = parser.parse_args()

    rows = pick(args.annotations, args.threshold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"threshold {args.threshold:.2f}: {len(rows)} images kept -> {args.out}")
    if len(rows) < 400:
        print("fewer than 400. Re-run with --threshold 0.15 and note it in the README.")

    by_super = {}
    for r in rows:
        by_super[r["supercategory"]] = by_super.get(r["supercategory"], 0) + 1
    for name, n in sorted(by_super.items(), key=lambda kv: -kv[1]):
        print(f"  {name:12s} {n}")

if __name__ == "__main__":
    main()
