"""Build Alexa store icons from 4NextDartIcon.jpg (stylized DART front).

Small: 108x108 PNG. Large: 512x512 PNG. The source is already a square icon,
so it is scaled to fill the canvas (no extra padding).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "4NextDartIcon.jpg"
OUT_DIR = ROOT / "skill-package" / "assets" / "images"
DOCS_DIR = ROOT / "docs" / "icons"


def fit_square(im: Image.Image, size: int) -> Image.Image:
    rgb = im.convert("RGB")
    return rgb.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}; add 4NextDartIcon.jpg and re-run")
    src = Image.open(SRC)
    specs = {
        "en-GB_smallIcon.png": 108,
        "en-GB_largeIcon.png": 512,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for name, size in specs.items():
        out = fit_square(src, size)
        for dest in (OUT_DIR / name, DOCS_DIR / name):
            out.save(dest, "PNG", optimize=True)
            print(f"wrote {dest} {out.size} {out.mode}")


if __name__ == "__main__":
    main()
