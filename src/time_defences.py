"""Ticket C9. Milliseconds per image for each defence, the last column of Table 1.

    python src/time_defences.py images/*.png --out results/defence_timing.csv

Each defence runs `repeats` times over every image after one warm-up call, and EasyOCR is loaded
before the clock starts, so the time is the defence alone. The machine is written in the file:
OCR-inpainting is much faster with a GPU, so the number is only comparable on the same hardware.
"""
import argparse
import platform
import time
from pathlib import Path

import pandas as pd

from defences import DEFENCES, get_reader, load_rgb


def time_defences(paths, repeats=5) -> pd.DataFrame:
    images = [load_rgb(p) for p in paths]
    get_reader()
    import torch
    rows = []
    for name, defend in DEFENCES.items():
        if name == "none":
            continue
        defend(images[0])
        start = time.perf_counter()
        for _ in range(repeats):
            for im in images:
                defend(im)
        ms = (time.perf_counter() - start) * 1000 / (repeats * len(images))
        rows.append({"defence": name, "ms_per_image": round(ms, 2), "n_images": len(images), "repeats": repeats,
                     "cpu": platform.processor(), "ocr_on_gpu": torch.cuda.is_available()})
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--out", type=Path, default=Path("results/defence_timing.csv"))
    a = p.parse_args()
    t = time_defences(a.images, a.repeats)
    t.to_csv(a.out, index=False)
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
