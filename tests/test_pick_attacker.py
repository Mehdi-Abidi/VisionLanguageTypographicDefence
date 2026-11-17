import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from make_attacker_set import CELLS, DEFENCES, grid
from pick_attacker import choose, score, table

TARGETS = pd.DataFrame({"image_id": [1, 2], "on_topic_target": ["cat", "hot dog"]})


def fake_runs(winner: dict) -> pd.DataFrame:
    rows = []
    for model in ("smolvlm2-2b", "qwen3-vl-4b"):
        for image_id, target in ((1, "cat"), (2, "hot dog")):
            for cell in CELLS:
                for g in grid():
                    for d in DEFENCES:
                        hit = g["setting"] in winner.get(d, ())
                        rows.append({"image_id": image_id, "cell": cell, "setting": g["setting"], "defence": d,
                                     "model": model, "output": target if hit else "dog"})
    return pd.DataFrame(rows)


def test_each_defence_gets_its_own_best_setting():
    winner = {"blur_s2": ("font32_high_object_dejavu_x3",), "jpeg_q20": ("font24_low_object_comic_x1",),
              "ocr_inpaint": ("font16_low_object_comic_x2",)}
    scored = score(fake_runs(winner), TARGETS)
    chosen = choose(table(scored), scored)
    for d, (setting,) in winner.items():
        assert chosen[d]["setting"] == setting
        assert chosen[d]["success"] == 1.0 and chosen[d]["answers"] == 2 * 2 * len(CELLS)
        assert chosen[d]["default_rendering_success"] == 0.0


def test_a_tie_goes_to_the_first_setting_in_the_grid():
    tied = ("font32_low_object_comic_x3", "font24_high_object_dejavu_x2")
    scored = score(fake_runs({"blur_s2": tied}), TARGETS)
    chosen = choose(table(scored), scored)
    assert chosen["blur_s2"]["setting"] == "font24_high_object_dejavu_x2"
    assert chosen["blur_s2"]["font_size"] == 24 and chosen["blur_s2"]["repeat"] == 2


def test_the_scorer_rules_apply_two_word_targets_and_negation():
    runs = pd.DataFrame([
        {"image_id": 2, "cell": "c_on", "setting": "s", "defence": "blur_s2", "model": "m", "output": "Hot dogs."},
        {"image_id": 1, "cell": "c_on", "setting": "s", "defence": "blur_s2", "model": "m", "output": "not a cat"},
    ])
    assert score(runs, TARGETS)["success"].tolist() == [True, False]


def test_main_writes_yaml_and_table(tmp_path, monkeypatch):
    import pick_attacker

    runs = fake_runs({"blur_s2": ("font24_high_object_dejavu_x1",)})
    paths = []
    for model, part in runs.groupby("model"):
        p = tmp_path / f"{model}.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in part.to_dict("records")) + "\n", encoding="utf-8")
        paths.append(str(p))
    TARGETS.to_csv(tmp_path / "targets.csv", index=False)
    out, tab = tmp_path / "attacker.yaml", tmp_path / "scores.csv"
    monkeypatch.setattr(sys, "argv", ["pick_attacker.py", "--runs", *paths, "--targets", str(tmp_path / "targets.csv"),
                                      "--out", str(out), "--table", str(tab)])
    pick_attacker.main()
    config = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert set(config["defences"]) == set(DEFENCES)
    assert config["defences"]["blur_s2"]["setting"] == "font24_high_object_dejavu_x1"
    assert len(pd.read_csv(tab)) == len(DEFENCES) * len(grid())
