import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import analysis
import hypotheses


def test_hypothesis_tests_follow_the_pre_registration():
    df = analysis.tidy()
    tests, h3 = hypotheses.run(df, analysis.textvqa(), pd.read_csv(ROOT / "results/ocr_read.csv"))
    for m, g in tests.groupby("model"):
        assert {"H1a", "H1b", "H2", "H3", "H4"} <= set(g.hypothesis), m
        # Holm never lowers a p-value
        both = g.dropna(subset=["p", "p_holm"])
        assert (both.p_holm >= both.p - 1e-12).all(), m
    # pilot gate: under 10 undefended I-on successes, H2 is not tested and does not hold
    t = df[(df.split == "test") & (df.setting == analysis.DEFAULT) & (df.defence == "none") & (df.cell == "i_on")]
    for m, n in t.groupby("model").success.sum().items():
        h2 = tests[(tests.model == m) & (tests.hypothesis == "H2") & tests.test.str.contains("all images")]
        assert h2.p.isna().all() == (n < hypotheses.MIN_I_ON), m
    assert set(hypotheses.verdicts(tests).hypothesis) == {"H1a", "H1b", "H2", "H3", "H4"}
    assert h3.missed.le(h3.successes).all()
