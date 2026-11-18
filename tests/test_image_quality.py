import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from image_quality import compute_metrics, pair_keys, summarize


def manifest_row(image_id, cell, setting, defence, path):
    return {"image_id": image_id, "cell": cell, "setting": setting, "defence": defence, "path": path}


def test_pair_keys_splits_undefended_from_defended():
    manifest = pd.DataFrame([
        manifest_row(1, "c_on", "s1", "none", "clean/1.png"),
        manifest_row(1, "c_on", "s1", "blur_s1", "blur/1.png"),
        manifest_row(2, "i_off", "s1", "none", "clean/2.png"),
        manifest_row(2, "i_off", "s1", "jpeg_q50", "jpeg/2.png"),
    ])
    undefended, defended = pair_keys(manifest)
    assert undefended.loc[(1, "c_on", "s1")] == "clean/1.png"
    assert undefended.loc[(2, "i_off", "s1")] == "clean/2.png"
    assert len(defended) == 2
    assert set(defended["defence"]) == {"blur_s1", "jpeg_q50"}


def test_pair_keys_missing_pair_is_absent_from_undefended_index():
    manifest = pd.DataFrame([
        manifest_row(1, "c_on", "s1", "blur_s1", "blur/1.png"),  # no matching "none" row
    ])
    undefended, defended = pair_keys(manifest)
    key = (defended.iloc[0]["image_id"], defended.iloc[0]["cell"], defended.iloc[0]["setting"])
    assert key not in undefended.index


def test_compute_metrics_identical_images_are_lossless():
    img = np.random.default_rng(0).integers(0, 255, size=(32, 32, 3), dtype=np.uint8)
    metrics = compute_metrics(img, img.copy())
    assert metrics["psnr"] == np.inf
    assert metrics["ssim"] == pytest.approx(1.0)


def test_compute_metrics_different_images_are_finite_and_imperfect():
    rng = np.random.default_rng(1)
    clean = rng.integers(0, 255, size=(32, 32, 3), dtype=np.uint8)
    noisy = np.clip(clean.astype(int) + rng.integers(-20, 20, size=clean.shape), 0, 255).astype(np.uint8)
    metrics = compute_metrics(clean, noisy)
    assert 0 < metrics["psnr"] < np.inf
    assert 0 <= metrics["ssim"] < 1.0


def test_compute_metrics_shape_mismatch_returns_none():
    clean = np.zeros((32, 32, 3), dtype=np.uint8)
    other = np.zeros((16, 16, 3), dtype=np.uint8)
    assert compute_metrics(clean, other) is None


def test_summarize_groups_by_defence_with_correct_stats():
    per_row = [
        {"defence": "blur_s1", "psnr": 30.0, "ssim": 0.9},
        {"defence": "blur_s1", "psnr": 34.0, "ssim": 0.95},
        {"defence": "jpeg_q50", "psnr": 40.0, "ssim": 0.99},
    ]
    summary = summarize(per_row).set_index("defence")
    assert summary.loc["blur_s1", "n"] == 2
    assert summary.loc["blur_s1", "psnr_mean"] == pytest.approx(32.0)
    assert summary.loc["blur_s1", "ssim_mean"] == pytest.approx(0.925)
    assert summary.loc["jpeg_q50", "n"] == 1
    assert summary.loc["jpeg_q50", "psnr_mean"] == pytest.approx(40.0)


def test_summarize_single_sample_std_is_nan():
    per_row = [{"defence": "bits_3", "psnr": 25.0, "ssim": 0.8}]
    summary = summarize(per_row).set_index("defence")
    assert np.isnan(summary.loc["bits_3", "psnr_std"])


def test_summarize_empty_input_has_no_rows():
    summary = summarize([])
    assert len(summary) == 0
    assert list(summary.columns) == ["defence", "n", "n_unchanged", "psnr_mean", "psnr_std", "ssim_mean", "ssim_std"]


def test_summarize_keeps_unchanged_pairs_out_of_the_psnr_mean():
    per_row = [
        {"defence": "ocr_inpaint", "psnr": np.inf, "ssim": 1.0},
        {"defence": "ocr_inpaint", "psnr": 30.0, "ssim": 0.9},
        {"defence": "ocr_inpaint", "psnr": 34.0, "ssim": 0.95},
    ]
    summary = summarize(per_row).set_index("defence")
    assert summary.loc["ocr_inpaint", "n"] == 3
    assert summary.loc["ocr_inpaint", "n_unchanged"] == 1
    assert summary.loc["ocr_inpaint", "psnr_mean"] == pytest.approx(32.0)
    assert np.isfinite(summary.loc["ocr_inpaint", "psnr_std"])
    assert summary.loc["ocr_inpaint", "ssim_mean"] == pytest.approx(0.95)
