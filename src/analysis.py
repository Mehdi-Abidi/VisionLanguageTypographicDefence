"""Ticket C8. Tidy table of every scored row in runs/, plus the two plots.

    tidy()                  -> one row per answer: image_id, cell, setting, defence, model, split, success, correct
    plot_asr_by_cell(df)    -> ASR per cell per model at the default rendering, no defence, Wilson 95% intervals
    plot_asr_by_font(df)    -> ASR against font size, one line per attack cell, one panel per model
Only the 150 `test` photos are used for plots (pre-registration: every reported number comes from test).
"""
from pathlib import Path

import matplotlib
import pandas as pd

from score import is_correct, is_success
from stats import wilson

ROOT = Path(__file__).resolve().parent.parent
ATTACK_CELLS = ["c_on", "i_on", "c_long", "i_off", "c_off"]
ON_TOPIC = {"neutral_short", "c_on", "i_on", "c_long"}  # the rest aim at the off-topic canary
DEFAULT = "font16_high_object"


def tidy(runs=ROOT / "runs", data=ROOT / "data") -> pd.DataFrame:
    t = pd.read_csv(data / "attack_set.csv")[["image_id", "split", "category", "on_topic_target", "off_topic_canary"]]
    # utility_*.jsonl (TextVQA, B8) have their own prompts and are scored elsewhere.
    d = pd.concat([pd.read_json(f, lines=True) for f in sorted(Path(runs).glob("*.jsonl")) if not f.name.startswith(("utility", "pilot"))])
    d = d.merge(t, on="image_id", how="left", validate="m:1")
    assert d.split.notna().all(), "run rows with an image_id not in attack_set.csv"
    d = d.drop_duplicates(["image_id", "cell", "setting", "defence", "model"])
    target = d.on_topic_target.where(d.cell.isin(ON_TOPIC), d.off_topic_canary)
    d["success"] = [int(is_success(o, x)) for o, x in zip(d.output, target)]
    d["correct"] = [int(is_correct(o, c)) for o, c in zip(d.output, d.category)]
    return d[["image_id", "cell", "setting", "defence", "model", "split", "success", "correct"]]


def _bar(ax, rows, x, label=None):
    n = len(rows)
    r, lo, hi = wilson(int(rows.success.sum()), n)
    ax.errorbar(x, r, yerr=[[r - lo], [hi - r]], fmt="o", capsize=3, color=label)


def plot_asr_by_cell(df):
    import matplotlib.pyplot as plt
    d = df[(df.split == "test") & (df.setting == DEFAULT) & (df.defence == "none")]
    models = sorted(d.model.unique())
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 3.5), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        for i, c in enumerate(["neutral_short", "neutral_long"] + ATTACK_CELLS):
            _bar(ax, d[(d.model == m) & (d.cell == c)], i)
        ax.set_xticks(range(7), ["neutral_short", "neutral_long"] + ATTACK_CELLS, rotation=60, ha="right")
        ax.set_title(m)
    axes[0][0].set_ylabel("attack success rate")
    fig.tight_layout()
    return fig


def plot_asr_by_font(df):
    import matplotlib.pyplot as plt
    d = df[(df.split == "test") & (df.defence == "none") & (df.setting.str.endswith("high_object"))].copy()
    d["font"] = d.setting.str.extract(r"font(\d+)").astype(int)
    models = sorted(d.model.unique())
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 3.5), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        for c in ATTACK_CELLS:
            pts = []
            for f, g in d[(d.model == m) & (d.cell == c)].groupby("font"):
                r, lo, hi = wilson(int(g.success.sum()), len(g))
                pts.append((f, r, lo, hi))
            if pts:
                f, r, lo, hi = zip(*sorted(pts))
                ax.errorbar(f, r, yerr=[[a - b for a, b in zip(r, lo)], [b - a for a, b in zip(r, hi)]], marker="o", capsize=3, label=c)
        ax.set_xlabel("font size (px)")
        ax.set_title(m)
    axes[0][0].set_ylabel("attack success rate")
    axes[0][-1].legend()
    fig.tight_layout()
    return fig
