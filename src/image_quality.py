"""A10. For each defence, PSNR and SSIM between the defended image and the
undefended (defence=none) version of the same image_id, cell and setting.

Usage:
    python src/image_quality.py --manifest manifests/full.csv \
        --images-root /tmp/pg_root --out results/image_quality.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from defences import load_rgb


def pair_keys(manifest: pd.DataFrame) -> tuple:
    """Split a manifest into (undefended_lookup, defended_rows).

    undefended_lookup maps (image_id, cell, setting) -> path, built from the
    defence == 'none' rows. defended_rows is every other row, in order."""
    undefended = manifest[manifest["defence"] == "none"].set_index(
        ["image_id", "cell", "setting"])["path"]
    defended = manifest[manifest["defence"] != "none"].reset_index(drop=True)
    return undefended, defended


def compute_metrics(clean: np.ndarray, other: np.ndarray) -> dict:
    """PSNR and SSIM between two same-shape RGB arrays, or None if the
    shapes don't match (the caller should skip/count the pair as missing)."""
    if clean.shape != other.shape:
        return None
    return {
        "psnr": psnr(clean, other, data_range=255),
        "ssim": ssim(clean, other, channel_axis=2, data_range=255),
    }


def summarize(per_row: list) -> pd.DataFrame:
    """Group a list of {"defence", "psnr", "ssim"} dicts into the mean/std
    per defence table that gets written to results/image_quality.csv."""
    per_row_df = pd.DataFrame(per_row, columns=["defence", "psnr", "ssim"])
    return per_row_df.groupby("defence").agg(
        n=("psnr", "size"),
        psnr_mean=("psnr", "mean"), psnr_std=("psnr", "std"),
        ssim_mean=("ssim", "mean"), ssim_std=("ssim", "std"),
    ).reset_index()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("manifests/full.csv"))
    parser.add_argument("--images-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("results/image_quality.csv"))
    parser.add_argument("--limit", type=int, default=0, help="stop after N defended rows, 0 for all")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest)
    undefended, defended = pair_keys(manifest)
    if args.limit:
        defended = defended.iloc[:args.limit]

    per_row = []
    missing_pair = 0
    for k, row in defended.iterrows():
        key = (row["image_id"], row["cell"], row["setting"])
        if key not in undefended.index:
            missing_pair += 1
            continue
        clean_path = undefended.loc[key]
        clean = load_rgb(args.images_root / clean_path)
        other = load_rgb(args.images_root / row["path"])
        metrics = compute_metrics(clean, other)
        if metrics is None:
            missing_pair += 1
            continue
        per_row.append({"defence": row["defence"], **metrics})
        if (k + 1) % 500 == 0 or k + 1 == len(defended):
            print(f"{k + 1}/{len(defended)}")

    if missing_pair:
        print(f"skipped {missing_pair} rows with no matching undefended pair or a shape mismatch")

    summary = summarize(per_row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out, index=False)
    print(f"wrote {len(summary)} defences to {args.out}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
