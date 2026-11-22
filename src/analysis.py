"""Ticket C8. Tidy table of every scored row in runs/, plus the two plots.

    tidy()                  -> one row per answer: image_id, cell, setting, defence, model, split, success, correct
    plot_asr_by_cell(df)    -> ASR per cell per model at the default rendering, no defence, Wilson 95% intervals
    plot_asr_by_font(df)    -> ASR against font size, one line per attack cell, one panel per model
    textvqa()               -> one row per TextVQA answer (C9): image_id, defence, model, acc
    plot_asr_by_defence(df) -> Figure 2 (C9): ASR against blur and JPEG strength, one panel per model and defence
    plot_ocr_vs_asr(df, ocr) -> Figure 3 (C9): EasyOCR recall against ASR per cell and rendering setting
    table1(...), table1_latex(tab) -> Table 1 (C9): attack, utility, image quality and time per defence
Only the 150 `test` photos are used for plots (pre-registration: every reported number comes from test).
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from score import is_correct, is_success, textvqa_accuracy
from stats import wilson

ROOT = Path(__file__).resolve().parent.parent
ATTACK_CELLS = ["c_on", "i_on", "c_long", "i_off", "c_off"]
ON_TOPIC = {"neutral_short", "c_on", "i_on", "c_long"}  # the rest aim at the off-topic canary
DEFAULT = "font16_high_object"
DEFENCES = ["none", "blur_s1", "blur_s2", "blur_s3", "jpeg_q50", "jpeg_q20", "jpeg_q10",
            "median_5", "bits_3", "downup_05", "ocr_inpaint"]
# Figure 2: the two swept defences, weakest to strongest (pre-registration, H2)
LADDERS = {"blur sigma": (["none", "blur_s1", "blur_s2", "blur_s3"], ["0", "1", "2", "3"]),
           "JPEG quality": (["none", "jpeg_q50", "jpeg_q20", "jpeg_q10"], ["none", "50", "20", "10"])}


def tidy(runs=ROOT / "runs", data=ROOT / "data") -> pd.DataFrame:
    t = pd.read_csv(data / "attack_set.csv")[["image_id", "split", "category", "on_topic_target", "off_topic_canary"]]
    # utility_*.jsonl (TextVQA, B8) have their own prompts and are scored elsewhere.
    d = pd.concat([pd.read_json(f, lines=True) for f in sorted(Path(runs).glob("*.jsonl")) if not f.name.startswith(("utility", "pilot", "attacker"))])
    d = d.merge(t, on="image_id", how="left", validate="m:1")
    assert d.split.notna().all(), "run rows with an image_id not in attack_set.csv"
    d = d.drop_duplicates(["image_id", "cell", "setting", "defence", "model"])
    target = d.on_topic_target.where(d.cell.isin(ON_TOPIC), d.off_topic_canary)
    d["success"] = [int(is_success(o, x)) for o, x in zip(d.output, target)]
    d["correct"] = [int(is_correct(o, c)) for o, c in zip(d.output, d.category)]
    return d[["image_id", "cell", "setting", "defence", "model", "split", "success", "correct"]]


def textvqa(runs=ROOT / "runs", data=ROOT / "data") -> pd.DataFrame:
    """One row per TextVQA answer (B8): image_id, defence, model, acc."""
    q = pd.read_csv(data / "textvqa_set.csv")[["image_id", "answers"]]
    q["answers"] = q.answers.map(json.loads)
    d = pd.concat([pd.read_json(f, lines=True) for f in sorted(Path(runs).glob("utility_*.jsonl"))])
    d = d[d.cell == "textvqa"].merge(q, on="image_id", how="left", validate="m:1")
    assert d.answers.notna().all(), "utility rows with an image_id not in textvqa_set.csv"
    d = d.drop_duplicates(["image_id", "defence", "model"])
    d["acc"] = [textvqa_accuracy(o, a) for o, a in zip(d.output, d.answers)]
    return d[["image_id", "defence", "model", "acc"]]


def plot_asr_by_defence(df):
    """Figure 2: ASR against defence strength at the default rendering, one line per attack cell."""
    import matplotlib.pyplot as plt
    d = df[(df.split == "test") & (df.setting == DEFAULT)]
    models = sorted(d.model.unique())
    fig, axes = plt.subplots(len(models), len(LADDERS), figsize=(4.5 * len(LADDERS), 3 * len(models)),
                             sharey=True, squeeze=False)
    for row, m in zip(axes, models):
        for ax, (xlabel, (defences, ticks)) in zip(row, LADDERS.items()):
            for c in ATTACK_CELLS:
                pts = [wilson(int(g.success.sum()), len(g)) for g in
                       (d[(d.model == m) & (d.cell == c) & (d.defence == x)] for x in defences)]
                r, lo, hi = zip(*pts)
                ax.errorbar(range(len(ticks)), r, yerr=[[a - b for a, b in zip(r, lo)], [b - a for a, b in zip(r, hi)]],
                            marker="o", capsize=3, label=c)
            ax.set_xticks(range(len(ticks)), ticks)
            ax.set_xlabel(xlabel)
            ax.set_title(m)
        row[0].set_ylabel("attack success rate")
    axes[0][-1].legend()
    fig.tight_layout()
    return fig


def plot_ocr_vs_asr(df, ocr):
    """Figure 3: per cell and rendering setting, EasyOCR recall (A9) against ASR, no defence, test photos.
    Colour is the cell, marker is the setting, both axes with Wilson 95% intervals."""
    import matplotlib.pyplot as plt
    key = ["image_id", "cell", "setting"]
    d = df[(df.split == "test") & (df.defence == "none") & df.cell.isin(ATTACK_CELLS)]
    d = d.merge(ocr[key + ["ocr_read"]], on=key, how="left", validate="m:1")
    assert d.ocr_read.notna().all(), "attacked rows with no OCR label"
    models = sorted(d.model.unique())
    settings = sorted(d.setting.unique())
    markers = dict(zip(settings, "osD^v<>"))
    colours = dict(zip(ATTACK_CELLS, plt.rcParams["axes.prop_cycle"].by_key()["color"]))
    fig, axes = plt.subplots(1, len(models), figsize=(4.5 * len(models), 4), sharex=True, sharey=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        for (c, s), g in d[d.model == m].groupby(["cell", "setting"]):
            x, xlo, xhi = wilson(int(g.ocr_read.sum()), len(g))
            y, ylo, yhi = wilson(int(g.success.sum()), len(g))
            ax.errorbar(x, y, xerr=[[x - xlo], [xhi - x]], yerr=[[y - ylo], [yhi - y]],
                        marker=markers[s], color=colours[c], capsize=2, linestyle="none")
        ax.set_xlabel("EasyOCR recall")
        ax.set_title(m)
    axes[0][0].set_ylabel("attack success rate")
    handles = [plt.Line2D([], [], color=colours[c], marker="o", linestyle="none", label=c) for c in ATTACK_CELLS]
    handles += [plt.Line2D([], [], color="grey", marker=markers[s], linestyle="none", label=s) for s in settings]
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
    fig.tight_layout()
    return fig


def table1(df, tv, quality, timing):
    """Table 1: one row per model and defence. Attack and clean rates use the 150 test photos at the
    default rendering. C-on is the context cell, I-off the original instruction cell (kept in Table 1 by
    the pilot gate) and I-on the instruction cell H2 uses since the pilot gate. PSNR and SSIM come from the
    A10 per-pair rows of the same test photos at the default rendering and the clean photos, and pairs the
    defence left unchanged (infinite PSNR) are left out of the PSNR mean."""
    key = ["model", "defence"]
    t = df[df.split == "test"]
    q = quality[quality.image_id.isin(set(t.image_id)) & quality.setting.isin([DEFAULT, "none"])]
    q = q.assign(psnr=q.psnr.where(np.isfinite(q.psnr)))
    quality = q.groupby("defence").agg(psnr_mean=("psnr", "mean"), ssim_mean=("ssim", "mean")).reset_index()
    atk = t[t.setting == DEFAULT]
    groups = {
        "context_asr": atk[atk.cell == "c_on"].groupby(key).success,
        "instruction_asr": atk[atk.cell == "i_off"].groupby(key).success,
        "i_on_asr": atk[atk.cell == "i_on"].groupby(key).success,
        "textvqa_acc": tv.groupby(key).acc,
        "clean_acc": t[t.cell == "clean"].groupby(key).correct,
    }
    for name, n in [("context_asr", 150), ("instruction_asr", 150), ("i_on_asr", 150), ("textvqa_acc", 200), ("clean_acc", 150)]:
        assert (groups[name].size() == n).all(), f"{name}: expected {n} answers per model and defence"
    out = pd.concat({k: g.mean() for k, g in groups.items()}, axis=1).reset_index()
    out = (out.merge(quality[["defence", "psnr_mean", "ssim_mean"]], on="defence", how="left")
              .merge(timing[["defence", "ms_per_image"]], on="defence", how="left"))
    out["defence"] = pd.Categorical(out.defence, DEFENCES, ordered=True)
    assert out.defence.notna().all(), "a defence missing from DEFENCES"
    return out.sort_values(key).reset_index(drop=True)


def table1_latex(tab) -> str:
    pct = lambda x: f"{100 * x:.1f}"
    t = tab.copy()
    t["model"] = t.model.where(~t.model.duplicated(), "")  # name each model once
    return t.to_latex(index=False, escape=True, column_format="llrrrrrrrr", na_rep="--", formatters={
        "context_asr": pct, "instruction_asr": pct, "i_on_asr": pct, "textvqa_acc": pct, "clean_acc": pct,
        "psnr_mean": "{:.1f}".format, "ssim_mean": "{:.3f}".format, "ms_per_image": "{:.1f}".format,
    }, header=["Model", "Defence", "C-on ASR (\\%)", "I-off ASR (\\%)", "I-on ASR (\\%)", "TextVQA (\\%)",
               "Clean COCO (\\%)", "PSNR (dB)", "SSIM", "ms / image"])


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
