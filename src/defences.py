"""Classical image defences applied after rendering and before the model sees the photo.

Every defence takes an RGB uint8 NumPy image of shape (height, width, 3) and returns
one of the same shape and dtype. DEFENCES maps the manifest names to the functions.

Usage:
    python src/defences.py images/9914_c_on_font16_high_object.png
    python src/defences.py images/9914_c_on_font16_high_object.png --out results/defences_9914.png
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


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


DEFENCES = {
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


def apply_defence(image: np.ndarray, name: str) -> np.ndarray:
    if name not in DEFENCES:
        raise KeyError(f"unknown defence {name!r}, expected one of {sorted(DEFENCES)}")
    return DEFENCES[name](image)


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--crop", type=int, default=300, help="side of the centre crop shown per tile, 0 for the whole photo")
    args = parser.parse_args()
    out = args.out or Path("results") / f"defences_{args.image.stem}.png"

    image = load_rgb(args.image)
    tiles = []
    for name in DEFENCES:
        result = apply_defence(image, name)
        assert result.shape == image.shape and result.dtype == image.dtype, name
        tile = Image.fromarray(result)
        if args.crop:
            cx, cy, half = tile.width // 2, tile.height // 2, args.crop // 2
            tile = tile.crop((cx - half, cy - half, cx + half, cy + half))
        tiles.append((name, tile))
        print(f"{name:10s} ok {result.shape} {result.dtype}")

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


if __name__ == "__main__":
    main()
