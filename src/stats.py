"""Ticket C4. The statistics, as fixed in docs/pre-registration.md ("Statistics, in one place").

    wilson(successes, n)                          -> (rate, lo, hi), 95% Wilson interval
    mcnemar(a, b, alternative)                    -> (statistic, p), exact test on paired 0/1 lists
    holm(pvalues)                                 -> Holm-corrected p-values, same order
    auc_curve(strengths, rates)                   -> trapezoid area under a success-vs-strength curve
    paired_bootstrap_auc(strengths, c, i, ...)    -> H2 test: retained success of i minus c
"""
import numpy as np
from scipy.stats import binomtest
from statsmodels.stats.contingency_tables import mcnemar as _mcnemar
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint


def wilson(successes, n):
    if n <= 0:
        raise ValueError("n must be positive")
    lo, hi = proportion_confint(successes, n, alpha=0.05, method="wilson")
    return successes / n, float(lo), float(hi)


def mcnemar(a, b, alternative="two-sided"):
    """a, b: 0/1 results on the same images. "greater" tests that a succeeds more often than b."""
    if len(a) != len(b):
        raise ValueError("a and b must have the same length")
    a, b = np.asarray(a), np.asarray(b)
    n10 = int(np.sum((a == 1) & (b == 0)))
    n01 = int(np.sum((a == 0) & (b == 1)))
    if alternative == "greater":
        p = binomtest(n10, n10 + n01, 0.5, "greater").pvalue if n10 + n01 else 1.0
        return min(n10, n01), float(p)
    if alternative != "two-sided":
        raise ValueError("alternative must be 'two-sided' or 'greater'")
    table = [[int(np.sum((a == 1) & (b == 1))), n10], [n01, int(np.sum((a == 0) & (b == 0)))]]
    r = _mcnemar(table, exact=True)
    return float(r.statistic), float(r.pvalue)


def holm(pvalues):
    return multipletests(pvalues, method="holm")[1].tolist()


def auc_curve(strengths, rates):
    return float(np.trapezoid(rates, strengths))


def _retained(strengths, means):
    """Area under each curve in the last axis of `means`, divided by its undefended (first) rate."""
    return np.trapezoid(means, strengths, axis=-1) / means[..., 0]


def paired_bootstrap_auc(strengths, c, i, n_boot=10000, seed=0):
    """H2. c, i: 0/1 arrays (n_images, n_strengths); row k is the same image in both, first column undefended.
    Returns (diff, (lo, hi), p, dropped): diff = retained(i) - retained(c) on the data, the 2.5th-97.5th
    percentile interval, the two-sided p (twice the share of resamples on the wrong side of zero), and how many
    resamples were dropped because an undefended rate was 0.
    shortcut: strengths are used as given, so for JPEG pass the ladder step (0..3), not the quality; no upgrade needed."""
    c, i = np.asarray(c, float), np.asarray(i, float)
    if c.shape != i.shape:
        raise ValueError("c and i must have the same shape")
    diff = float(_retained(strengths, i.mean(0)) - _retained(strengths, c.mean(0)))
    idx = np.random.default_rng(seed).integers(0, len(c), (n_boot, len(c)))
    cm, im = c[idx].mean(1), i[idx].mean(1)  # (n_boot, n_strengths): the same rows drawn for both cells
    keep = (cm[:, 0] > 0) & (im[:, 0] > 0)
    d = _retained(strengths, im[keep]) - _retained(strengths, cm[keep])
    p = min(1.0, 2 * min(np.mean(d <= 0), np.mean(d >= 0)))
    return diff, tuple(np.percentile(d, [2.5, 97.5]).tolist()), float(p), int((~keep).sum())
