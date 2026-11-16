"""Ticket A8. Pick 200 TextVQA questions and make the utility set that B8 runs.

Picks questions from the TextVQA 0.5.1 validation set whose majority answer is one word or a
number, shuffles them with the seed, and keeps one question per image until it has 200. Each
image is resized to a 512 px short side, the same size as the attack photos, and passed through
every defence used in A7. Paths follow make_manifest.py with cell "textvqa" and setting "none".

Writes data/textvqa_set.csv and manifests/utility.csv. With --images it also writes the images.
The image zip is about 7 GB, so by default only the 200 needed images are read from it over
HTTP range requests.

Usage:
    python src/make_textvqa_set.py
    python src/make_textvqa_set.py --images --out /kaggle/working
"""
import argparse
import csv
import io
import json
import random
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_manifest as mm

JSON_URL = "https://dl.fbaipublicfiles.com/textvqa/data/TextVQA_0.5.1_val.json"
ZIP_URL = "https://dl.fbaipublicfiles.com/textvqa/images/train_val_images.zip"
DEFENCES = ["none", "blur_s1", "blur_s2", "blur_s3", "jpeg_q50", "jpeg_q20", "jpeg_q10", "ocr_inpaint",
            "median_5", "bits_3", "downup_05"]
CELL, SETTING = "textvqa", "none"
SHORT_SIDE = 512


class RangeFile(io.RawIOBase):
    def __init__(self, url: str, block: int = 1 << 18):
        self.url, self.block, self.pos, self.cache = url, block, 0, {}
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
            self.size = int(r.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def _block(self, k: int) -> bytes:
        if k not in self.cache:
            start = k * self.block
            end = min(start + self.block, self.size) - 1
            req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                self.cache[k] = r.read()
        return self.cache[k]

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        out = bytearray()
        while n > 0 and self.pos < self.size:
            k, off = divmod(self.pos, self.block)
            chunk = self._block(k)[off:off + n]
            out += chunk
            self.pos += len(chunk)
            n -= len(chunk)
        return bytes(out)

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def majority(answers: list) -> str:
    counts = Counter(a.strip().lower() for a in answers)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def is_single(answer: str) -> bool:
    return re.fullmatch(r"[a-z0-9]+(\.[0-9]+)?", answer) is not None


def pick(questions: list, n: int, seed: int) -> list:
    eligible = sorted((q for q in questions if is_single(majority(q["answers"]))), key=lambda q: q["question_id"])
    random.Random(seed).shuffle(eligible)
    chosen, seen = [], set()
    for q in eligible:
        if q["image_id"] not in seen:
            seen.add(q["image_id"])
            chosen.append(q)
        if len(chosen) == n:
            break
    return chosen


def load_json(path: Path) -> list:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(JSON_URL, timeout=120) as r:
            path.write_bytes(r.read())
    return json.loads(path.read_text(encoding="utf-8"))["data"]


def manifest_rows(chosen: list) -> list:
    return [{"image_id": q["question_id"], "cell": CELL, "setting": SETTING, "defence": d,
             "path": mm.resolved_path(q["question_id"], CELL, SETTING, d)} for q in chosen for d in DEFENCES]


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_images(chosen: list, rows: list, out: Path, zip_source: str) -> None:
    from PIL import Image
    from render import resize_short_side

    source = zip_source if Path(zip_source).exists() else RangeFile(zip_source)
    with zipfile.ZipFile(source) as z:
        members = {Path(m).stem: m for m in z.namelist() if m.lower().endswith(".jpg")}
        (out / "images").mkdir(parents=True, exist_ok=True)
        for k, q in enumerate(chosen, 1):
            path = out / mm.render_path(q["question_id"], CELL, SETTING)
            if not path.exists():
                photo = Image.open(io.BytesIO(z.read(members[q["image_id"]]))).convert("RGB")
                photo, _ = resize_short_side(photo, (0, 0, 0, 0))
                photo.save(path)
            if k % 50 == 0 or k == len(chosen):
                print(f"{k}/{len(chosen)} images read and resized")
    mm.generate_missing(rows, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=Path("data/raw/TextVQA_0.5.1_val.json"))
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--set-out", type=Path, default=Path("data/textvqa_set.csv"))
    parser.add_argument("--manifest-out", type=Path, default=Path("manifests/utility.csv"))
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("."))
    parser.add_argument("--zip", default=ZIP_URL)
    args = parser.parse_args()

    questions = load_json(args.json)
    chosen = pick(questions, args.n, args.seed)
    rows = manifest_rows(chosen)
    write_csv(args.set_out, [{
        "image_id": q["question_id"], "textvqa_image_id": q["image_id"], "question": q["question"],
        "answers": json.dumps(q["answers"], ensure_ascii=False), "majority_answer": majority(q["answers"]),
        "width": q["image_width"], "height": q["image_height"],
        "path": mm.render_path(q["question_id"], CELL, SETTING)} for q in chosen])
    write_csv(args.manifest_out, rows)
    print(f"{len(questions)} questions, {sum(is_single(majority(q['answers'])) for q in questions)} with a one-word "
          f"answer, {len(chosen)} picked from {len({q['image_id'] for q in chosen})} images, {len(rows)} manifest rows")
    if args.images:
        make_images(chosen, rows, args.out, args.zip)


if __name__ == "__main__":
    main()
