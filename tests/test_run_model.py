import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from run_model import config_hash, load_config, run, run_config

FIELDS = ["image_id", "cell", "setting", "defence", "model", "revision", "prompt",
          "output", "config_hash", "seed", "timestamp"]
CONFIG = Path(__file__).resolve().parents[1] / "configs" / "models.yaml"


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "images").mkdir()
    rows = []
    for k in range(10):
        path = f"images/{1000 + k}_c_on_font16_high_object_none.png"
        Image.new("RGB", (40, 30), (k * 20, 0, 0)).save(tmp_path / path)
        rows.append({"image_id": str(1000 + k), "cell": "c_on", "setting": "font16_high_object",
                     "defence": "none", "path": path})
    config, spec = load_config(CONFIG, "qwen3-vl-4b")
    meta = {"model": spec["name"], "revision": spec["revision"][:12], "prompt": config["prompt"],
            "config_hash": config_hash(run_config(config, spec, 0)), "seed": 0}
    return tmp_path, rows, meta


class FakeModel:
    def __init__(self, fail_batches=False):
        self.calls, self.fail_batches = [], fail_batches

    def __call__(self, images):
        self.calls.append(len(images))
        if self.fail_batches and len(images) > 1:
            raise RuntimeError("CUDA out of memory")
        return [f" red {im.getpixel((0, 0))[0]} " for im in images]


def test_writes_one_valid_row_per_manifest_row(setup):
    tmp, rows, meta = setup
    out = tmp / "runs" / "test.jsonl"
    fake = FakeModel()
    assert run(rows, fake, out, tmp, meta, batch_size=8, log=lambda *_: None) == 10
    assert fake.calls == [8, 2]
    df = pd.read_json(out, lines=True)
    assert list(df.columns) == FIELDS
    assert len(df) == 10 and df["image_id"].tolist() == list(range(1000, 1010))
    assert df["output"].iloc[1] == "red 20"
    assert df["revision"].iloc[0] == "ebb281ec70b0" and df["model"].iloc[0] == "qwen3-vl-4b"
    stamps = [json.loads(line)["timestamp"] for line in out.read_text(encoding="utf-8").splitlines()]
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", s) for s in stamps)


def test_restart_skips_rows_already_done(setup):
    tmp, rows, meta = setup
    out = tmp / "test.jsonl"
    run(rows[:5], FakeModel(), out, tmp, meta, log=lambda *_: None)
    fake = FakeModel()
    assert run(rows, fake, out, tmp, meta, log=lambda *_: None) == 5
    assert fake.calls == [5]
    df = pd.read_json(out, lines=True)
    assert len(df) == 10 and df["image_id"].is_unique


def test_half_written_last_line_is_dropped_and_redone(setup):
    tmp, rows, meta = setup
    out = tmp / "test.jsonl"
    run(rows[:3], FakeModel(), out, tmp, meta, log=lambda *_: None)
    with open(out, "a", encoding="utf-8") as f:
        f.write('{"image_id": 1003, "cell": "c_')
    assert run(rows, FakeModel(), out, tmp, meta, log=lambda *_: None) == 7
    df = pd.read_json(out, lines=True)
    assert len(df) == 10 and df["image_id"].is_unique


def test_failed_batch_falls_back_to_one_image_at_a_time(setup):
    tmp, rows, meta = setup
    out = tmp / "test.jsonl"
    fake = FakeModel(fail_batches=True)
    assert run(rows, fake, out, tmp, meta, log=lambda *_: None) == 10
    assert len(pd.read_json(out, lines=True)) == 10


def test_config_hash_is_md5_of_sorted_config():
    config, spec = load_config(CONFIG, "smolvlm2-2b")
    cfg = run_config(config, spec, 0)
    h = config_hash(cfg)
    assert len(h) == 32
    assert config_hash(dict(reversed(list(cfg.items())))) == h
    assert config_hash({**cfg, "prompt": "Describe the image."}) != h
    assert config_hash({**cfg, "seed": 1}) != h


def test_every_model_in_the_config_gets_a_different_hash():
    hashes = set()
    for name in ("smolvlm2-2b", "qwen3-vl-4b", "llava-next-mistral-7b"):
        config, spec = load_config(CONFIG, name)
        hashes.add(config_hash(run_config(config, spec, 0)))
    assert len(hashes) == 3


def test_unknown_model_stops_with_a_message():
    with pytest.raises(SystemExit):
        load_config(CONFIG, "gpt-4o")


def test_output_text_is_written_unchanged(setup):
    tmp, rows, meta = setup
    out = tmp / "test.jsonl"
    run(rows[:1], lambda ims: ["Ein Café, “cat”!"], out, tmp, meta, log=lambda *_: None)
    assert json.loads(out.read_text(encoding="utf-8"))["output"] == "Ein Café, “cat”!"


WORKER = """
import sys, time
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from run_model import read_manifest, run

def slow_model(images):
    time.sleep(0.25)
    return ["dog"] * len(images)

meta = {"model": "fake", "revision": "000000000000", "prompt": "p", "config_hash": "h", "seed": 0}
run(read_manifest(Path(sys.argv[2])), slow_model, Path(sys.argv[3]), Path(sys.argv[4]), meta, batch_size=8, log=lambda *_: None)
"""


def test_kill_after_20_rows_and_restart_gives_50_unique_rows(tmp_path):
    import csv
    import subprocess
    import time

    (tmp_path / "images").mkdir()
    rows = []
    for k in range(50):
        path = f"images/{k}_clean_none.png"
        Image.new("RGB", (8, 8)).save(tmp_path / path)
        rows.append({"image_id": k, "cell": "clean", "setting": "none", "defence": "none", "path": path})
    manifest, out = tmp_path / "manifest.csv", tmp_path / "run.jsonl"
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    src = str(Path(__file__).resolve().parents[1] / "src")
    command = [sys.executable, "-c", WORKER, src, str(manifest), str(out), str(tmp_path)]

    def lines():
        return len(out.read_text(encoding="utf-8").splitlines()) if out.exists() else 0

    first = subprocess.Popen(command)
    deadline = time.time() + 60
    while lines() < 20 and time.time() < deadline:
        time.sleep(0.02)
    first.kill()
    first.wait()
    stopped_at = lines()
    assert 20 <= stopped_at < 50

    subprocess.run(command, check=True, timeout=60)
    df = pd.read_json(out, lines=True)
    assert len(df) == 50
    assert not df.duplicated(["image_id", "cell", "setting", "defence"]).any()
    assert sorted(df["image_id"]) == list(range(50))
