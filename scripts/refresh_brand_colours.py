#!/usr/bin/env python3
"""Sample each supplier's real brand colours from its own logo, and write them
into supplier-seed.json as `brand`.

WHY
---
The Company Report puts the company's own colours behind its name. Hand-picking
those colours is a guess dressed as branding, and it does not scale past the two
companies somebody happened to look at. This reads the actual logo the report
already displays and takes the colours out of it, recording where each came from.

METHOD, AND ITS LIMITS
----------------------
The logo is fetched from the favicon service already used by the report, at the
largest size it serves. Pixels are binned in RGB, and the most common SATURATED,
non-extreme colour wins: white, near-black and grey are excluded because almost
every logo sits on a white square, and picking the background would give every
company the same non-brand. A second, darker shade is derived from the first for
the gradient — that is a presentation choice, not a claim about the brand.

If no saturated colour clears the threshold (a genuinely monochrome logo, or a
favicon that is just a letter on white), the supplier gets NO brand entry and the
report falls back to the house navy. An honest fallback beats a colour we made
up, and "this company's colour is grey" is a claim we cannot support from a
32-pixel favicon.

SUPERSEDED AS THE PREFERRED SOURCE, 18/08/2026 — STILL LIVE FOR THE 95 IT WROTE
------------------------------------------------------------------------------
scripts/refresh_logos.py now fetches each company's ACTUAL BRAND MARK from its
own website, stores it in this repo, and samples the colour from that — a 192px
mark from the company's own site beats a 128px favicon from a third-party
service, and it is written under a contrast rule this script never had. The
Company Report prefers a logo-derived colour over anything this script wrote.

The 95 records here are NOT retired: they cover companies refresh_logos.py could
not reach, and the renderer keeps using them. But they carry no contrast proof,
so app/company-report.js re-checks every shade at the point of use and drops any
that cannot clear its floor. Do not add new colours with this script where
refresh_logos.py can reach the company.

Run:  python3 scripts/refresh_brand_colours.py [--limit N] [--only NAME]
Then: python3 scripts/stamp_notice.py && python3 verify.py
"""
import argparse
import colorsys
import io
import json
import re
import sys
import time
import urllib.request

SEED = "data/supplier-seed.json"
INDEX = "data/supplier-index.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
ICON = "https://www.google.com/s2/favicons?domain=%s&sz=128"
PAUSE = 0.4

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install Pillow")


def domain_for(rec):
    for l in (rec.get("links") or []):
        u = l.get("url") if isinstance(l, dict) else l
        m = re.search(r"https?://([^/]+)", str(u or ""))
        if m:
            host = m.group(1)
            if "gov.uk" in host or "supplychain" in host or "nhs.uk" in host:
                continue
            return host
    img = rec.get("image") or ""
    m = re.search(r"logo\.clearbit\.com/([^/?]+)|domain=([^&]+)", img)
    if m:
        return m.group(1) or m.group(2)
    dd = (rec.get("deepDive") or {}).get("domain")
    return dd or None


def dominant(colours):
    """Most common saturated, mid-luminance colour. None if the logo has none."""
    best, best_n = None, 0
    for (r, g, b), n in colours:
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if s < 0.25:            # grey, white, black — almost always the background
            continue
        if l < 0.12 or l > 0.88:  # near-black or near-white
            continue
        if n > best_n:
            best, best_n = (r, g, b), n
    return best


def darken(rgb, factor=0.62):
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def hexs(rgb):
    return "#%02x%02x%02x" % rgb


def sample(host):
    url = ICON % host
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    px = []
    for r_, g_, b_, a_ in im.getdata():
        if a_ < 200:
            continue
        # Bin to 16 levels per channel so anti-aliased edges group with their colour.
        px.append(((r_ // 16) * 16 + 8, (g_ // 16) * 16 + 8, (b_ // 16) * 16 + 8))
    counts = {}
    for p in px:
        counts[p] = counts.get(p, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1]), len(px), url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    seed = json.load(open(SEED, encoding="utf-8"))
    index = json.load(open(INDEX, encoding="utf-8"))
    idx = {s["name"]: s for s in index.get("suppliers", [])}

    targets = []
    for rec in seed["suppliers"]:
        if args.only and rec["name"] != args.only:
            continue
        merged = dict(idx.get(rec["name"], {}))
        merged.update(rec)
        host = domain_for(merged)
        if host:
            targets.append((rec, host))
    if args.limit:
        targets = targets[:args.limit]

    done = skipped = 0
    for rec, host in targets:
        try:
            colours, n, url = sample(host)
        except Exception as exc:
            print("  skip %s (%s): %s" % (rec["name"], host, exc))
            skipped += 1
            continue
        if n < 40:
            print("  skip %s: favicon too small to sample (%d opaque pixels)" % (rec["name"], n))
            skipped += 1
            continue
        rgb = dominant(colours)
        if not rgb:
            # Monochrome logo. The house navy is the honest fallback.
            print("  skip %s: no saturated colour in the logo" % rec["name"])
            skipped += 1
            continue
        rec["brand"] = {
            "c1": hexs(rgb),
            "c2": hexs(darken(rgb)),
            "source": "sampled from the company's own favicon at %s on %s; c2 is c1 darkened "
                      "for the gradient, not a second brand colour"
                      % (url, time.strftime("%Y-%m-%d")),
        }
        done += 1
        print("  %-38s %s" % (rec["name"][:38], rec["brand"]["c1"]))
        time.sleep(PAUSE)

    with open(SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print("Brand colours written for %d supplier(s); %d skipped (no usable logo colour)."
          % (done, skipped))


if __name__ == "__main__":
    main()
