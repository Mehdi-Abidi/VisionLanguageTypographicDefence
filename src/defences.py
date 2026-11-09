"""Image defences applied after rendering and before the model sees the photo.

Every defence takes an RGB uint8 NumPy image of shape (height, width, 3) and returns
one of the same shape and dtype. DEFENCES maps the manifest names to the functions.
ocr_inpaint needs EasyOCR, which is loaded the first time it is used.

Usage:
    python src/defences.py images/9914_c_on_font16_high_object.png
    python src/defences.py images/9914_c_on_font16_high_object.png --out results/defences_9914.png
    python src/defences.py images/9914_i_off_font32_high_object.png --ocr-dir results/ocr
"""
import argparse
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OCR_MIN_CONFIDENCE = 0.3
OCR_DILATE_PX = 3
INPAINT_RADIUS = 3


def gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(image, (0, 0), sigmaX=sigma, sigmaY=sigma)


def median_filter(image: np.ndarray, size: int = 5) -> np.ndarray:
    return cv2.medianBlur(image, size)


def jpeg(image: np.ndarray, quality: int) -> np.ndarray:
    ok, encoded = cv2.imencode(".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
                               [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return cv2.cvtColor(cv2.imdecode(encoded, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def bit_depth(image: np.ndarray, bits: int = 3) -> np.ndarray:
    levels = 2 ** bits - 1
    return (np.round(image.astype(np.float32) / 255 * levels) / levels * 255).round().astype(np.uint8)


def down_up(image: np.ndarray, factor: float = 0.5) -> np.ndarray:
    height, width = image.shape[:2]
    small = cv2.resize(image, (max(1, round(width * factor)), max(1, round(height * factor))),
                       interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)


@lru_cache(maxsize=1)
def get_reader():
    import easyocr
    import torch
    return easyocr.Reader(["en"], gpu=torch.cuda.is_available(), verbose=False)


def read_text(image: np.ndarray) -> list:
    detections = get_reader().readtext(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return [{"text": text,
             "confidence": round(float(confidence), 4),
             "box": [[int(round(x)), int(round(y))] for x, y in box],
             "kept": float(confidence) >= OCR_MIN_CONFIDENCE}
            for box, text, confidence in detections]


def ocr_inpaint(image: np.ndarray, words: list = None) -> tuple:
    if words is None:
        words = read_text(image)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for word in words:
        if word["kept"]:
            cv2.fillPoly(mask, [np.array(word["box"], dtype=np.int32)], 255)
    if mask.any():
        kernel = np.ones((2 * OCR_DILATE_PX + 1, 2 * OCR_DILATE_PX + 1), np.uint8)
        mask = cv2.dilate(mask, kernel)
        result = cv2.inpaint(image, mask, INPAINT_RADIUS, cv2.INPAINT_TELEA)
    else:
        result = image.copy()
    return result, mask, words


CLASSICAL = {
    "none": lambda im: im.copy(),
    "blur_s1": lambda im: gaussian_blur(im, 1),
    "blur_s2": lambda im: gaussian_blur(im, 2),
    "blur_s3": lambda im: gaussian_blur(im, 3),
    "median_5": lambda im: median_filter(im, 5),
    "jpeg_q50": lambda im: jpeg(im, 50),
    "jpeg_q20": lambda im: jpeg(im, 20),
    "jpeg_q10": lambda im: jpeg(im, 10),
    "bits_3": lambda im: bit_depth(im, 3),
    "downup_05": lambda im: down_up(im, 0.5),
}

DEFENCES = {**CLASSICAL, "ocr_inpaint": lambda im: ocr_inpaint(im)[0]}


def apply_defence(image: np.ndarray, name: str) -> np.ndarray:
    if name not in DEFENCES:
        raise KeyError(f"unknown defence {name!r}, expected one of {sorted(DEFENCES)}")
    return DEFENCES[name](image)


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def save_ocr_inpaint(image_path: Path, out_dir: Path) -> list:
    result, mask, words = ocr_inpaint(load_rgb(image_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{image_path.stem}_ocr_inpaint"
    Image.fromarray(result).save(out_dir / f"{name}.png")
    Image.fromarray(mask).save(out_dir / f"{name}_mask.png")
    return words


def defence_sheet(image_path: Path, out: Path, crop: int, names: list) -> None:
    image = load_rgb(image_path)
    tiles = []
    for name in names:
        result = apply_defence(image, name)
        assert result.shape == image.shape and result.dtype == image.dtype, name
        tile = Image.fromarray(result)
        if crop:
            cx, cy, half = tile.width // 2, tile.height // 2, crop // 2
            tile = tile.crop((cx - half, cy - half, cx + half, cy + half))
        tiles.append((name, tile))
        print(f"{name:11s} ok {result.shape} {result.dtype}")

    cols = 5
    w, h = tiles[0][1].size
    sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * (h + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for i, (name, tile) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + 24)
        draw.text((x + 6, y + 2), name, fill="black", font=font)
        sheet.paste(tile, (x, y + 24))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("saved", out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, default=None, help="sheet file name, only with one image")
    parser.add_argument("--crop", type=int, default=300, help="side of the centre crop shown per tile, 0 for the whole photo")
    parser.add_argument("--classical-only", action="store_true", help="leave ocr_inpaint out of the sheet")
    parser.add_argument("--ocr-dir", type=Path, default=None, help="run only ocr_inpaint and save the result and mask here")
    args = parser.parse_args()

    for image_path in args.images:
        if args.ocr_dir:
            words = save_ocr_inpaint(image_path, args.ocr_dir)
            print(image_path.name)
            for w in words or [{"text": "(nothing found)", "confidence": 0, "kept": False}]:
                print(f"    {'kept' if w['kept'] else 'skip'} {w['confidence']:.2f} {w['text']!r}")
        else:
            out = args.out if args.out and len(args.images) == 1 else Path("results") / f"defences_{image_path.stem}.png"
            names = list(CLASSICAL if args.classical_only else DEFENCES)
            defence_sheet(image_path, out, args.crop, names)


if __name__ == "__main__":
    main()
