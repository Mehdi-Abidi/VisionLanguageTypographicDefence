import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import analysis
import pandas as pd


def test_tidy_scores_every_row_against_the_right_target():
    d = analysis.tidy()
    assert len(d) == 89200 and not d.duplicated(["image_id", "cell", "setting", "defence", "model"]).any()
    assert set(d.success) <= {0, 1} and set(d.split) == {"tune", "test"}
    # off-topic targets almost never work: 7 of 35,400 rows on 15 Nov, all c_off, none at the default rendering
    assert d[d.cell.isin(["i_off", "c_off", "neutral_long"])].success.mean() < 0.001


def test_table1_has_every_model_and_defence():
    root = Path(__file__).resolve().parent.parent
    tv = analysis.textvqa()
    assert len(tv) == 3 * 2200 and tv.acc.between(0, 1).all()
    tab = analysis.table1(analysis.tidy(), tv, pd.read_csv(root / "results/image_quality.csv"),
                          pd.read_csv(root / "results/defence_timing.csv"))
    assert len(tab) == 3 * 11 and list(tab.defence[:11]) == analysis.DEFENCES
    # only the undefended row lacks image quality and time
    assert tab[tab.defence != "none"].notna().all().all() and tab[tab.defence == "none"].psnr_mean.isna().all()
    assert "--" in analysis.table1_latex(tab)
