#!/usr/bin/env python3
"""Draws the Live Desk app icon and splash into assets/ (01/10/2026).

The Elevate and Thrive logo's lettering is unreadable at app-icon size, so the
icon is its rising bars and arrow (the same shapes as the phone alerts badge,
scripts/make_alert_icons.py) in Hub gold on Hub navy, drawn large and scaled
down for smooth edges. `npx capacitor-assets generate` turns these into every
iOS and Android size. Needs Pillow.
"""
from PIL import Image, ImageDraw

NAVY = (0x0B, 0x1C, 0x33, 255)
GOLD = (0xE0, 0xBE, 0x8E, 255)


def mark(n, colour):
    """Bars and arrow on transparent, in a 96-unit grid scaled to n."""
    u = n / 96.0
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = 88 * u
    for i, top in enumerate((66, 56, 44, 30)):
        x = (10 + i * 20) * u
        d.rounded_rectangle((x, top * u, x + 14 * u, base), radius=3 * u, fill=colour)
    d.line(((8 * u, 50 * u), (40 * u, 34 * u), (76 * u, 12 * u)), fill=colour,
           width=round(6 * u), joint="curve")
    d.polygon(((88 * u, 4 * u), (64 * u, 6 * u), (80 * u, 26 * u)), fill=colour)
    return img


def icon(px=1024, share=0.62, ss=4):
    n = px * ss
    img = Image.new("RGBA", (n, n), NAVY)
    m = mark(int(n * share), GOLD)
    off = (n - m.width) // 2
    img.alpha_composite(m, (off, off))
    return img.resize((px, px), Image.LANCZOS)


def splash(px=2732):
    img = Image.new("RGBA", (px, px), NAVY)
    m = mark(int(px * 0.18), GOLD)
    img.alpha_composite(m, ((px - m.width) // 2, (px - m.height) // 2))
    return img


if __name__ == "__main__":
    icon().convert("RGB").save("assets/icon-only.png")
    fg = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    m = mark(int(1024 * 0.42), GOLD)
    fg.alpha_composite(m, ((1024 - m.width) // 2, (1024 - m.height) // 2))
    fg.save("assets/icon-foreground.png")
    Image.new("RGB", (1024, 1024), NAVY[:3]).save("assets/icon-background.png")
    s = splash().convert("RGB")
    s.save("assets/splash.png")
    s.save("assets/splash-dark.png")
    print("wrote assets/")
