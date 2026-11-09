import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from defences import CLASSICAL, DEFENCES, apply_defence, ocr_inpaint


def random_image(height=512, width=683, seed=0):
    return np.random.default_rng(seed).integers(0, 256, size=(height, width, 3), dtype=np.uint8)


def text_image(text="STOP HERE", size=48):
    image = Image.new("RGB", (512, 256), (200, 160, 120))
    draw = ImageDraw.Draw(image)
    draw.rectangle([60, 90, 452, 170], fill="white")
    draw.text((80, 100), text, fill="black", font=ImageFont.load_default(size=size))
    return np.asarray(image)


@pytest.mark.parametrize("name", sorted(CLASSICAL))
@pytest.mark.parametrize("shape", [(512, 683), (767, 512), (513, 513)])
def test_same_shape_and_dtype(name, shape):
    image = random_image(*shape)
    result = apply_defence(image, name)
    assert result.shape == image.shape
    assert result.dtype == image.dtype


@pytest.mark.parametrize("name", sorted(CLASSICAL))
def test_input_is_not_changed(name):
    image = random_image()
    before = image.copy()
    apply_defence(image, name)
    assert np.array_equal(image, before)


@pytest.mark.parametrize("name", sorted(set(CLASSICAL) - {"none"}))
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


def test_ocr_inpaint_is_listed():
    assert "ocr_inpaint" in DEFENCES


def test_ocr_inpaint_with_no_words_returns_a_copy():
    image = random_image()
    result, mask, words = ocr_inpaint(image, words=[])
    assert np.array_equal(result, image) and result is not image
    assert mask.shape == image.shape[:2] and not mask.any()


def test_ocr_inpaint_skips_low_confidence_boxes():
    image = random_image()
    weak = [{"text": "x", "confidence": 0.1, "box": [[10, 10], [60, 10], [60, 40], [10, 40]], "kept": False}]
    result, mask, _ = ocr_inpaint(image, words=weak)
    assert not mask.any() and np.array_equal(result, image)


def test_ocr_inpaint_mask_is_box_plus_three_pixels():
    image = random_image()
    box = [{"text": "x", "confidence": 0.9, "box": [[100, 100], [200, 100], [200, 150], [100, 150]], "kept": True}]
    result, mask, _ = ocr_inpaint(image, words=box)
    ys, xs = np.nonzero(mask)
    assert (xs.min(), xs.max(), ys.min(), ys.max()) == (97, 203, 97, 153)
    assert result.shape == image.shape and result.dtype == image.dtype
    assert np.array_equal(result[mask == 0], image[mask == 0])


def test_ocr_inpaint_finds_and_removes_real_text():
    pytest.importorskip("easyocr")
    image = text_image()
    result, mask, words = ocr_inpaint(image)
    read = " ".join(w["text"] for w in words if w["kept"]).upper()
    assert "STOP" in read
    assert mask.any()
    assert result.shape == image.shape and result.dtype == image.dtype
    dark_before = (image[mask > 0] < 60).all(axis=1).sum()
    dark_after = (result[mask > 0] < 60).all(axis=1).sum()
    assert dark_after < dark_before * 0.1
