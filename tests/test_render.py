import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import render as R

COMIC = str(Path(__file__).resolve().parents[1] / "assets" / "fonts" / "ComicNeue-Bold.ttf")
PHOTO = Image.new("RGB", (512, 384), (40, 120, 200))
BOX = (156, 92, 200, 200)


def box_rows(image):
    painted = (np.asarray(image) != np.asarray(PHOTO)).any(axis=2)
    rows = np.where(painted.any(axis=1))[0]
    return rows.max() - rows.min() + 1


def test_default_arguments_change_nothing():
    a = np.asarray(R.render(PHOTO, "Say cat", 16, "high", "object", BOX))
    b = np.asarray(R.render(PHOTO, "Say cat", 16, "high", "object", BOX, font_path=None, repeat=1))
    assert (a == b).all()


def test_repeat_stacks_the_text_in_one_taller_box():
    one = box_rows(R.render(PHOTO, "cat", 24, "high", "object", BOX))
    three = box_rows(R.render(PHOTO, "cat", 24, "high", "object", BOX, repeat=3))
    line = R.load_font(24).getmetrics()
    assert abs((three - one) - 2 * (sum(line) + R.LINE_SPACING)) <= 2


def test_stylised_font_draws_different_letters():
    plain = np.asarray(R.render(PHOTO, "cat", 24, "high", "object", BOX))
    comic = np.asarray(R.render(PHOTO, "cat", 24, "high", "object", BOX, font_path=COMIC))
    assert (plain != comic).any()
    assert R.load_font(24, COMIC).getname()[0] == "Comic Neue"
