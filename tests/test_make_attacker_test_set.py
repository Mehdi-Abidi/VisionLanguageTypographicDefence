import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from make_attacker_set import CELLS, DEFENCES
from make_attacker_test_set import chosen_settings, manifest_rows, test_photos as load_test_photos

ATTACK = Path(__file__).resolve().parents[1] / "data" / "attack_set.csv"


def write_config(tmp_path, chosen):
    p = tmp_path / "attacker.yaml"
    p.write_text(yaml.safe_dump({"defences": {d: {"setting": s} for d, s in chosen.items()}}), encoding="utf-8")
    return p


def test_only_the_150_test_photos_are_used():
    photos = load_test_photos(ATTACK)
    assert len(photos) == 150 and {p["split"] for p in photos} == {"test"}


def test_each_setting_runs_under_its_defence_and_undefended(tmp_path):
    chosen = {"blur_s2": "font32_high_object_dejavu_x3", "jpeg_q20": "font24_low_object_comic_x1",
              "ocr_inpaint": "font16_low_object_comic_x2"}
    photos = load_test_photos(ATTACK)
    rows = manifest_rows(photos, chosen_settings(write_config(tmp_path, chosen)))
    assert len(rows) == 150 * len(CELLS) * 3 * 2 == 1800
    keys = {(r["image_id"], r["cell"], r["setting"], r["defence"]) for r in rows}
    assert len(keys) == len(rows)
    for d, s in chosen.items():
        assert {(r["setting"], r["defence"]) for r in rows if r["setting"] == s} == {(s, "none"), (s, d)}
    first = photos[0]["image_id"]
    assert rows[0]["path"] == f"images/{first}_c_on_font32_high_object_dejavu_x3.png"
    assert rows[1]["path"] == f"images/{first}_c_on_font32_high_object_dejavu_x3_blur_s2.png"


def test_a_shared_setting_has_one_undefended_row(tmp_path):
    chosen = {"blur_s2": "font24_high_object_dejavu_x1", "jpeg_q20": "font24_high_object_dejavu_x1",
              "ocr_inpaint": "font16_low_object_comic_x2"}
    rows = manifest_rows(load_test_photos(ATTACK), chosen_settings(write_config(tmp_path, chosen)))
    assert len(rows) == 150 * len(CELLS) * (2 + 1 + 2)
    shared = [r for r in rows if r["setting"] == "font24_high_object_dejavu_x1"]
    assert sorted({r["defence"] for r in shared}) == ["blur_s2", "jpeg_q20", "none"]


def test_a_setting_outside_the_grid_is_refused(tmp_path):
    chosen = {d: "font16_high_object" for d in DEFENCES}
    with pytest.raises(AssertionError):
        chosen_settings(write_config(tmp_path, chosen))
