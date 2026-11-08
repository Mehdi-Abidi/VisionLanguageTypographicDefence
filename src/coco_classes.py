"""Ticket A2, step 3. Write the table of COCO supercategories and their classes.

Reads the category list from instances_val2017.json so nothing is typed by hand.

Usage:
    python src/coco_classes.py
"""
import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path,
                        default=Path("data/raw/coco_annotations/annotations/instances_val2017.json"))
    parser.add_argument("--out", type=Path, default=Path("data/coco_supercategories.csv"))
    args = parser.parse_args()

    with open(args.annotations, encoding="utf-8") as f:
        categories = json.load(f)["categories"]

    rows = sorted(({"supercategory": c["supercategory"], "category": c["name"], "coco_id": c["id"]}
                   for c in categories), key=lambda r: (r["supercategory"], r["coco_id"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["supercategory", "category", "coco_id"])
        w.writeheader()
        w.writerows(rows)

    groups = {}
    for r in rows:
        groups.setdefault(r["supercategory"], []).append(r["category"])
    for name, classes in groups.items():
        print(f"{name:12s} ({len(classes):2d}): {', '.join(classes)}")
    print("saved", args.out)


if __name__ == "__main__":
    main()
