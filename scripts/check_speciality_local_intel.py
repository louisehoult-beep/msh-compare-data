#!/usr/bin/env python3
"""check_speciality_local_intel.py — re-check every source in
data/speciality-local-intel.json and record the result in each item's `lastCheck`.

WHY (28/09/2026). The file is hand-curated from primary sources (formularies,
contract awards, board papers). A formulary PDF is replaced, a board paper moves,
a notice is withdrawn. A dead link on a paid page is member-facing damage (README,
"Dead source links"), so every item is re-fetched on each panel build and the
renderer hides an item whose source is gone.

WHAT IT WRITES: only `lastCheck` = {"date", "status", "http"}. It never edits a
fact, a quote or a date, which are human-curated (see the file's own note).

status:
  ok           2xx from the item's checkUrl (or url)
  gone         404 or 410 on two attempts: hidden by the renderer
  unreachable  anything else (403, 429, 5xx, timeout, TLS). NOT treated as gone:
               Find a Tender rate-limits and several NHS sites refuse scripted
               fetches. The item stays visible and the status is reported.

Find a Tender HTML refuses scripted fetches, so FTS items carry a `checkUrl` on
the OCDS API, which serves the same notice.

Usage: python3 scripts/check_speciality_local_intel.py [--dry-run]
Stdlib only. Exit 0 always (a check failure must not block the panel build);
prints a summary so the workflow log shows what changed.
"""
import json, os, re, sys, time, datetime, html, urllib.request, urllib.error, ssl

PATH = os.path.join("data", "speciality-local-intel.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40, context=ssl.create_default_context()) as r:
            r.read(2048)
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def _norm(t):
    t = re.sub(r"(?s)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", t).strip().lower()


def quote_state(item):
    """found | missing | unchecked. A quote that has vanished from its page means the
    source text changed since a human last read it: the item needs re-reading, not hiding.
    Pages that refuse scripted fetches, or are not text (PDF, xlsx), are 'unchecked'."""
    q = item.get("quote")
    if not q:
        return "n/a"
    req = urllib.request.Request(item["url"], headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40, context=ssl.create_default_context()) as r:
            if r.status != 200:  # 202 is a bot-challenge page, not the source
                return "unchecked"
            if "html" not in (r.headers.get("Content-Type") or "") and "json" not in (r.headers.get("Content-Type") or ""):
                return "unchecked"
            body = r.read(6_000_000).decode("utf-8", "replace")
    except Exception:
        return "unchecked"
    return "found" if _norm(q) in _norm(body) else "missing"


def check(item):
    url = item.get("checkUrl") or item.get("url")
    code = probe(url)
    if code in (404, 410):
        time.sleep(3)
        code = probe(url)  # a single 404 is retried before an item is hidden
    if code is not None and 200 <= code < 300:
        status = "ok"
    elif code in (404, 410):
        status = "gone"
    else:
        status = "unreachable"
    res = {"date": datetime.date.today().isoformat(), "status": status, "http": code}
    if status == "ok":
        res["quote"] = quote_state(item)
    return res


def main():
    dry = "--dry-run" in sys.argv
    with open(PATH, encoding="utf-8") as fh:
        doc = json.load(fh)
    tally = {"ok": 0, "gone": 0, "unreachable": 0}
    missing = []
    for slug, items in doc["specialities"].items():
        for it in items:
            res = check(it)
            tally[res["status"]] += 1
            if res["status"] != "ok":
                print("  %-12s %-38s %s (%s)" % (res["status"], slug, it["id"], res["http"]))
            elif res.get("quote") == "missing":
                missing.append("%s/%s" % (slug, it["id"]))
                print("  QUOTE MISSING %-38s %s  <- source text changed; re-read it" % (slug, it["id"]))
            if not dry:
                it["lastCheck"] = res
            time.sleep(1.5)  # Find a Tender allows about 12 quick requests
    print("speciality-local-intel: %d ok, %d gone (hidden), %d unreachable (kept)"
          % (tally["ok"], tally["gone"], tally["unreachable"]))
    if missing:
        print("speciality-local-intel: %d item(s) whose quoted source text has changed: %s"
              % (len(missing), ", ".join(missing)))
    if not dry:
        with open(PATH, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")


if __name__ == "__main__":
    main()
