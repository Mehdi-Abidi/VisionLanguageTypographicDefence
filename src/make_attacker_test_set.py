"""Ticket B10. The attacker settings chosen in B9 on the 150 test photos.

Reads configs/attacker.yaml, written by pick_attacker.py, which names one rendering setting per
defence. For every test photo, C-on and I-on are rendered in each chosen setting, and each render
is run through the defence it was chosen for and also left undefended, so the drop the defence
causes can be measured on the same images. If two defences chose the same setting, its
undefended row appears once.

Writes manifests/attacker_test.csv. With --images it also renders the images and applies the
defences, the same way make_attacker_set.py does for B9.

Usage:
    python src/make_attacker_test_set.py
    python src/make_attacker_test_set.py --images --out /kaggle/working
"""
import argparse
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_manifest as mm
from make_attacker_set import CELLS, DEFENCES, grid, make_images


def chosen_settings(config_path: Path) -> dict:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    names = {g["setting"] for g in grid()}
    chosen = {d: config["defences"][d]["setting"] for d in DEFENCES}
    unknown = sorted(set(chosen.values()) - names)
    assert not unknown, f"settings not in the B9 grid: {unknown}"
    return chosen


def test_photos(attack_csv: Path) -> list:
    with open(attack_csv, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["split"] == "test"]


def manifest_rows(photos: list, chosen: dict) -> list:
    settings = list(dict.fromkeys(chosen[d] for d in DEFENCES))
    rows = []
    for p in photos:
        for cell in CELLS:
            for s in settings:
                for d in ("none",) + tuple(d for d in DEFENCES if chosen[d] == s):
                    rows.append({"image_id": p["image_id"], "cell": cell, "setting": s, "defence": d,
                                 "path": mm.resolved_path(p["image_id"], cell, s, d)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attack-set", type=Path, default=Path("data/attack_set.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/attacker.yaml"))
    parser.add_argument("--manifest-out", type=Path, default=Path("manifests/attacker_test.csv"))
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("."))
    parser.add_argument("--cache", type=Path, default=Path("data/raw/val2017"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    chosen = chosen_settings(args.config)
    photos = test_photos(args.attack_set)
    photos = photos[:args.limit] if args.limit else photos
    rows = manifest_rows(photos, chosen)
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for d in DEFENCES:
        print(f"{d}: {chosen[d]}")
    print(f"{len(photos)} test photos, {len(rows)} manifest rows")
    if args.images:
        settings = [g for g in grid() if g["setting"] in set(chosen.values())]
        make_images(photos, rows, args.out, args.cache, settings)


if __name__ == "__main__":
    main()
