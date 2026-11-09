import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stats import auc_curve, holm, mcnemar, paired_bootstrap_auc, wilson


def test_wilson():
    assert wilson(0, 10)[1] == pytest.approx(0, abs=1e-12)
    rate, lo, hi = wilson(5, 10)  # known value for 5/10
    assert (rate, round(lo, 4), round(hi, 4)) == (0.5, 0.2366, 0.7634)
    with pytest.raises(ValueError):
        wilson(0, 0)


def test_mcnemar():
    a = [1] * 8 + [0] * 2 + [1] * 5  # 8 only-a, 2 only-b, 5 both
    b = [0] * 8 + [1] * 2 + [1] * 5
    assert mcnemar(a, b) == (2, pytest.approx(0.109375))  # 2 * P(Bin(10, .5) <= 2) = 2 * 56/1024
    assert mcnemar(a, b, "greater")[1] == pytest.approx(0.0546875)
    assert mcnemar([1, 0], [1, 0], "greater")[1] == 1.0  # no discordant pairs
    with pytest.raises(ValueError):
        mcnemar([1], [1, 0])


def test_holm():
    # sorted .01*3=.03, .03*2=.06, .04*1=.04 -> raised to .06 to stay monotone
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.6, 0.9]) == pytest.approx([1.0, 1.0])  # capped at 1


def test_auc_curve():
    assert auc_curve([0, 1, 2, 3], [1.0, 0.5, 0.25, 0.0]) == pytest.approx(1.25)  # .75 + .375 + .125


def test_bootstrap_identical_cells():
    x = np.array([[1, 1, 0, 0], [1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 1, 0]])  # first column all 1: nothing dropped
    diff, (lo, hi), p, dropped = paired_bootstrap_auc([0, 1, 2, 3], x, x, n_boot=500)
    assert (diff, lo, hi, p, dropped) == (0, 0, 0, 1.0, 0)


def test_bootstrap_instruction_drops_faster():
    c = np.ones((20, 4))  # context never falls: area 3, retained 3
    i = np.tile([1, 1, 0, 0], (20, 1))  # instruction: (1+1)/2 + (1+0)/2 + 0 = 1.5, retained 1.5
    diff, (lo, hi), p, dropped = paired_bootstrap_auc([0, 1, 2, 3], c, i, n_boot=500)
    assert (diff, lo, hi, p, dropped) == (-1.5, -1.5, -1.5, 0.0, 0)


def test_bootstrap_same_seed_same_answer():
    rng = np.random.default_rng(1)
    c, i = rng.integers(0, 2, (30, 4)), rng.integers(0, 2, (30, 4))
    assert paired_bootstrap_auc([0, 1, 2, 3], c, i, n_boot=200) == paired_bootstrap_auc([0, 1, 2, 3], c, i, n_boot=200)
