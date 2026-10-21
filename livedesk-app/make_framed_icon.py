#!/usr/bin/env python3
"""Live Desk app icon: the photo in a bold gold frame (option B, Lou 21/10/2026).

Source photo: assets/icon-photo.png (1024 square). Writes:
  assets/icon-only.png and the iOS AppIcon (opaque 1024, iOS rounds the corners)
  Android legacy and round launcher icons
  Android adaptive layers: gold background, photo inset as a rounded square in
  front, so the gold reads as a frame whatever shape the phone cuts the icon to.
Run from livedesk-app/. Needs Pillow.
"""
from PIL import Image, ImageChops, ImageDraw

GOLD = (0xE0, 0xBE, 0x8E)
GOLD_D = (0xA8, 0x84, 0x2C)
R = 0.2237            # iOS corner radius as a share of the side
SS = 4                # supersample

PHOTO = Image.open('assets/icon-photo.png').convert('RGB')
RES = 'android/app/src/main/res/'
DPI = {'ldpi': 0.75, 'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}


def rrect(n, inset, radius):
    m = Image.new('L', (n, n), 0)
    ImageDraw.Draw(m).rounded_rectangle((inset, inset, n - 1 - inset, n - 1 - inset), radius=max(radius, 1), fill=255)
    return m


def framed(px):
    """Option B at px: photo, gold band 0-58/1024, dark gold edge 58-64/1024."""
    n = px * SS
    img = PHOTO.resize((n, n), Image.LANCZOS)
    r = int(n * R)
    a, b = int(n * 58 / 1024), int(n * 64 / 1024)
    img.paste(Image.new('RGB', (n, n), GOLD), (0, 0), ImageChops.subtract(rrect(n, 0, r), rrect(n, a, r - a)))
    img.paste(Image.new('RGB', (n, n), GOLD_D), (0, 0), ImageChops.subtract(rrect(n, a, r - a), rrect(n, b, r - b)))
    return img.resize((px, px), Image.LANCZOS)


def masked(img, mask):
    out = img.convert('RGBA')
    out.putalpha(mask.resize(img.size, Image.LANCZOS))
    return out


def round_icon(px):
    n = px * SS
    img = PHOTO.resize((n, n), Image.LANCZOS)
    circle = lambda i: (lambda m: (ImageDraw.Draw(m).ellipse((i, i, n - 1 - i, n - 1 - i), fill=255), m)[1])(Image.new('L', (n, n), 0))
    a, b = int(n * 0.07), int(n * 0.078)
    img.paste(Image.new('RGB', (n, n), GOLD), (0, 0), ImageChops.subtract(circle(0), circle(a)))
    img.paste(Image.new('RGB', (n, n), GOLD_D), (0, 0), ImageChops.subtract(circle(a), circle(b)))
    return masked(img.resize((px, px), Image.LANCZOS), circle(0))


def adaptive(px):
    """108dp layers. Visible area is the middle 72dp; the photo is a 54dp rounded square, inside a circle cut too."""
    n = px * SS
    bg = Image.new('RGB', (n, n), GOLD)
    side, rad, edge = n * 54 / 108, n * 14 / 108, max(1, round(n * 1.2 / 108))
    o = int((n - side) / 2)
    s = int(side)
    fg = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    edge_img = Image.new('RGBA', (s + 2 * edge, s + 2 * edge), GOLD_D + (255,))
    fg.paste(edge_img, (o - edge, o - edge), rrect(s + 2 * edge, 0, int(rad + edge)))
    fg.paste(PHOTO.resize((s, s), Image.LANCZOS), (o, o), rrect(s, 0, int(rad)))
    return bg.resize((px, px), Image.LANCZOS), fg.resize((px, px), Image.LANCZOS)


big = framed(1024)
big.save('assets/icon-only.png')
big.save('ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png')
for d, k in DPI.items():
    leg = round(48 * k)
    masked(framed(leg), rrect(leg * SS, 0, int(leg * SS * 0.18))).save(f'{RES}mipmap-{d}/ic_launcher.png')
    round_icon(leg).save(f'{RES}mipmap-{d}/ic_launcher_round.png')
    bg, fg = adaptive(round(108 * k))
    bg.save(f'{RES}mipmap-{d}/ic_launcher_background.png')
    fg.save(f'{RES}mipmap-{d}/ic_launcher_foreground.png')
print('icons written')
