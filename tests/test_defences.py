import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from defences import DEFENCES, apply_defence


def random_image(height=512, width=683, seed=0):
    return np.random.default_rng(seed).integers(0, 256, size=(height, width, 3), dtype=np.uint8)


@pytest.mark.parametrize("name", sorted(DEFENCES))
@pytest.mark.parametrize("shape", [(512, 683), (767, 512), (513, 513)])
def test_same_shape_and_dtype(name, shape):
    image = random_image(*shape)
    result = apply_defence(image, name)
    assert result.shape == image.shape
    assert result.dtype == image.dtype


@pytest.mark.parametrize("name", sorted(DEFENCES))
def test_input_is_not_changed(name):
    image = random_image()
    before = image.copy()
    apply_defence(image, name)
    assert np.array_equal(image, before)


@pytest.mark.parametrize("name", sorted(set(DEFENCES) - {"none"}))
def test_defence_changes_the_image(name):
    image = random_image()
    assert not np.array_equal(apply_defence(image, name), image)


def test_none_returns_same_pixels():
    image = random_image()
    assert np.array_equal(apply_defence(image, "none"), image)


def test_bits_3_leaves_eight_levels():
    image = random_image()
    assert len(np.unique(apply_defence(image, "bits_3"))) == 8
    assert apply_defence(np.full((4, 4, 3), 255, np.uint8), "bits_3").max() == 255


def test_stronger_blur_moves_further_from_original():
    image = random_image()
    errors = [np.abs(apply_defence(image, f"blur_s{s}").astype(int) - image).mean() for s in (1, 2, 3)]
    assert errors[0] < errors[1] < errors[2]


def test_lower_jpeg_quality_moves_further_from_original():
    image = random_image()
    errors = [np.abs(apply_defence(image, f"jpeg_q{q}").astype(int) - image).mean() for q in (50, 20, 10)]
    assert errors[0] < errors[1] < errors[2]


def test_unknown_defence_raises():
    with pytest.raises(KeyError):
        apply_defence(random_image(), "sharpen")
