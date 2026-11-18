import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import analysis


def test_tidy_scores_every_row_against_the_right_target():
    d = analysis.tidy()
    assert len(d) == 89200 and not d.duplicated(["image_id", "cell", "setting", "defence", "model"]).any()
    assert set(d.success) <= {0, 1} and set(d.split) == {"tune", "test"}
    # off-topic targets almost never work: 7 of 35,400 rows on 15 Nov, all c_off, none at the default rendering
    assert d[d.cell.isin(["i_off", "c_off", "neutral_long"])].success.mean() < 0.001
