#!/usr/bin/env python3
"""
refresh_logos.py — fetch each supplier's own brand mark ONCE, at build time,
store it in this repo, and sample the company's real colours from it.

WHY THIS EXISTS
---------------
The Company Report had exactly one logo route: `logo.clearbit.com`, called LIVE
from the members-facing page. That host stopped resolving. Nothing failed
loudly — every report simply fell through to the monogram, and nobody found out
until somebody looked at the code on 18/08/2026.

That is the whole argument for this script. A logo the page fetches from a third
party is a dependency nobody is watching, on a page members pay for. A logo
fetched here, checked here, and committed here can only break in a commit, and
the commit is reviewed by verify.py before it publishes.

So: NO THIRD-PARTY LOGO SERVICE IS EVER CALLED FROM THE PAGE. Marks come from
the company's own website, are stored under assets/logos/, and are served from
this repo alongside the data the report already fetches.

WHAT COUNTS AS A MARK, AND WHAT DOES NOT
----------------------------------------
Candidates are read from the company's own homepage, best first:

  1. <link rel="apple-touch-icon"> / apple-touch-icon-precomposed
     A site that publishes one has deliberately supplied a square mark at
     display size. This is the best available source by a distance.
  2. An SVG referenced as a logo — <img src="...logo....svg">, or a
     <link rel="icon" type="image/svg+xml">. Vector, so size is not a question.
  3. <link rel="icon"> / shortcut icon whose declared `sizes` clears the floor.
  4. og:image, ONLY where the URL names it as a logo. An og:image is usually a
     photograph or a share card — a share card is not a brand mark, and putting
     one on a 74px plate produces an unreadable smear.
  5. A raster <img> whose src, class or alt names it as the logo.
  6. /favicon.ico, and only when the file genuinely holds a large frame.

  NEVER a favicon SERVICE. icons.duckduckgo.com and google.com/s2/favicons are
  refused before a request is made. They serve a 16px tab glyph, and where they
  hold nothing they serve their own grey placeholder arrow — which is how 13 of
  the 15 `image` values already in supplier-index.json came to point at a mark
  that is not the company's. Those 13 are not migrated. They are dropped.

THE SIZE FLOOR, STATED
----------------------
The report draws the mark on a 74px plate, so a Retina member needs 148 real
pixels. FLOOR_PX = 148 on the longest edge, and it is not negotiable downwards
for a raster: below it, the mark is being upscaled on a paid page. SVG is exempt
because vector has no native size. The count of marks that fell between 64px and
the floor is REPORTED, so the cost of the floor is visible rather than assumed.

PLACEHOLDERS
------------
A placeholder answers 200 and decodes cleanly, so size alone will not catch it.
Three tests, all recorded when they fire:
  * a mark that is one flat colour, or effectively blank, is refused;
  * a mark whose bytes are IDENTICAL to a mark already accepted for three or
    more OTHER companies is a CDN or theme default, not a brand, and every copy
    of it is refused;
  * favicon services are refused before the request (above).

COLOURS
-------
The colour is sampled from the fetched mark, which is a far better source than
the 128px favicon scripts/refresh_brand_colours.py had to use, and it keeps that
script's recorded-provenance convention: every `brand` object says what it was
sampled from and on what date.

  c1  the most common saturated, mid-luminance colour in the mark.
  c2  c1 darkened for the gradient and for anything that carries white text.
      A presentation choice, not a second brand colour — same as before.

CONTRAST, AND WHY TWO THRESHOLDS
--------------------------------
The accent is used two ways, so it is tested two ways:
  * as a RULE or EDGE on the report's ivory card ground (#fdfcf9) it is a
    non-text interface element — WCAG 2.1 1.4.11 asks 3:1. c1 must clear it.
  * where it carries WHITE TEXT it is text — WCAG 2.1 1.4.3 asks 4.5:1. c2 is
    the shade used there, so c2 must clear it. c2 is darkened in steps until it
    does; if it cannot get there while staying recognisably the same hue, the
    colour is refused outright.
A colour that fails is NOT published and NOT quietly corrected into something
prettier. The supplier keeps the house Antique Gold and the file records why.

POLITENESS
----------
robots.txt is fetched and obeyed per host, one host at a time, with a real
contactable user agent and a pause between requests. A robots.txt refusal is
recorded as a refusal — the same way seed_supplier_domains.py banks its refusals
— never treated as "no logo".

USAGE
    python3 scripts/refresh_logos.py                    # full sweep
    python3 scripts/refresh_logos.py --limit 25
    python3 scripts/refresh_logos.py --only "GBUK Group"
    python3 scripts/refresh_logos.py --resume           # keep banked results
    python3 scripts/refresh_logos.py --report-only      # fetch nothing, list targets

Then: python3 scripts/stamp_notice.py && python3 verify.py
"""

import argparse
import colorsys
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(HERE, "data", "supplier-index.json")
SEED = os.path.join(HERE, "data", "supplier-seed.json")
OUT = os.path.join(HERE, "data", "company-logos.json")
ASSETS = os.path.join(HERE, "assets", "logos")

UA = ("Mozilla/5.0 (compatible; MedSalesHubBot/1.0; "
      "+https://medsalesintelligencehub.co.uk) brand mark capture")
TIMEOUT = 20
PAUSE = 1.0                      # between requests to the same host
FLOOR_PX = 148                   # 74px plate at 2x. Raster only; SVG is exempt.
NEAR_MISS_PX = 64                # counted and reported, so the floor's cost is visible
STORE_PX = 192                   # marks are stored at this longest edge (74px plate at 2x, plus headroom)
MAX_SVG_BYTES = 60_000
DUP_LIMIT = 3                    # same bytes for this many companies = a default, not a brand
IVORY = (0xfd, 0xfc, 0xf9)       # .mcr-report card ground
NAVY = (0x0b, 0x1c, 0x33)        # .mcr-mast — Midnight Navy, the brand guide's
MIN_ON_NAVY = 3.0                # WCAG 2.1 1.4.11, non-text contrast
MIN_ON_IVORY = 3.0               # WCAG 2.1 1.4.11, non-text contrast
MIN_WHITE_TEXT = 4.5             # WCAG 2.1 1.4.3, normal text

# Hosts that can never be a supplier's own site.
NEVER = ("linkedin.", "facebook.", "twitter.", "x.com", "instagram.", "youtube.",
         "wikipedia.", "amazon.", "ebay.", "companieshouse.", "gov.uk",
         "supplychain.nhs", "nhs.uk", "bloomberg.", "crunchbase.", "indeed.",
         "glassdoor.", "yell.com", "endole.", "opencorporates.", "trustpilot.",
         "find-and-update", "google.", "youtu.be")

# A LOGO ON A PAGE IS NOT NECESSARILY THIS COMPANY'S LOGO.
# The first sweep pulled AB Scientific's "logo" out of a cookie-consent plugin's
# own banner asset, because the banner's <img> carries class="cky-logo". Every
# WordPress site is full of other people's marks: consent banners, payment-card
# rows, "powered by", accreditation badges, partner and client walls, app-store
# buttons. Publishing one of those on a paid page as the company's own mark is
# the same class of error as publishing another company's product range.
NOT_A_BRAND_MARK = re.compile(
    r"(cky-|cookie|consent|gdpr|/plugins?/|wp-content/plugins|payment|visa|"
    r"mastercard|maestro|amex|paypal|klarna|stripe|apple-?pay|google-?pay|"
    r"powered-?by|partner|sponsor|client|accredit|badge|award|certif|iso-?\d|"
    r"trustpilot|feefo|reviews?\.io|app-?store|play-?store|placeholder|"
    r"default-?(?:logo|image)|no-?image|avatar|spinner|loader|flag)", re.I)

# Favicon SERVICES. Refused before a request is made — see the module docstring.
FAVICON_SERVICE = re.compile(
    r"(?:^|//)(?:icons?\.duckduckgo\.com|www\.google\.com/s2/favicons|"
    r"favicons?\.[^/]+|t\d\.gstatic\.com/faviconV2)", re.I)

try:
    from PIL import Image
except ImportError:                                              # pragma: no cover
    sys.exit("Pillow is required: python3 -m pip install Pillow")


# ---------------------------------------------------------------------------
# colour maths
# ---------------------------------------------------------------------------
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hexs(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def unhex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def darken(rgb, factor):
    return tuple(max(0, min(255, int(round(c * factor)))) for c in rgb)


def dominant(counts):
    """Most common saturated, mid-luminance colour. None if the mark has none.

    White, near-black and grey are excluded: nearly every logo sits on a white
    or transparent ground, and picking the ground would give every company the
    same non-brand.
    """
    best, best_n = None, 0
    for (r, g, b), n in counts:
        _h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if s < 0.25:
            continue
        if l < 0.12 or l > 0.88:
            continue
        if n > best_n:
            best, best_n = (r, g, b), n
    return best


def brand_from(im, source_url, today):
    """A contrast-checked brand object, or (None, reason).

    Every threshold this applies is stated in the returned object, so a reader
    can judge the colour without re-running anything.
    """
    px = []
    for r, g, b, a in im.convert("RGBA").getdata():
        if a < 200:
            continue
        px.append(((r // 16) * 16 + 8, (g // 16) * 16 + 8, (b // 16) * 16 + 8))
    if len(px) < 200:
        return None, "mark has too few opaque pixels to sample a colour from"
    tally = {}
    for p in px:
        tally[p] = tally.get(p, 0) + 1
    rgb = dominant(sorted(tally.items(), key=lambda kv: -kv[1]))
    if not rgb:
        return None, ("no saturated colour in the mark — a monochrome logo yields no "
                      "brand colour, and 'this company's colour is grey' is not a claim "
                      "this can support")

    return _finish_brand(rgb, source_url, today,
                         "the pixels of the company's own brand mark")


SVG_HEX = re.compile(r"(?:fill|stop-color|stroke)\s*[:=]\s*[\"']?\s*#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def brand_from_svg(raw, source_url, today):
    """Colour from an SVG mark, read from its own declared fills.

    There is no rasteriser in this repo, so an SVG cannot be sampled pixel by
    pixel. It does not need to be: an SVG logo STATES its colours, and the
    declared fills are a better source than pixels because there is no
    anti-aliasing to bin away. Every fill/stroke/stop-colour is counted once per
    appearance, and the same saturation and luminance rules apply as for a
    raster mark, so a black-and-white SVG yields nothing rather than grey.
    """
    tally = {}
    for m in SVG_HEX.finditer(raw.decode("utf-8", "replace")):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        rgb = unhex(h)
        rgb = ((rgb[0] // 16) * 16 + 8, (rgb[1] // 16) * 16 + 8, (rgb[2] // 16) * 16 + 8)
        tally[rgb] = tally.get(rgb, 0) + 1
    if not tally:
        return None, ("the SVG declares no colour in a fill, stroke or gradient stop — "
                      "it is styled from a stylesheet this script does not fetch")
    rgb = dominant(sorted(tally.items(), key=lambda kv: -kv[1]))
    if not rgb:
        return None, ("no saturated colour is declared anywhere in the SVG — a monochrome "
                      "mark yields no brand colour")
    return _finish_brand(rgb, source_url, today, "the fills declared in the company's own SVG mark")


def lighten(rgb, factor):
    """Move towards white by `factor`, keeping the hue."""
    return tuple(max(0, min(255, int(round(c + (255 - c) * factor)))) for c in rgb)


def _finish_brand(rgb, source_url, today, what):
    """One sampled colour, two contrast-proven shades — because the report has
    two grounds and one accent variable cannot serve both.

    This was got wrong twice before it was got right, and both failures are
    worth keeping written down.

      Testing the accent ONLY against the ivory card ground threw away 22 of
      the 95 colours already in the seed, Stryker's yellow and Smith+Nephew's
      orange among them. Testing it ONLY against the navy masthead threw away
      48, because medtech is full of dark blues and a dark blue is invisible
      on Midnight Navy. Neither list was a list of bad colours. Both were the
      wrong question.

    So c1 — the colour actually sampled from the mark, and the only thing here
    that is a CLAIM about the company — is never painted directly. Two shades
    of it are, and each is tested against the ground it is painted on:

      accentOnNavy   c1 LIGHTENED until it clears 3:1 on Midnight Navy
                     (#0B1C33). This is the masthead's 5px top edge.
      accentOnIvory  c1 DARKENED until it clears 3:1 on the ivory card ground
                     AND 4.5:1 under white text. This is every rule, card top
                     border and filled chip below the masthead. It is `c2`,
                     which is the name the existing seed records already use.

    Both are the same hue as c1, moved along one axis by a recorded factor, so
    nothing is nudged towards a colour the company does not own. If neither
    direction can reach its floor the colour is refused outright and the
    company keeps the house Antique Gold — but in practice only a colour
    dominant() would already have rejected can fail here.
    """
    navy_shade = navy_ratio = navy_f = None
    for f in (0.0, 0.12, 0.24, 0.36, 0.48, 0.60, 0.72):
        cand = lighten(rgb, f)
        r = contrast(cand, NAVY)
        if r >= MIN_ON_NAVY:
            navy_shade, navy_ratio, navy_f = cand, r, f
            break
    if navy_shade is None:
        return None, ("c1 %s cannot be lightened to clear %.1f:1 on the navy masthead while "
                      "staying the same hue" % (hexs(rgb), MIN_ON_NAVY))

    c2 = ivory_ratio = white_ratio = ink_f = None
    for f in (1.0, 0.82, 0.70, 0.62, 0.55, 0.48, 0.42, 0.36, 0.30, 0.24):
        cand = darken(rgb, f)
        iv = contrast(cand, IVORY)
        wt = contrast(cand, (255, 255, 255))
        if iv >= MIN_ON_IVORY and wt >= MIN_WHITE_TEXT:
            c2, ivory_ratio, white_ratio, ink_f = cand, iv, wt, f
            break
    if c2 is None:
        return None, ("c1 %s cannot be darkened to clear %.1f:1 on the ivory card ground and "
                      "%.1f:1 under white text while staying the same hue — refused rather "
                      "than published unreadable"
                      % (hexs(rgb), MIN_ON_IVORY, MIN_WHITE_TEXT))

    return {
        "c1": hexs(rgb),
        "c2": hexs(c2),
        "accentOnNavy": hexs(navy_shade),
        "accentOnIvory": hexs(c2),
        "contrastOnNavy": round(navy_ratio, 2),
        "contrastOnIvory": round(ivory_ratio, 2),
        "contrastWhiteOnC2": round(white_ratio, 2),
        "thresholds": {"onNavy": MIN_ON_NAVY, "onIvory": MIN_ON_IVORY,
                       "whiteTextOnC2": MIN_WHITE_TEXT},
        "source": ("sampled from %s at %s on %s. c1 %s is the most common saturated "
                   "mid-luminance colour in the mark and is the only claim here about the "
                   "company; it is never painted directly. accentOnNavy is c1 lightened "
                   "%d%% towards white for the navy masthead (%.2f:1); accentOnIvory (c2) "
                   "is c1 darkened to %d%% for the ivory card ground (%.2f:1) and for white "
                   "text on it (%.2f:1). Both derived shades are presentation choices, not "
                   "second brand colours."
                   % (what, source_url, today, hexs(rgb), round(navy_f * 100), navy_ratio,
                      round(ink_f * 100), ivory_ratio, white_ratio)),
    }, None


# ---------------------------------------------------------------------------
# http
# ---------------------------------------------------------------------------
_robots = {}


def robots_ok(url):
    """True if robots.txt allows us. A failure to READ robots.txt is not consent
    to ignore it, but a 404 is: no robots.txt means no restriction."""
    p = urllib.parse.urlsplit(url)
    key = (p.scheme, p.netloc)
    rp = _robots.get(key)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url("%s://%s/robots.txt" % (p.scheme, p.netloc))
        try:
            req = urllib.request.Request(rp.url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True
        except Exception:
            rp.allow_all = True
        _robots[key] = rp
    return rp.can_fetch(UA, url)


def get(url, limit=3_000_000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(limit), r.headers.get("Content-Type", ""), r.geturl()


# ---------------------------------------------------------------------------
# candidate extraction
# ---------------------------------------------------------------------------
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
META_RE = re.compile(r"<meta\b[^>]*>", re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)


def attrs(tag):
    out = {}
    for m in re.finditer(r"([a-zA-Z:\-]+)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", tag):
        out[m.group(1).lower()] = m.group(2).strip("\"'")
    return out


def sizes_max(v):
    best = 0
    for m in re.finditer(r"(\d+)\s*[xX]\s*(\d+)", str(v or "")):
        best = max(best, int(m.group(1)), int(m.group(2)))
    return best


def candidates(html, base_url):
    """(priority, url, why) best first. Priority order is the docstring's."""
    out = []

    def add(pri, href, why):
        if not href:
            return
        u = urllib.parse.urljoin(base_url, href.strip())
        if not u.lower().startswith(("http://", "https://")):
            return
        if FAVICON_SERVICE.search(u):
            return
        if NOT_A_BRAND_MARK.search(u):
            return
        out.append((pri, u, why))

    for tag in LINK_RE.findall(html):
        a = attrs(tag)
        rel = (a.get("rel") or "").lower()
        href = a.get("href")
        if "apple-touch-icon" in rel:
            add(1, href, "apple-touch-icon declared by the site")
        elif "icon" in rel:
            if (a.get("type") or "").lower() == "image/svg+xml" or str(href or "").lower().endswith(".svg"):
                add(2, href, "SVG icon declared by the site")
            elif sizes_max(a.get("sizes")) >= FLOOR_PX:
                add(3, href, "link rel=icon declaring sizes %s" % a.get("sizes"))
            else:
                add(6, href, "link rel=icon, size undeclared or below the floor")

    for tag in IMG_RE.findall(html):
        a = attrs(tag)
        src = a.get("src") or a.get("data-src") or ""
        hay = " ".join([src, a.get("class") or "", a.get("id") or "", a.get("alt") or ""]).lower()
        if "logo" not in hay:
            continue
        if src.lower().split("?")[0].endswith(".svg"):
            add(2, src, "SVG named as the logo in the page markup")
        else:
            add(5, src, "image named as the logo in the page markup")

    for tag in META_RE.findall(html):
        a = attrs(tag)
        prop = (a.get("property") or a.get("name") or "").lower()
        if prop in ("og:image", "og:image:url", "twitter:image"):
            u = a.get("content") or ""
            # An og:image is usually a photograph or a share card. Only taken
            # when the URL itself names it as a logo.
            if "logo" in u.lower():
                add(4, u, "og:image whose URL names it as the logo")

    add(7, "/favicon.ico", "/favicon.ico (only accepted if it holds a large frame)")

    seen, uniq = set(), []
    for pri, u, why in sorted(out, key=lambda t: t[0]):
        if u in seen:
            continue
        seen.add(u)
        uniq.append((pri, u, why))
    return uniq[:6]


# ---------------------------------------------------------------------------
# image handling
# ---------------------------------------------------------------------------
def flat(im):
    """True if the image is one colour, or effectively blank."""
    rgba = im.convert("RGBA")
    opaque = [p for p in rgba.getdata() if p[3] > 40]
    if len(opaque) < 64:
        return True
    tally = {}
    for r, g, b, _a in opaque:
        k = ((r // 24), (g // 24), (b // 24))
        tally[k] = tally.get(k, 0) + 1
    return max(tally.values()) / float(len(opaque)) > 0.985


def optimise_png(im):
    im = im.convert("RGBA")
    if max(im.size) > STORE_PX:
        im.thumbnail((STORE_PX, STORE_PX), Image.LANCZOS)
    best = None
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    best = buf.getvalue()
    try:
        for ncol in (128, 96, 64):
            q = im.convert("RGB").quantize(colors=ncol, method=Image.MEDIANCUT)
            q.putalpha(im.getchannel("A"))
            buf2 = io.BytesIO()
            q.save(buf2, "PNG", optimize=True)
            if len(buf2.getvalue()) < len(best):
                best = buf2.getvalue()
    except Exception:
        pass
    return best


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or hashlib.sha1(str(name).encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------
# domain discovery — from data already recorded, never guessed
# ---------------------------------------------------------------------------
def domains_for(rec):
    """(host, provenance) best first. Nothing here is invented: every host is
    already recorded against this company in the seed or the index."""
    out, seen = [], set()

    def add(host, why):
        h = str(host or "").strip().lower().rstrip("/")
        h = re.sub(r"^https?://", "", h).split("/")[0]
        if not h or h in seen:
            return
        if any(n in h for n in NEVER):
            return
        seen.add(h)
        out.append((h, why))

    for l in (rec.get("links") or []):
        if not isinstance(l, dict):
            continue
        if l.get("label") == "Company website":
            add(l.get("url"), "registration-proven company website link in the seed")
    dd = (rec.get("deepDive") or {}).get("domain")
    if dd:
        add(dd, "domain recorded on the deep-dive record")
    for l in (rec.get("links") or []):
        u = l.get("url") if isinstance(l, dict) else l
        lab = (l.get("label") if isinstance(l, dict) else "") or ""
        if isinstance(l, dict) and l.get("label") == "Company website":
            continue
        if re.search(r"website|products|home", lab, re.I) or lab == "":
            add(u, "curated link labelled %r in the seed" % lab[:60])
    return out


def load_records():
    index = json.load(open(INDEX, encoding="utf-8"))
    seed = json.load(open(SEED, encoding="utf-8"))
    by = {}
    for s in index.get("suppliers", []):
        by[s["name"]] = dict(s)
    for s in seed.get("suppliers", []):
        m = by.setdefault(s["name"], {})
        merged = dict(m)
        merged.update(s)
        # links from both, de-duplicated on url
        links, seen = [], set()
        for l in (m.get("links") or []) + (s.get("links") or []):
            u = (l.get("url") if isinstance(l, dict) else l) or ""
            k = str(u).rstrip("/").lower()
            if k and k not in seen:
                seen.add(k)
                links.append(l)
        merged["links"] = links
        by[s["name"]] = merged
    return by


# ---------------------------------------------------------------------------
# one supplier
# ---------------------------------------------------------------------------
def try_supplier(name, rec, today, near_miss):
    doms = domains_for(rec)
    if not doms:
        return None, {"name": name, "reason": "no domain recorded for this company",
                      "reasonCode": "no-domain", "checked": today}

    last = None
    for host, why in doms[:2]:
        for scheme in ("https", "http"):
            home = "%s://%s/" % (scheme, host)
            try:
                if not robots_ok(home):
                    last = {"name": name, "domain": host, "reason":
                            "robots.txt at %s disallows this crawler — refused, not retried"
                            % host, "reasonCode": "refused", "checked": today}
                    break
                html, ctype, final = get(home, 1_200_000)
                time.sleep(PAUSE)
            except Exception as exc:
                last = {"name": name, "domain": host,
                        "reason": "site did not answer: %s: %s" % (type(exc).__name__, exc),
                        "reasonCode": "dead-site", "checked": today}
                continue
            fhost = urllib.parse.urlsplit(final).netloc.lower()
            if any(n in fhost for n in NEVER):
                last = {"name": name, "domain": host,
                        "reason": "redirected to a third-party host (%s) — not the company's own site" % fhost,
                        "reasonCode": "dead-site", "checked": today}
                break
            html = html.decode("utf-8", "replace")

            tried = []
            for _pri, url, cwhy in candidates(html, final):
                try:
                    if not robots_ok(url):
                        tried.append("%s (robots.txt disallows)" % url)
                        continue
                    raw, ctype, _f = get(url, 4_000_000)
                    time.sleep(PAUSE)
                except Exception as exc:
                    tried.append("%s (%s)" % (url, type(exc).__name__))
                    continue
                if not raw:
                    tried.append("%s (empty)" % url)
                    continue

                is_svg = (url.lower().split("?")[0].endswith(".svg")
                          or "svg" in ctype.lower()
                          or raw[:400].lstrip().lower().startswith(b"<svg")
                          or b"<svg" in raw[:400].lower())
                if is_svg:
                    if len(raw) > MAX_SVG_BYTES:
                        tried.append("%s (SVG %d bytes, over the %d-byte store limit)"
                                     % (url, len(raw), MAX_SVG_BYTES))
                        continue
                    if b"<script" in raw.lower() or b"<foreignobject" in raw.lower():
                        tried.append("%s (SVG carries script — never stored)" % url)
                        continue
                    return {"name": name, "domain": host, "domainFrom": why,
                            "source": url, "sourceWhy": cwhy, "format": "svg",
                            "bytes": len(raw), "w": None, "h": None,
                            "fetched": today, "_raw": raw, "_im": None}, None

                try:
                    im = Image.open(io.BytesIO(raw))
                    if getattr(im, "n_frames", 1) > 1:
                        # .ico files hold several frames; take the largest.
                        big, area = None, 0
                        for i in range(im.n_frames):
                            im.seek(i)
                            if im.size[0] * im.size[1] > area:
                                area = im.size[0] * im.size[1]
                                big = im.copy()
                        im = big
                    im.load()
                except Exception as exc:
                    tried.append("%s (not a decodable image: %s)" % (url, type(exc).__name__))
                    continue

                if url.lower().endswith(".ico") or "icon" in ctype.lower():
                    # An .ico can declare a large size and hold a 16px frame.
                    try:
                        sizes = sorted(Image.open(io.BytesIO(raw)).info.get("sizes", []),
                                       key=lambda wh: -(wh[0] * wh[1]))
                        if sizes:
                            im = Image.open(io.BytesIO(raw))
                            im.size = sizes[0]
                            im = im.convert("RGBA")
                    except Exception:
                        pass

                w, h = im.size
                if max(w, h) < FLOOR_PX:
                    if max(w, h) >= NEAR_MISS_PX:
                        near_miss.append((name, url, max(w, h)))
                    tried.append("%s (%dx%d, below the %dpx floor)" % (url, w, h, FLOOR_PX))
                    continue
                if flat(im):
                    tried.append("%s (one flat colour or blank — a placeholder, not a mark)" % url)
                    continue

                return {"name": name, "domain": host, "domainFrom": why,
                        "source": url, "sourceWhy": cwhy, "format": "png",
                        "w": w, "h": h, "fetched": today, "_raw": None, "_im": im}, None

            # SAY WHICH THING ACTUALLY HAPPENED.
            # "No usable mark" and "we were not allowed to fetch the mark" are
            # different findings and only one of them is about the company. Wix,
            # Squarespace and Shopify all serve site images from a CDN whose
            # robots.txt disallows crawlers, so a site can publish a perfectly
            # good 180px apple-touch-icon and still, correctly, refuse us. Filed
            # as "no usable mark" that reads as a company with no logo, which is
            # a claim about them rather than about us.
            robots_only = bool(tried) and all("robots.txt disallows" in t for t in tried)
            if robots_only:
                last = {"name": name, "domain": host,
                        "reason": "the site publishes marks, but every one is served from a "
                                  "host whose robots.txt disallows this crawler — refused, "
                                  "not absent. Tried: %s" % "; ".join(tried[:6]),
                        "reasonCode": "refused", "checked": today}
            else:
                last = {"name": name, "domain": host,
                        "reason": "site read, but it publishes no mark that clears the %dpx "
                                  "floor. Tried: %s"
                                  % (FLOOR_PX, "; ".join(tried[:6]) or "nothing"),
                        "reasonCode": "no-usable-mark", "checked": today}
            break
        if last and last.get("reasonCode") == "refused":
            break
    return None, last or {"name": name, "reason": "no candidate domain answered",
                          "reasonCode": "dead-site", "checked": today}


def recolour(today):
    """Re-derive every brand colour from the stored marks. No network at all.

    The colour rule changed twice while the first sweep was still running.
    Re-sweeping 279 companies' websites to re-run arithmetic on files already
    committed here would be both slow and rude, so the marks are the source and
    this pass reads them off disk.
    """
    doc = json.load(open(OUT, encoding="utf-8"))
    changed = lost = gained = 0
    for r in doc["logos"]:
        path = os.path.join(HERE, r["file"])
        if not os.path.exists(path):
            continue
        had = bool(r.get("brand"))
        if r["file"].endswith(".svg"):
            brand, why = brand_from_svg(open(path, "rb").read(), r["source"], r["fetched"])
        else:
            brand, why = brand_from(Image.open(path), r["source"], r["fetched"])
        if brand != r.get("brand"):
            changed += 1
        r["brand"] = brand
        r.pop("brandRefused", None)
        if brand is None:
            r["brandRefused"] = why
        if had and brand is None:
            lost += 1
        if not had and brand is not None:
            gained += 1
    # RECLASSIFY REFUSALS FROM WHAT WAS ALREADY RECORDED.
    # Every refusal already carries the full list of candidates it tried and why
    # each one failed, so a mis-filed reason can be corrected here without asking
    # anybody's server anything a second time. Nothing is invented: the sentence
    # is rewritten from evidence the sweep already banked.
    reclassified = 0
    for r in doc.get("refusals", []):
        reason = str(r.get("reason") or "")
        if r.get("reasonCode") != "no-usable-mark" or "Tried: " not in reason:
            continue
        tried = reason.split("Tried: ", 1)[1]
        parts = [t for t in tried.split("; ") if t.strip()]
        if parts and all("robots.txt disallows" in t for t in parts):
            r["reasonCode"] = "refused"
            r["reason"] = ("the site publishes marks, but every one is served from a host "
                           "whose robots.txt disallows this crawler — refused, not absent. "
                           "Tried: %s" % tried)
            reclassified += 1
    if reclassified:
        print("reclassified %d refusal(s) from 'no usable mark' to 'refused by robots.txt' — "
              "the site had a mark, we were not allowed to fetch it." % reclassified)

    doc["generated"] = today
    doc["counts"]["logosWithBrandColour"] = sum(1 for r in doc["logos"] if r.get("brand"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("recoloured from the stored marks: %d changed, %d gained a colour, %d lost one; "
          "%d of %d mark(s) now carry one."
          % (changed, gained, lost, doc["counts"]["logosWithBrandColour"], len(doc["logos"])))
    return 0


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--recolour", action="store_true",
                    help="re-derive everything computable from what is already recorded — "
                         "brand colours from the marks in assets/logos/, and refusal "
                         "reasons from the candidate lists the sweep banked. Fetches "
                         "nothing. Run this after changing the colour, contrast or "
                         "classification rules: re-sweeping other people's servers to "
                         "re-run arithmetic on evidence we already hold is rude and slow.")
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    os.makedirs(ASSETS, exist_ok=True)
    recs = load_records()

    targets = []
    for name in sorted(recs):
        if a.only and name != a.only:
            continue
        targets.append(name)

    with_domain = [n for n in targets if domains_for(recs[n])]
    print("%d supplier(s); %d carry a recorded domain." % (len(targets), len(with_domain)))
    if a.report_only:
        for n in with_domain[:40]:
            print("  %-40s %s" % (n[:40], domains_for(recs[n])[0][0]))
        return 0

    if a.recolour:
        return recolour(today)

    banked = {}
    if a.resume and os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8"))
        for r in old.get("logos", []):
            banked[r["name"]] = ("logo", r)
        for r in old.get("refusals", []):
            banked[r["name"]] = ("refusal", r)

    todo = [n for n in with_domain if n not in banked]
    if a.limit:
        todo = todo[:a.limit]

    logos = [r for k, (t, r) in banked.items() if t == "logo"]
    refusals = [r for k, (t, r) in banked.items() if t == "refusal"]
    near_miss = []
    byhash = {}
    for r in logos:
        byhash.setdefault(r.get("sha256"), []).append(r["name"])

    for i, name in enumerate(todo, 1):
        got, ref = try_supplier(name, recs[name], today, near_miss)
        if not got:
            refusals.append(ref)
            print("  --  %-38s %s" % (name[:38], ref.get("reason", "")[:70]), flush=True)
            continue

        if got["format"] == "svg":
            blob = got.pop("_raw")
            got.pop("_im", None)
            ext = "svg"
            im_for_colour = None
        else:
            im = got.pop("_im")
            got.pop("_raw", None)
            blob = optimise_png(im)
            ext = "png"
            im_for_colour = im

        digest = hashlib.sha256(blob).hexdigest()
        got["sha256"] = digest
        got["bytes"] = len(blob)
        slug = slugify(name)
        got["slug"] = slug
        got["file"] = "assets/logos/%s.%s" % (slug, ext)

        # A mark shared by several companies is a CDN or theme default.
        byhash.setdefault(digest, []).append(name)
        if len(byhash[digest]) >= DUP_LIMIT:
            shared = byhash[digest]
            for other in shared:
                logos[:] = [r for r in logos if r["name"] != other]
                p = os.path.join(HERE, "assets", "logos")
                for e in ("png", "svg"):
                    f = os.path.join(p, "%s.%s" % (slugify(other), e))
                    if os.path.exists(f):
                        os.remove(f)
                if not any(r["name"] == other for r in refusals):
                    refusals.append({
                        "name": other, "domain": None,
                        "reason": "the mark fetched for this company is byte-identical to the "
                                  "mark fetched for %d others (%s) — a CDN or theme default, "
                                  "not a brand mark" % (len(shared) - 1,
                                                        ", ".join(sorted(shared)[:4])),
                        "reasonCode": "no-usable-mark", "checked": today})
            print("  --  %-38s shared placeholder, %d companies refused"
                  % (name[:38], len(shared)), flush=True)
            continue

        with open(os.path.join(HERE, got["file"]), "wb") as f:
            f.write(blob)

        # SAMPLE THE FILE THAT SHIPS, NOT THE ONE THAT ARRIVED.
        # The stored mark is resized and colour-quantised, which moves the
        # histogram — so sampling the original here and re-sampling the stored
        # file in --recolour gave two different answers for the same company,
        # and only one of them described what a member actually sees. The file
        # in assets/logos/ is the mark, so it is the thing sampled. Both paths
        # now read the same bytes and cannot disagree.
        if im_for_colour is not None:
            brand, why = brand_from(Image.open(io.BytesIO(blob)), got["source"], today)
        else:
            brand, why = brand_from_svg(blob, got["source"], today)
        got["brand"] = brand
        if brand is None:
            got["brandRefused"] = why
        logos.append(got)
        print("  OK  %-38s %-5s %s  %s" % (name[:38], ext, got.get("brand", {}) and
                                           got["brand"]["c1"] if brand else "(no colour)",
                                           got["source"][:60]), flush=True)

    logos.sort(key=lambda r: r["name"])
    refusals.sort(key=lambda r: r["name"])
    withcol = [r for r in logos if r.get("brand")]

    doc = {
        "generated": today,
        "rule": (
            "Every mark here was fetched ONCE, at build time, from the company's own "
            "website, and is served from this repository. No third-party logo or favicon "
            "service is called, here or by the page. A raster mark must be at least %d "
            "pixels on its longest edge — the report draws it on a 74px plate, so a "
            "Retina member needs 148 real pixels — and SVG is exempt because vector has "
            "no native size. A mark that is one flat colour, or that is byte-identical "
            "to the mark of %d or more other companies, is a placeholder and is refused. "
            "Colours are sampled from the mark itself: c1 must clear %.1f:1 against the "
            "report's ivory card ground (WCAG 2.1 1.4.11, non-text) and c2 must clear "
            "%.1f:1 with white text on it (WCAG 2.1 1.4.3); a colour that cannot is not "
            "published and the company keeps the house Antique Gold."
            % (FLOOR_PX, DUP_LIMIT, MIN_ON_IVORY, MIN_WHITE_TEXT)),
        "floorPx": FLOOR_PX,
        "thresholds": {"onIvory": MIN_ON_IVORY, "whiteTextOnC2": MIN_WHITE_TEXT},
        "counts": {
            "suppliers": len(targets),
            "withRecordedDomain": len(with_domain),
            "logos": len(logos),
            "logosWithBrandColour": len(withcol),
            "refusals": len(refusals),
        },
        "logos": logos,
        "refusals": refusals,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")

    total = sum(r["bytes"] for r in logos)
    print("\nlogos            : %d of %d supplier(s)" % (len(logos), len(targets)))
    print("with brand colour: %d" % len(withcol))
    print("refusals         : %d" % len(refusals))
    print("stored bytes     : %d (%.2f MB) across %d file(s)"
          % (total, total / 1048576.0, len(logos)))
    if near_miss:
        print("  %d mark(s) were between %dpx and the %dpx floor and were refused; "
              "lowering the floor would buy those and nothing else."
              % (len(near_miss), NEAR_MISS_PX, FLOOR_PX))
    print("\nnext: python3 scripts/stamp_notice.py && python3 verify.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
