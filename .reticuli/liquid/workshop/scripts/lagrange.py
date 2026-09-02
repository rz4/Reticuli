"""Draw the L1 Lagrange point between ζ¹ and ζ² Reticuli on the logo.

The metaphor, made literal. The two stars are two realizations of one claim —
two mass wells. Each star's "mass" is read from its own luminous footprint in
the image; the inner Lagrange point L1 is the balance between them
(m1/r1² = m2/r2²), the saddle from which a test mass falls into either well.
That saddle is where the *spec* sits: massless next to the implementations,
reproducible into either. The minimal-USD realization is the spec arriving at
L1 — trivial cost, then downhill to a valid star.

    python3 scripts/lagrange.py [out.png]
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = "logo.png"
OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/experiments/basin_lagrange.png"
SCALE = 3


def star_centers(dark: np.ndarray) -> tuple:
    h, w = dark.shape
    yy, xx = np.mgrid[0:h, 0:w]

    def peak(d):
        i = int(d.argmax())
        return i % w, i // w                          # x, y

    x1, y1 = peak(dark)
    d2 = dark.copy()
    d2[(yy - y1) ** 2 + (xx - x1) ** 2 < 45 ** 2] = 0
    x2, y2 = peak(d2)
    return (x1, y1), (x2, y2)


def mass(dark: np.ndarray, cx: int, cy: int, r: int = 38) -> float:
    """Luminous footprint = integrated darkness in a disk — the well's depth."""
    h, w = dark.shape
    yy, xx = np.mgrid[0:h, 0:w]
    disk = (yy - cy) ** 2 + (xx - cx) ** 2 < r ** 2
    return float(dark[disk].sum())


def main() -> int:
    g = np.asarray(Image.open(SRC).convert("L"), float)
    dark = 255 - g
    (x1, y1), (x2, y2) = star_centers(dark)
    m1, m2 = mass(dark, x1, y1), mass(dark, x2, y2)

    # L1 on the segment: the gravitational null, r1/r2 = sqrt(m1/m2), so the
    # saddle leans toward the lighter well.
    t = np.sqrt(m1) / (np.sqrt(m1) + np.sqrt(m2))     # fraction from star1 -> star2
    lx, ly = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
    ratio = m2 / m1

    im = Image.open(SRC).convert("RGB").resize(
        (g.shape[1] * SCALE, g.shape[0] * SCALE), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    S = SCALE
    amber, ink = (198, 122, 0), (40, 40, 40)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Courier New.ttf", 15 * S)
        small = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Courier New.ttf", 10 * S)
    except OSError:
        font = small = ImageFont.load_default()

    def ring(x, y, r, color, width=2):
        d.ellipse([(x * S - r, y * S - r), (x * S + r, y * S + r)],
                  outline=color, width=width * S)

    # the line between the wells, the two stars, and the saddle
    d.line([(x1 * S, y1 * S), (x2 * S, y2 * S)], fill=ink, width=1 * S)
    ring(x1, y1, 10 * S, ink, 1)
    ring(x2, y2, 10 * S, ink, 1)
    d.text((x1 * S + 12 * S, y1 * S - 20 * S), "ζ¹", font=font, fill=ink)
    d.text((x2 * S + 12 * S, y2 * S + 6 * S), "ζ²", font=font, fill=ink)

    r = 7 * S                                          # the L1 mark: an amber cross-in-ring
    d.line([(lx * S - r, ly * S), (lx * S + r, ly * S)], fill=amber, width=2 * S)
    d.line([(lx * S, ly * S - r), (lx * S, ly * S + r)], fill=amber, width=2 * S)
    ring(lx, ly, 10 * S, amber, 2)
    d.text((lx * S + 14 * S, ly * S - 8 * S), "L1", font=font, fill=amber)
    d.text((lx * S + 14 * S, ly * S + 8 * S), "the spec", font=small, fill=amber)

    im.save(OUT)
    print(f"stars  ζ¹ ({x1},{y1})  ζ² ({x2},{y2})   mass ratio m2/m1 = {ratio:.3f}")
    print(f"L1     ({lx:.1f},{ly:.1f})   {t*100:.1f}% from ζ¹ toward ζ²")
    print(f"wrote  {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
