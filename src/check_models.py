"""Check that every model in configs/models.yaml exists on Hugging Face at its pinned revision.

Needs no GPU and downloads only each model's small config.json.

Usage:
    python src/check_models.py
"""
import argparse
import json
import urllib.request
from pathlib import Path

import yaml


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/models.yaml"))
    args = parser.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    all_ok = True
    for m in cfg["models"]:
        repo, rev = m["repo_id"], m["revision"]
        try:
            info = fetch_json(f"https://huggingface.co/api/models/{repo}/revision/{rev}")
            config = fetch_json(f"https://huggingface.co/{repo}/resolve/{rev}/config.json")
            weights = sum(1 for s in info.get("siblings", []) if s["rfilename"].endswith(".safetensors"))
            size_gb = sum(s.get("size", 0) for s in info.get("siblings", [])) / 1e9
            print(f"OK   {m['name']:22s} {repo}")
            print(f"     revision {rev[:12]} exists, model_type={config.get('model_type')}, "
                  f"{weights} safetensors files, gated={info.get('gated')}, "
                  f"license={(info.get('cardData') or {}).get('license')}"
                  + (f", about {size_gb:.1f} GB" if size_gb else ""))
        except Exception as e:
            all_ok = False
            print(f"FAIL {m['name']:22s} {repo} @ {rev[:12]}: {e}")

    print("\nall three models resolve at their pinned revisions" if all_ok else "\nsomething is wrong, see FAIL lines")


if __name__ == "__main__":
    main()
