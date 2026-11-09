"""Swap every attack photo that already contains text for a text-free photo of the same class.

Runs after make_attack_set.py and scan_clean_text.py. For each photo the scan flagged,
it shuffles the unused candidates of the same class with the seed "0-replace-<old id>",
runs EasyOCR on them in that order and takes the first one with no text. The new photo
keeps the old photo's split and gets its target with the same rule as A2.

Writes data/attack_set.csv, data/targets.csv, data/replacements.csv (old -> new) and
data/replacement_scan.csv (every candidate that was read, with what OCR found).

Usage:
    python src/replace_text_photos.py
"""
import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from defences import read_text
from make_attack_set import CONFUSABLE, DROP_CLASSES, MAX_PER_CLASS, load, save
from render import load_photo, resize_short_side

SPLIT_ORDER = ["tune", "test", "spare"]


def find_text(file_name: str, cache: Path, min_letters: int) -> list:
    photo, _ = resize_short_side(load_photo(file_name, cache), (0, 0, 0, 0))
    return [w for w in read_text(np.asarray(photo))
            if w["kept"] and sum(c.isalnum() for c in w["text"]) >= min_letters]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attack-set", type=Path, default=Path("data/attack_set.csv"))
    parser.add_argument("--scan", type=Path, default=Path("data/clean_text_scan.csv"))
    parser.add_argument("--candidates", type=Path, default=Path("data/coco_candidates.csv"))
    parser.add_argument("--classes", type=Path, default=Path("data/coco_supercategories.csv"))
    parser.add_argument("--cache", type=Path, default=Path("data/raw/val2017"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--min-letters", type=int, default=2)
    args = parser.parse_args()

    attack = load(args.attack_set)
    flagged_ids = {r["image_id"] for r in load(args.scan) if r["has_text"] == "1"}
    to_replace = [r for r in attack if r["image_id"] in flagged_ids]
    if not to_replace:
        print("no flagged photo is in the attack set, nothing to replace")
        return

    siblings = defaultdict(list)
    for r in load(args.classes):
        siblings[r["supercategory"]].append(r["category"])

    used = {r["image_id"] for r in attack}
    pool = [r for r in load(args.candidates) if r["category"] not in DROP_CLASSES and r["image_id"] not in used]
    per_class = Counter(r["category"] for r in attack if r["image_id"] not in flagged_ids)
    scanned = {}
    scan_log, replacements = [], []

    def text_in(candidate: dict) -> list:
        if candidate["image_id"] not in scanned:
            scanned[candidate["image_id"]] = find_text(candidate["file_name"], args.cache, args.min_letters)
            scan_log.append({"image_id": candidate["image_id"], "category": candidate["category"],
                             "has_text": int(bool(scanned[candidate["image_id"]])),
                             "words": " | ".join(f"{w['text']} ({w['confidence']:.2f})"
                                                 for w in scanned[candidate["image_id"]])})
        return scanned[candidate["image_id"]]

    to_replace.sort(key=lambda r: (SPLIT_ORDER.index(r["split"]), int(r["image_id"])))
    for old in to_replace:
        rng = random.Random(f"{args.seed}-replace-{old['image_id']}")
        same_class = [c for c in pool if c["category"] == old["category"]]
        rng.shuffle(same_class)
        family = [c for c in pool if c["supercategory"] == old["supercategory"] and c["category"] != old["category"]]
        rng.shuffle(family)

        new, tried, how = None, 0, "same class"
        for group, label in ((same_class, "same class"), (family, "same family")):
            for c in group:
                if label == "same family" and per_class[c["category"]] >= MAX_PER_CLASS:
                    continue
                tried += 1
                if not text_in(c):
                    new, how = c, label
                    break
            if new:
                break
        if new is None:
            raise RuntimeError(f"no text-free replacement for {old['image_id']} {old['category']}")

        pool.remove(new)
        per_class[new["category"]] += 1
        new = dict(new)
        new["split"] = old["split"]
        options = CONFUSABLE.get(new["category"]) or [
            c for c in siblings[new["supercategory"]] if c != new["category"] and c not in DROP_CLASSES]
        new["on_topic_target"] = random.Random(f"{args.seed}-{new['image_id']}").choice(options)
        new["off_topic_canary"] = old["off_topic_canary"]
        attack[attack.index(old)] = new
        replacements.append({"old_image_id": old["image_id"], "old_category": old["category"],
                             "split": old["split"], "new_image_id": new["image_id"],
                             "new_category": new["category"], "new_target": new["on_topic_target"],
                             "match": how, "candidates_read": tried})
        print(f"{old['split']:5s} {old['image_id']:>6} {old['category']:14s} -> {new['image_id']:>6} "
              f"{new['category']:14s} target {new['on_topic_target']:12s} ({how}, read {tried})")

    attack.sort(key=lambda r: (SPLIT_ORDER.index(r["split"]), int(r["image_id"])))
    save(args.attack_set, attack)
    save(Path("data/targets.csv"), [
        {k: r[k] for k in ("image_id", "file_name", "split", "category", "supercategory",
                           "on_topic_target", "off_topic_canary")} for r in attack])
    save(Path("data/replacements.csv"), replacements)
    save(Path("data/replacement_scan.csv"), scan_log)

    print(f"\nreplaced {len(replacements)} photos, read {len(scan_log)} candidates, "
          f"{sum(r['has_text'] for r in scan_log)} of them had text")
    print("split sizes:", dict(Counter(r["split"] for r in attack)))
    print("largest class:", Counter(r["category"] for r in attack).most_common(1))


if __name__ == "__main__":
    main()
