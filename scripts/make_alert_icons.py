#!/usr/bin/env python3
"""Build the phone alerts app icons (alerts/icon-*.png) from one source logo.

Added 24/09/2026. The first icons were a plain navy square, which on an
iPhone Home Screen read as "just a navy black". Lou picked the Elevate and
Thrive Gold logo (WordPress media 2237 on the Hub site) instead.

Run by .github/workflows/alert-icons.yml, because the logo lives on the Hub
site and only a GitHub runner can fetch it. Locally:

    python3 scripts/make_alert_icons.py <url-or-path>

iOS fills any transparent pixel of a Home Screen icon with black and rounds
the corners itself, so a logo with transparency is laid on the Hub navy with
a margin that keeps it clear of the rounded corners. An opaque logo already
has its own background and is used edge to edge.

Writes:
  alerts/apple-touch-icon.png  180x180  iPhone Home Screen
  alerts/icon-192.png          192x192  manifest, favicon, notification icon
  alerts/icon-512.png          512x512  manifest, Android splash
"""
import io
import os
import sys
import urllib.request

from PIL import Image

NAVY = (0x0B, 0x1C, 0x33)
MARGIN = 0.12          # each side, as a share of the icon, for transparent logos
SIZES = {"apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alerts")


def load(src):
    if src.startswith("https://"):
        req = urllib.request.Request(src, headers={"User-Agent": "msh-compare-data alert-icons"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return Image.open(io.BytesIO(r.read()))
    return Image.open(src)


def has_transparency(img):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        return img.convert("RGBA").getchannel("A").getextrema()[0] < 255
    return False


def square_master(img, size=1024):
    """One opaque square master; every output size is resized from it."""
    if not has_transparency(img):
        img = img.convert("RGB")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        return img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    logo = img.convert("RGBA")
    box = logo.getchannel("A").getbbox()
    if box:
        logo = logo.crop(box)
    inner = int(size * (1 - 2 * MARGIN))
    scale = min(inner / logo.width, inner / logo.height)
    logo = logo.resize((max(1, round(logo.width * scale)), max(1, round(logo.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), NAVY + (255,))
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return canvas.convert("RGB")


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    master = square_master(load(argv[1]))
    for name, px in SIZES.items():
        path = os.path.normpath(os.path.join(OUT_DIR, name))
        master.resize((px, px), Image.LANCZOS).save(path, "PNG", optimize=True)
        print("wrote", path, "%dx%d" % (px, px))


if __name__ == "__main__":
    main(sys.argv)
