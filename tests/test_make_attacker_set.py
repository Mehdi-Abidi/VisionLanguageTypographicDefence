import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from make_attacker_set import CELLS, DEFENCES, FONTS, grid, manifest_rows, tune_photos

ATTACK = Path(__file__).resolve().parents[1] / "data" / "attack_set.csv"


def test_grid_has_36_distinct_settings():
    settings = [g["setting"] for g in grid()]
    assert len(settings) == len(set(settings)) == 36
    assert "font16_high_object_dejavu_x1" in settings
    assert "font32_low_object_comic_x3" in settings


def test_manifest_covers_every_tune_photo_cell_setting_and_defence():
    photos = tune_photos(ATTACK)
    rows = manifest_rows(photos)
    assert len(photos) == 50
    assert len(rows) == 50 * len(CELLS) * 36 * len(DEFENCES) == 10800
    assert len({(r["image_id"], r["cell"], r["setting"], r["defence"]) for r in rows}) == len(rows)
    assert {r["defence"] for r in rows} == set(DEFENCES)
    assert rows[0]["path"] == f"images/{photos[0]['image_id']}_c_on_font16_high_object_dejavu_x1_blur_s2.png"


def test_stylised_font_file_is_in_the_repo():
    assert Path(FONTS["comic"]).exists()
