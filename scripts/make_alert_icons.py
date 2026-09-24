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
  alerts/badge-96.png           96x96   Android status-bar badge

The badge is drawn here, not taken from the logo. Android paints a badge
from its transparency alone, in white, at about 24 pixels: the logo there is
a blank square (what members saw until 24/09/2026) and its lettering would
be mush. It is the logo's rising bars and arrow as a white silhouette.
Rebuild just the badge with:

    python3 scripts/make_alert_icons.py --badge
"""
import io
import os
import sys
import urllib.request

from PIL import Image, ImageDraw

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


def badge(px=96, ss=8):
    """White bars-and-arrow silhouette on transparent, drawn large and scaled
    down so the edges are smooth."""
    n = px * ss
    u = n / 96.0
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    base = 88 * u
    for i, top in enumerate((66, 56, 44, 30)):          # four rising bars
        x = (10 + i * 20) * u
        d.rounded_rectangle((x, top * u, x + 14 * u, base), radius=3 * u, fill=white)
    d.line(((8 * u, 50 * u), (40 * u, 34 * u), (76 * u, 12 * u)), fill=white,
           width=round(6 * u), joint="curve")               # the arrow's shaft
    d.polygon(((88 * u, 4 * u), (64 * u, 6 * u), (80 * u, 26 * u)), fill=white)
    return img.resize((px, px), Image.LANCZOS)


def write_badge():
    path = os.path.normpath(os.path.join(OUT_DIR, "badge-96.png"))
    badge().save(path, "PNG", optimize=True)
    print("wrote", path, "96x96")


def main(argv):
    if len(argv) == 2 and argv[1] == "--badge":
        write_badge()
        return
    if len(argv) != 2:
        sys.exit(__doc__)
    master = square_master(load(argv[1]))
    for name, px in SIZES.items():
        path = os.path.normpath(os.path.join(OUT_DIR, name))
        master.resize((px, px), Image.LANCZOS).save(path, "PNG", optimize=True)
        print("wrote", path, "%dx%d" % (px, px))
    write_badge()


if __name__ == "__main__":
    main(sys.argv)
