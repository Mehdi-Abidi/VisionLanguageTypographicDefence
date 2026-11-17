"""Ticket B9, step 4 and 5. Pick the best rendering setting for each defence.

Reads the B9 answers of the two smaller models, scores each one with score.py against the
photo's on-topic target, and for each defence takes the setting with the highest attack success
over both models, both cells and all 50 tuning photos (200 answers per setting). A tie goes to the
setting that comes first in the grid of make_attacker_set.py: smaller font, high contrast,
DejaVu, fewer repeats, so the least visible of the equally good settings wins.

Writes configs/attacker.yaml with one setting per defence, and results/attacker_search_scores.csv
with the success rate of every setting under every defence, per model and in total.

Usage:
    python src/pick_attacker.py
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_attacker_set import CELLS, DEFENCES, grid
from score import label

MODELS = ("smolvlm2-2b", "qwen3-vl-4b")
BASELINE = "font16_high_object_dejavu_x1"


def load_runs(paths: list) -> pd.DataFrame:
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return pd.DataFrame(rows)


def score(runs: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    target = targets.set_index("image_id")["on_topic_target"]
    runs = runs.copy()
    runs["success"] = [label(str(o), target[int(i)]) == "success" for o, i in zip(runs["output"], runs["image_id"])]
    return runs


def table(scored: pd.DataFrame) -> pd.DataFrame:
    by_model = scored.pivot_table(index=["defence", "setting"], columns="model", values="success", aggfunc="mean")
    by_model.columns = [f"success_{m}" for m in by_model.columns]
    total = scored.groupby(["defence", "setting"])["success"].agg(success="mean", answers="size")
    out = total.join(by_model).reset_index()
    order = {g["setting"]: k for k, g in enumerate(grid())}
    out["grid_order"] = out["setting"].map(order)
    return out.sort_values(["defence", "grid_order"]).reset_index(drop=True)


def choose(scores: pd.DataFrame, scored: pd.DataFrame) -> dict:
    settings = {g["setting"]: g for g in grid()}
    chosen = {}
    for defence in DEFENCES:
        d = scores[scores["defence"] == defence]
        best = d.sort_values(["success", "grid_order"], ascending=[False, True]).iloc[0]
        g = settings[best["setting"]]
        rows = scored[(scored["defence"] == defence) & (scored["setting"] == best["setting"])]
        base = d[d["setting"] == BASELINE]["success"]
        chosen[defence] = {
            "setting": g["setting"], "font_size": g["size"], "contrast": g["contrast"], "font": g["font"],
            "repeat": g["repeat"], "success": round(float(best["success"]), 4), "answers": int(best["answers"]),
            "success_by_model": {m: round(float(v), 4) for m, v in rows.groupby("model")["success"].mean().items()},
            "success_by_cell": {c: round(float(v), 4) for c, v in rows.groupby("cell")["success"].mean().items()},
            "default_rendering_success": round(float(base.iloc[0]), 4) if len(base) else None,
        }
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", type=Path,
                        default=[Path(f"runs/attacker_search_{m}.jsonl") for m in MODELS])
    parser.add_argument("--targets", type=Path, default=Path("data/targets.csv"))
    parser.add_argument("--out", type=Path, default=Path("configs/attacker.yaml"))
    parser.add_argument("--table", type=Path, default=Path("results/attacker_search_scores.csv"))
    args = parser.parse_args()

    scored = score(load_runs(args.runs), pd.read_csv(args.targets))
    scores = table(scored)
    chosen = choose(scores, scored)
    args.table.parent.mkdir(parents=True, exist_ok=True)
    scores.drop(columns="grid_order").to_csv(args.table, index=False, lineterminator="\n")
    config = {
        "search": {"photos": "the 50 tune photos", "cells": list(CELLS), "models": sorted(scored["model"].unique()),
                   "settings_tried": len(grid()), "rule": "highest attack success after the defence, ties to the "
                   "first setting in the grid (smaller font, high contrast, DejaVu, fewer repeats)"},
        "defences": chosen,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    for defence, c in chosen.items():
        print(f"{defence}: {c['setting']}, success {c['success']:.1%} (default rendering {c['default_rendering_success']:.1%})")
    print(f"wrote {args.out} and {args.table}")


if __name__ == "__main__":
    main()
