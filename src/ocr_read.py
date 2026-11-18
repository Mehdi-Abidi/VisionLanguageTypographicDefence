"""A9. For every attacked image in the rendering sweep (no defence), run EasyOCR
and record whether it read the row's target word (or canary), within edit distance 1.

EasyOCR returns lines, such as "Say cat" or "This is a cat, not a dog", so each kept line is split
into words with score.words, and the target is compared with every run of as many words as it has,
or one fewer or one more. So "hot dog" matches across two detections, and also when read as "hotdog".

Scope: manifest rows with defence == 'none', and cell in the five real attack
cells (c_on, i_on, i_off, c_off, c_long). Clean has no text, and the two
neutral controls have scrambled random text with no fixed "target" to match
against, so they are left out of the match logic (same reasoning the ticket
implies by always talking about "the target word").

Usage:
    python src/ocr_read.py --manifest manifests/full.csv --targets data/targets.csv \
        --images-root /tmp/pg_root --out results/ocr_read.csv
"""
import argparse
from pathlib import Path

import pandas as pd
from rapidfuzz.distance import Levenshtein

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from defences import load_rgb, read_text
from score import words as score_words

ATTACK_CELLS = {"c_on": "on_topic_target", "i_on": "on_topic_target", "c_long": "on_topic_target",
                "i_off": "off_topic_canary", "c_off": "off_topic_canary"}


def expected_word(row: pd.Series) -> str:
    return row[ATTACK_CELLS[row["cell"]]]


def best_match(words: list, target: str) -> tuple:
    """(ocr_read, ocr_confidence) for the run of read words closest to target by edit distance.
    The confidence is the lowest of the detections the run spans. (0, 0.0) if nothing was kept."""
    tokens = [(w, d["confidence"]) for d in words if d["kept"] for w in score_words(d["text"])]
    goal = " ".join(score_words(target))
    n = max(1, len(goal.split()))
    best = None
    for size in sorted({max(1, n - 1), n, n + 1}):
        for k in range(len(tokens) - size + 1):
            run = tokens[k:k + size]
            dist = Levenshtein.distance(" ".join(w for w, _ in run), goal)
            if best is None or dist < best[0]:
                best = (dist, min(c for _, c in run))
    if best is None:
        return 0, 0.0
    dist, confidence = best
    return int(dist <= 1), confidence


def read_words(words: list) -> str:
    return " | ".join(d["text"] for d in words if d["kept"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("manifests/full.csv"))
    parser.add_argument("--targets", type=Path, default=Path("data/targets.csv"))
    parser.add_argument("--images-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("results/ocr_read.csv"))
    parser.add_argument("--limit", type=int, default=0, help="stop after N rows, 0 for all")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest)
    targets = pd.read_csv(args.targets).set_index("image_id")

    rows = manifest[(manifest["defence"] == "none") & (manifest["cell"].isin(ATTACK_CELLS))]
    rows = rows.reset_index(drop=True)
    if args.limit:
        rows = rows.iloc[:args.limit]

    out_rows = []
    for k, row in rows.iterrows():
        target_row = targets.loc[row["image_id"]]
        target = target_row[ATTACK_CELLS[row["cell"]]]
        image = load_rgb(args.images_root / row["path"])
        words = read_text(image)
        ocr_read, confidence = best_match(words, target)
        out_rows.append({"image_id": row["image_id"], "cell": row["cell"], "setting": row["setting"],
                          "ocr_read": ocr_read, "ocr_confidence": confidence, "ocr_text": read_words(words)})
        if (k + 1) % 200 == 0 or k + 1 == len(rows):
            print(f"{k + 1}/{len(rows)}")

    out_df = pd.DataFrame(out_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"wrote {len(out_df)} rows to {args.out}")
    print(f"ocr_read rate: {out_df['ocr_read'].mean():.3f}")


if __name__ == "__main__":
    main()
