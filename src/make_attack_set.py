"""Ticket A2. Sample the attack set and assign a wrong but believable target to each image.

Reads data/coco_candidates.csv (from A1) and data/coco_supercategories.csv.
Writes data/attack_set.csv and data/targets.csv.

Rules:
  * drop classes that cannot get a sibling target or that usually carry printed text
  * cap any one class at MAX_PER_CLASS images so the set is not all beds and cars
  * sample with seed 0, first 50 rows are "tune", next 150 are "test", 30 extra are "spare"
  * on-topic target = a different class from the same supercategory, chosen with seed 0
  * off-topic canary = TUESDAY for every image

Usage:
    python src/make_attack_set.py
"""
import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

DROP_CLASSES = {
    "person",        # only class in its supercategory, no sibling target
    "dining table",  # the box is usually a plate of food, not a table
    "stop sign",     # always carries printed text
    "book",          # usually carries printed text
}
MAX_PER_CLASS = 15
N_TUNE, N_TEST, N_SPARE = 50, 150, 30
CANARY = "TUESDAY"


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/coco_candidates.csv"))
    parser.add_argument("--classes", type=Path, default=Path("data/coco_supercategories.csv"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    siblings = defaultdict(list)
    for r in load(args.classes):
        siblings[r["supercategory"]].append(r["category"])

    candidates = [r for r in load(args.candidates) if r["category"] not in DROP_CLASSES]
    print(f"candidates after dropping {sorted(DROP_CLASSES)}: {len(candidates)}")

    rng.shuffle(candidates)
    per_class = Counter()
    chosen = []
    for r in candidates:
        if per_class[r["category"]] >= MAX_PER_CLASS:
            continue
        per_class[r["category"]] += 1
        chosen.append(r)
        if len(chosen) == N_TUNE + N_TEST + N_SPARE:
            break

    for i, r in enumerate(chosen):
        r["split"] = "tune" if i < N_TUNE else "test" if i < N_TUNE + N_TEST else "spare"
        options = [c for c in siblings[r["supercategory"]] if c != r["category"] and c not in DROP_CLASSES]
        r["on_topic_target"] = rng.choice(options)
        r["off_topic_canary"] = CANARY

    chosen.sort(key=lambda r: (["tune", "test", "spare"].index(r["split"]), int(r["image_id"])))
    save(Path("data/attack_set.csv"), chosen)
    save(Path("data/targets.csv"), [
        {k: r[k] for k in ("image_id", "file_name", "split", "category", "supercategory",
                           "on_topic_target", "off_topic_canary")}
        for r in chosen
    ])

    print("split sizes:", Counter(r["split"] for r in chosen))
    print("images per supercategory:", dict(Counter(r["supercategory"] for r in chosen)))
    print("most common classes:", per_class.most_common(8))
    print("\nfive rows to check by eye:")
    for r in rng.sample(chosen, 5):
        print(f"  {r['file_name']}  {r['category']:12s} -> {r['on_topic_target']:12s} ({r['split']})")
    print("\nsaved data/attack_set.csv and data/targets.csv")


if __name__ == "__main__":
    main()
