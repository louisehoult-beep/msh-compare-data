#!/usr/bin/env python3
"""Cluster watch: tell members when an ICB cluster publishes new medicines committee
minutes or when its formulary Skin chapter (BNF chapter 13) changes (16/10/2026).

WHY IT EXISTS. Birmingham and Solihull and Black Country share one leadership team and
a legal merger is anticipated; Coventry and Warwickshire and Herefordshire and
Worcestershire share a chair and chief executive (data/icb-watch.json, from NHS England).
A merged formulary chapter is where a brand's position in the new cluster is decided,
and the first sign is a new set of committee minutes or a changed chapter page. The
ICB watch already carries the structure; this carries what the clusters publish.

WHAT IS WATCHED is configured in config/cluster-watch-sources.json, each URL read on a
stated date. A source that could not be found is listed under notWatched with the
reason; it is never guessed.

FOUR KINDS OF SOURCE
  doclib    netFormulary document library: links to launcher.asp?docID=N. A new docID
            whose title matches itemPattern is a new document (minutes).
  dirlist   netFormulary file directory listing: a new file name is a new document.
  linklist  an ICB page of linked guidance documents: a new or retitled link.
  chapter   a formulary chapter page. Its visible text is fingerprinted, and the page
            is checked for the name of each partner ICB.

CHANGE DETECTION, FROM STORED STATE (same discipline as the ICB watch, born of the
24/07/2026 incident)
  * The first successful read of a source is a baseline and emits nothing.
  * A new item, a changed fingerprint or a newly named partner is held in `pending` and
    published only when read again on a DIFFERENT day.
  * A failed read, or a read that yields no items where items were stored, keeps the
    stored state and is logged under `errors`. An item that disappears is never reported.
  * Events say what was read and where. A changed chapter page is reported as
    "changed", never as "merged": only a page that now names the partner ICB is said to
    name it, and nobody is told what the change means.

USAGE
    python3 scripts/refresh_cluster_watch.py
Stdlib only. Writes data/cluster-watch.json; refresh_icb_watch.py then merges its
`events` into data/icb-watch.json (kind "cluster") so the structure page and the Live
Desk carry them.
"""
import datetime
import hashlib
import html
import json
import os
import re
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(REPO, "config", "cluster-watch-sources.json")
OUT = os.path.join(REPO, "data", "cluster-watch.json")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36", "Accept": "*/*"}


def today():
    return os.environ.get("CLUSTER_WATCH_TODAY") or datetime.date.today().isoformat()


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def anchors(raw):
    return [(m.group(1), clean(m.group(2))) for m in
            re.finditer(r'(?is)<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', raw)]


def parse_items(src, raw):
    """-> {item id: title}"""
    kind = src["kind"]
    out = {}
    if kind == "doclib":
        pat = re.compile(src.get("itemPattern") or ".")
        for href, title in anchors(raw):
            m = re.search(r"launcher\.asp\?docID=(\d+)", href)
            if m and title and pat.search(title):
                out[m.group(1)] = title
    elif kind == "dirlist":
        for href, title in anchors(raw):
            if re.search(r"\.(pdf|docx?|xlsx?)(\?|$)", href, re.I) and title:
                out[os.path.basename(href.split("?")[0])] = title
    elif kind == "linklist":
        for href, title in anchors(raw):
            if src.get("linkPattern", "") in href and title:
                out[hashlib.sha256((href + "|" + title).encode()).hexdigest()[:10]] = title
    return out


def chapter_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", raw)
    t = clean(raw)
    # Session tokens and cache-busters in links are not content.
    t = re.sub(r"UNLID=\w+|UID=\w+", "", t)
    return t


def read_source(src):
    raw = fetch(src["url"])
    if src["kind"] == "chapter":
        t = chapter_text(raw)
        if len(t) < 500:
            raise ValueError("chapter page returned only %d characters" % len(t))
        return {"hash": hashlib.sha256(t.encode()).hexdigest()[:16], "chars": len(t), "text": t}
    items = parse_items(src, raw)
    return {"items": items}


def mentions(text, names):
    return sorted(n for n in names if re.search(re.escape(n), text, re.I))


def event(date, cl, src, headline, detail, urls):
    codes = cl["icbs"]
    first = src.get("icb") or codes[0]
    ev = {"date": date, "icb": first, "kind": "cluster", "role": "medicines",
          "headline": headline, "detail": detail, "sources": urls}
    others = [c for c in codes if c != first]
    if others:
        ev["alsoIcbs"] = others
    ev["id"] = hashlib.sha256(("%s|cluster|%s" % (first, headline)).encode()).hexdigest()[:12]
    return ev


def step(prev_src, got, src, cl, t):
    """One source's new state and any events. Pure: no network, no clock."""
    st = dict(prev_src or {})
    pending = dict(st.get("pending") or {})
    events = []
    st.update({"id": src["id"], "label": src["label"], "kind": src["kind"], "url": src["url"],
               "checkedOn": t, "status": "ok"})
    baseline = "firstRead" not in st
    if src["kind"] == "chapter":
        names = list(src.get("partnerNames", []))
        seen_names = mentions(got["text"], names)
        if baseline:
            st.update({"firstRead": t, "hash": got["hash"], "chars": got["chars"], "named": seen_names})
            return st, events
        if got["hash"] != st["hash"]:
            first = pending.get("hash")
            if first and first["value"] == got["hash"] and first["on"] != t:
                events.append(event(t, cl, src,
                    "%s: page text changed" % src["label"],
                    "The text of this formulary page differs from the version stored on %s (first seen "
                    "changed on %s). The change has not been read by a person; open the page to see "
                    "what it says. This notice does not say the chapter has been merged or "
                    "rewritten." % (st.get("hashSince", st["firstRead"]), first["on"]),
                    [src["url"]]))
                st["hash"], st["chars"], st["hashSince"] = got["hash"], got["chars"], t
                pending.pop("hash", None)
            elif not first or first["value"] != got["hash"]:
                pending["hash"] = {"value": got["hash"], "on": t}
        else:
            pending.pop("hash", None)
        new_names = [n for n in seen_names if n not in st.get("named", [])]
        for n in new_names:
            key = "name:" + n
            first = pending.get(key)
            if first and first["on"] != t:
                events.append(event(t, cl, src,
                    "%s: page now names %s" % (src["label"], n),
                    "The page's text names \"%s\", which an earlier read did not. The page may be "
                    "describing a shared or merged chapter, or may only mention the partner; open "
                    "it to see which." % n, [src["url"]]))
                st["named"] = sorted(set(st.get("named", [])) | {n})
                pending.pop(key, None)
            elif not first:
                pending[key] = {"value": n, "on": t}
        for n in [k for k in list(pending) if k.startswith("name:") and k[5:] not in new_names]:
            pending.pop(n)
    else:
        items = got["items"]
        known = {i["id"]: i for i in st.get("items", [])}
        if baseline:
            st.update({"firstRead": t, "items": [{"id": k, "title": v} for k, v in sorted(items.items())]})
            return st, events
        for k, title in sorted(items.items()):
            if k in known:
                pending.pop("item:" + k, None)
                continue
            first = pending.get("item:" + k)
            if first and first["on"] != t:
                what = {"minutes": "new minutes", "revisions": "new revisions log",
                        "guidance": "new or retitled guidance document"}.get(src.get("what"), "new document")
                events.append(event(t, cl, src, "%s: %s listed: %s" % (src["label"], what, title),
                    "The list at this address now includes \"%s\", which was not in the list stored "
                    "on %s. It has not been read by a person; open it to see what it says." %
                    (title, st["firstRead"]), [src["url"]]))
                known[k] = {"id": k, "title": title}
                pending.pop("item:" + k, None)
            elif not first:
                pending["item:" + k] = {"value": title, "on": t}
        st["items"] = sorted(known.values(), key=lambda i: i["id"])
        for k in [k for k in pending if k.startswith("item:") and k[5:] not in items]:
            pending.pop(k)
    st["pending"] = pending
    return st, events


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def build(cfg, prev, reader, t):
    prev_cl = {c["id"]: c for c in prev.get("clusters", [])}
    out_cl, events, errors = [], [e for e in prev.get("events", [])], []
    by_id = {e["id"]: e for e in events}
    for cl in cfg["clusters"]:
        pc = prev_cl.get(cl["id"], {})
        prev_src = {s["id"]: s for s in pc.get("sources", [])}
        srcs = []
        for src in cl["sources"]:
            old = prev_src.get(src["id"])
            try:
                got = reader(src)
                if src["kind"] != "chapter" and not got["items"] and old and old.get("items"):
                    raise ValueError("read returned no items where %d were stored" % len(old["items"]))
                if src["kind"] != "chapter" and not got["items"]:
                    raise ValueError("read returned no items")
                st, evs = step(old, got, src, cl, t)
                for e in evs:
                    by_id.setdefault(e["id"], e)
            except Exception as e:  # noqa: BLE001 - a failed read must never read as a change
                msg = "%s: %s" % (src["id"], e)
                errors.append(msg)
                st = dict(old or {"id": src["id"], "label": src["label"], "kind": src["kind"], "url": src["url"]})
                st["status"] = "error"
                st["lastError"] = {"on": t, "message": str(e)[:200]}
            srcs.append(st)
        out_cl.append({"id": cl["id"], "name": cl["name"], "icbs": cl["icbs"], "sources": srcs,
                       "notWatched": cl.get("notWatched", [])})
    evs = sorted(by_id.values(), key=lambda e: (e["date"], e["id"]), reverse=True)
    doc = {"_notice": prev.get("_notice"), "generated": t, "configRead": cfg.get("readOn"),
           "note": ("What each ICB cluster has published, read from the sources in "
                    "config/cluster-watch-sources.json. A first read is a baseline; a change is "
                    "published only when seen on two different days. A failed read keeps the "
                    "stored state and is never reported as a removal."),
           "clusters": out_cl, "events": evs, "errorsToday": errors}
    if doc["_notice"] is None:
        del doc["_notice"]
    return doc


def main():
    cfg = load(CFG, None)
    if not cfg:
        sys.exit("config/cluster-watch-sources.json missing")
    prev = load(OUT, {})
    doc = build(cfg, prev, read_source, today())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    n = sum(len(c["sources"]) for c in doc["clusters"])
    print("cluster-watch: %d sources, %d events, %d read errors today" % (n, len(doc["events"]), len(doc["errorsToday"])))
    for e in doc["errorsToday"]:
        print("  error:", e)


if __name__ == "__main__":
    main()
