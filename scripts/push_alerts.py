#!/usr/bin/env python3
"""
push_alerts.py — phone alerts (web push) for members, on new speciality news.

WHAT THIS IS
------------
A member opens alerts/index.html (served from this repo by GitHub Pages), picks
the specialities they sell into and taps "Turn on alerts". Their browser hands
back a push subscription (an endpoint URL plus two keys) which the page stores
in a Supabase table. This script runs after every "Speciality news refresh"
(.github/workflows/push-alerts.yml), works out which items in
data/speciality-news/<slug>.json are new since the last run, and sends each
subscriber ONE notification covering the specialities they chose. Tapping it
opens the speciality page on the Hub.

Four subcommands:

  keys           mint a VAPID key pair (once; the private half is a secret)
  build-config   write alerts/config.json from the news slugs + the secrets
  send           send the digest; --dry-run prints instead of sending
  test           send a fixed test alert to every subscriber now (state untouched)

WHY THE SHAPE IS WHAT IT IS
---------------------------
* ONE push per member per run, never one per item. The news build can add
  thirty items across ten specialities in a morning; thirty buzzes is how a
  member turns alerts off for good.
* "New" means "not seen by THIS script before", tracked in
  state/push-alerts.json, not "published in the last 24 hours". Feeds
  back-date items and the build re-fetches up to 60 days of them, so a
  date window would either miss items or repeat them.
* The FIRST run seeds the seen-set and sends nothing. Otherwise the first
  subscriber ever would be greeted with 60 days of backlog.
* Subscriptions are stored in Supabase, not in this repo. Endpoints are
  per-device secrets — anyone holding one can push to that phone — and this
  repo is public. The browser inserts with the anon key under a row-level
  policy that allows INSERT only; this script reads and prunes with the
  service-role key, which lives in a GitHub secret.
* A push service answering 404 or 410 means the member unsubscribed or the
  browser dropped the subscription: the row is deleted, not retried.
* Runtime dependency on pywebpush (RFC 8291 encryption + RFC 8292 VAPID) is
  imported lazily inside send(), so `build-config`, `--dry-run` and the unit
  tests need nothing beyond the standard library.

Secrets (GitHub Actions):
  VAPID_PRIVATE_KEY     base64url raw P-256 private key from `keys`
  SUPABASE_URL          https://<project>.supabase.co
  SUPABASE_ANON_KEY     public anon key (goes into alerts/config.json)
  SUPABASE_SERVICE_KEY  service-role key (never leaves the runner)

Set-up, table SQL and the runbook: docs/PUSH-ALERTS.md.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_DIR = os.path.join(ROOT, "data", "speciality-news")
PANELS_DIR = os.path.join(ROOT, "data", "speciality-panels")
STATE_PATH = os.path.join(ROOT, "state", "push-alerts.json")
CONFIG_PATH = os.path.join(ROOT, "alerts", "config.json")

HUB_ORIGIN = "https://medsalesintelligencehub.co.uk"
HUB_HOME = HUB_ORIGIN + "/medical-sales-hub/"
VAPID_SUBJECT = "mailto:contact@elevateandthrive.uk"
TABLE = "push_subscriptions"

TTL_SECONDS = 24 * 3600     # a phone off overnight still gets the morning digest
BODY_MAX = 160              # Android truncates around here; iOS a little earlier
MAX_PER_RUN = 5000          # sanity cap on rows pulled per run


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def label_for(slug: str, panels_dir: str = PANELS_DIR) -> str:
    """The speciality's display label: the panels file's own, else the slug
    tidied up (title case, "and" kept lower)."""
    p = os.path.join(panels_dir, slug + ".json")
    try:
        with open(p, encoding="utf-8") as fh:
            lbl = json.load(fh).get("label")
        if isinstance(lbl, str) and lbl.strip():
            return lbl.strip()
    except (OSError, ValueError):
        pass
    words = slug.split("-")
    return " ".join(w if w in ("and", "the", "of") else w.capitalize() for w in words)


def hub_page(slug: str) -> str:
    return "%s/medical-sales-hub/%s/" % (HUB_ORIGIN, slug)


# --------------------------------------------------------------------------
# news + state
# --------------------------------------------------------------------------
def load_news(news_dir: str = NEWS_DIR) -> dict[str, list[dict]]:
    """{slug: [item, ...]} for every readable speciality-news file."""
    out: dict[str, list[dict]] = {}
    if not os.path.isdir(news_dir):
        return out
    for fn in sorted(os.listdir(news_dir)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(news_dir, fn), encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        slug = doc.get("speciality") or fn[:-5]
        items = [i for i in (doc.get("items") or []) if isinstance(i, dict) and i.get("link")]
        out[slug] = items
    return out


def load_state(path: str = STATE_PATH) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        if isinstance(st, dict) and isinstance(st.get("seen"), dict):
            return st
    except (OSError, ValueError):
        pass
    return None


def diff_news(news: dict[str, list[dict]], state: dict | None):
    """Returns (new_by_slug, next_state).

    new_by_slug: {slug: [item, ...]} — items whose link is not in the seen-set.
    next_state:  the seen-set to persist, pruned to links still in the feed
                 (the build only keeps 60 days, so this can't grow unbounded).
    First run (state is None): nothing is new, everything is seeded.
    """
    seen = (state or {}).get("seen", {})
    first_run = state is None
    new_by_slug: dict[str, list[dict]] = {}
    next_seen: dict[str, list[str]] = {}
    for slug, items in news.items():
        prev = set(seen.get(slug, []))
        links = []
        fresh = []
        for it in items:
            link = it["link"]
            if link in links:
                continue
            links.append(link)
            if not first_run and link not in prev:
                fresh.append(it)
        next_seen[slug] = links
        if fresh:
            new_by_slug[slug] = fresh
    next_state = {
        "_about": "Seen-set for scripts/push_alerts.py. Links here have already been "
                  "pushed (or were present when alerts first ran). Delete this file to "
                  "re-seed without sending.",
        "lastRun": now_iso(),
        "seen": next_seen,
    }
    return new_by_slug, next_state


def save_state(state: dict, path: str = STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------
# the message
# --------------------------------------------------------------------------
def _clip(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def build_message(new_by_slug: dict[str, list[dict]], wanted: list[str] | None,
                  labels=label_for) -> dict | None:
    """One notification for one subscriber, or None if nothing new for them.

    wanted: the subscriber's speciality slugs; empty/None means every speciality.
    """
    slugs = [s for s in sorted(new_by_slug) if not wanted or s in wanted]
    if not slugs:
        return None
    total = sum(len(new_by_slug[s]) for s in slugs)
    if len(slugs) == 1:
        slug = slugs[0]
        items = new_by_slug[slug]
        lbl = labels(slug)
        title = "%s: %d new item%s" % (lbl, len(items), "" if len(items) == 1 else "s")
        lead = items[0].get("title") or ""
        src = items[0].get("source") or ""
        body = _clip(lead + (" — " + src if src else ""), BODY_MAX)
        url = hub_page(slug)
    else:
        title = "Hub news: %d new items across %d specialities" % (total, len(slugs))
        parts = ["%s (%d)" % (labels(s), len(new_by_slug[s])) for s in slugs]
        body = _clip(" · ".join(parts), BODY_MAX)
        url = HUB_HOME
    return {
        "title": title,
        "body": body,
        "url": url,
        "tag": "msh-news-" + _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d"),
    }


# --------------------------------------------------------------------------
# Supabase (plain REST, service-role key)
# --------------------------------------------------------------------------
class SupabaseError(RuntimeError):
    pass


_HINTS = {
    404: ("\nHint: the push_subscriptions table is not in the project SUPABASE_URL points at. "
          "Run the SQL in docs/PUSH-ALERTS.md in THAT project, and check SUPABASE_URL is just "
          "https://<project-ref>.supabase.co with nothing after it."),
    401: "\nHint: SUPABASE_SERVICE_KEY is not a valid key for this project.",
    403: "\nHint: the key has no access to push_subscriptions; SUPABASE_SERVICE_KEY must be the service_role/secret key.",
}


class Store:
    def __init__(self, url: str, service_key: str, opener=None):
        self.base = url.rstrip("/") + "/rest/v1/" + TABLE
        self.key = service_key
        self._open = opener or urllib.request.urlopen

    def _req(self, method: str, query: str = "", body=None, prefer: str | None = None):
        req = urllib.request.Request(self.base + query, method=method)
        req.add_header("apikey", self.key)
        req.add_header("Authorization", "Bearer " + self.key)
        req.add_header("Accept", "application/json")
        if prefer:
            req.add_header("Prefer", prefer)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        try:
            with self._open(req, data, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            # Say what Supabase said. A bare "HTTP Error 404" (23/09/2026) could
            # mean a missing table, a wrong project or a wrong URL; the body
            # (e.g. PGRST205 "Could not find the table") tells them apart.
            # The body never contains the key; the URL is the table's path.
            try:
                body = exc.read().decode("utf-8", "replace")[:400]
            except Exception:
                body = ""
            raise SupabaseError("Supabase %s %s returned HTTP %s: %s%s" % (
                method, self.base.split("/rest/v1/")[-1] + query.split("&")[0], exc.code, body,
                _HINTS.get(exc.code, ""))) from None
        return json.loads(raw) if raw else None

    def subscriptions(self) -> list[dict]:
        rows = self._req("GET", "?select=id,endpoint,p256dh,auth,specialities&limit=%d" % MAX_PER_RUN)
        return [r for r in (rows or []) if r.get("endpoint") and r.get("p256dh") and r.get("auth")]

    def delete(self, row_id) -> None:
        self._req("DELETE", "?id=eq.%s" % row_id, prefer="return=minimal")

    def events(self, limit: int = 60) -> list[dict]:
        """Newest rows of push_events: where a phone got stuck on the page."""
        base = self.base
        self.base = base[: -len(TABLE)] + "push_events"
        try:
            return self._req("GET", "?select=created_at,stage,detail,standalone,permission,user_agent"
                                    "&order=created_at.desc&limit=%d" % limit) or []
        finally:
            self.base = base


# --------------------------------------------------------------------------
# sending
# --------------------------------------------------------------------------
def pywebpush_sender(private_key: str):
    """Returns send(row, message) -> (ok: bool, gone: bool, detail: str)."""
    from pywebpush import WebPushException, webpush   # lazy: only `send` needs it

    def send(row: dict, message: dict):
        info = {"endpoint": row["endpoint"], "keys": {"p256dh": row["p256dh"], "auth": row["auth"]}}
        try:
            webpush(subscription_info=info, data=json.dumps(message),
                    vapid_private_key=private_key,
                    vapid_claims={"sub": VAPID_SUBJECT},
                    ttl=TTL_SECONDS, headers={"Urgency": "high"})
            return True, False, "sent"
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            gone = status in (404, 410)
            return False, gone, "HTTP %s: %s" % (status, str(exc)[:200])
        except Exception as exc:   # network etc. — report, do not prune
            return False, False, "error: %s" % str(exc)[:200]
    return send


def deliver(rows: list[dict], new_by_slug: dict[str, list[dict]], send, on_gone=None,
            log=print) -> dict:
    """Send one message per row. Returns counts."""
    counts = {"subscribers": len(rows), "sent": 0, "skipped": 0, "failed": 0, "pruned": 0}
    for row in rows:
        wanted = row.get("specialities") or []
        if isinstance(wanted, str):
            wanted = [w for w in re.split(r"[,\s]+", wanted) if w]
        msg = build_message(new_by_slug, wanted)
        if msg is None:
            counts["skipped"] += 1
            continue
        ok, gone, detail = send(row, msg)
        if ok:
            counts["sent"] += 1
        elif gone:
            counts["pruned"] += 1
            if on_gone:
                on_gone(row)
            log("  pruned %s (%s)" % (_host(row["endpoint"]), detail))
        else:
            counts["failed"] += 1
            log("  FAILED %s (%s)" % (_host(row["endpoint"]), detail))
    return counts


def _host(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1) if m else "?"


# --------------------------------------------------------------------------
# config for the page
# --------------------------------------------------------------------------
def public_key_from_private(private_b64url: str) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    raw = b64url_decode(private_b64url)
    if len(raw) != 32:
        raise ValueError("VAPID private key must be 32 raw bytes, base64url (got %d)" % len(raw))
    key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
    return b64url(pub)


def build_config(existing: dict | None, news: dict[str, list[dict]], env: dict,
                 labels=label_for) -> dict:
    """alerts/config.json: what the member page needs and nothing else.

    Public by design: the VAPID PUBLIC key, the Supabase URL and its ANON key
    are meant to sit in a web page. Secrets never come through here.
    """
    cfg = dict(existing or {})
    cfg["_about"] = ("Read by alerts/index.html. Generated by scripts/push_alerts.py "
                     "build-config — edit the script or the GitHub secrets, not this file.")
    cfg["hubOrigin"] = HUB_ORIGIN
    cfg["specialities"] = [{"slug": s, "label": labels(s)} for s in sorted(news)]
    priv = env.get("VAPID_PRIVATE_KEY", "").strip()
    if priv:
        cfg["vapidPublicKey"] = public_key_from_private(priv)
    else:
        cfg.setdefault("vapidPublicKey", "")
    if env.get("SUPABASE_URL", "").strip():
        cfg["supabaseUrl"] = env["SUPABASE_URL"].strip().rstrip("/")
    else:
        cfg.setdefault("supabaseUrl", "")
    if env.get("SUPABASE_ANON_KEY", "").strip():
        cfg["supabaseAnonKey"] = env["SUPABASE_ANON_KEY"].strip()
    else:
        cfg.setdefault("supabaseAnonKey", "")
    cfg["table"] = TABLE
    cfg["generatedAt"] = now_iso()
    return cfg


def write_json(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_keys(_args) -> int:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    pub = key.public_key().public_bytes(serialization.Encoding.X962,
                                        serialization.PublicFormat.UncompressedPoint)
    print("VAPID_PRIVATE_KEY (GitHub secret, never commit):")
    print("  " + b64url(priv))
    print("VAPID public key (derived by build-config, safe to publish):")
    print("  " + b64url(pub))
    return 0


def cmd_build_config(args) -> int:
    news = load_news(args.news_dir)
    existing = None
    try:
        with open(args.config, encoding="utf-8") as fh:
            existing = json.load(fh)
    except (OSError, ValueError):
        pass
    cfg = build_config(existing, news, os.environ)
    if existing:
        same = {k: v for k, v in existing.items() if k != "generatedAt"} == \
               {k: v for k, v in cfg.items() if k != "generatedAt"}
        if same:
            print("build-config: unchanged (%d specialities)" % len(cfg["specialities"]))
            return 0
    write_json(args.config, cfg)
    print("build-config: wrote %s (%d specialities, vapid %s, supabase %s)" % (
        os.path.relpath(args.config, ROOT), len(cfg["specialities"]),
        "set" if cfg["vapidPublicKey"] else "MISSING",
        "set" if cfg["supabaseUrl"] and cfg["supabaseAnonKey"] else "MISSING"))
    return 0


def cmd_send(args) -> int:
    news = load_news(args.news_dir)
    if not news:
        print("send: no speciality-news files found — nothing to do")
        return 0
    state = load_state(args.state)
    new_by_slug, next_state = diff_news(news, state)
    total_new = sum(len(v) for v in new_by_slug.values())

    if state is None:
        save_state(next_state, args.state)
        print("send: FIRST RUN — seeded %d specialities / %d items, sent nothing"
              % (len(next_state["seen"]), sum(len(v) for v in next_state["seen"].values())))
        return 0

    print("send: %d new item(s) across %d specialit%s" % (
        total_new, len(new_by_slug), "y" if len(new_by_slug) == 1 else "ies"))
    for slug in sorted(new_by_slug):
        print("  %-45s %d" % (slug, len(new_by_slug[slug])))

    if total_new == 0:
        save_state(next_state, args.state)
        print("send: nothing new — state refreshed, no pushes")
        return 0

    url = os.environ.get("SUPABASE_URL", "").strip()
    svc = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()

    if args.dry_run:
        sample = build_message(new_by_slug, None)
        print("send: DRY RUN — message for an all-specialities subscriber would be:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))
        for slug in sorted(new_by_slug):
            print(json.dumps(build_message(new_by_slug, [slug]), ensure_ascii=False))
        print("send: DRY RUN — state NOT updated, nothing sent")
        return 0

    missing = [n for n, v in (("SUPABASE_URL", url), ("SUPABASE_SERVICE_KEY", svc),
                              ("VAPID_PRIVATE_KEY", priv)) if not v]
    if missing:
        # No secrets means no subscriber table to read, so nobody could have
        # subscribed yet and nobody misses these items. Mark them seen so the
        # first CONFIGURED run starts from that morning, not from a backlog.
        next_state["lastSent"] = {"at": now_iso(), "items": total_new, "sent": 0,
                                  "reason": "not configured", "missing": missing}
        save_state(next_state, args.state)
        print("send: NOT CONFIGURED — missing %s. Nothing sent; %d item(s) marked seen. "
              "See docs/PUSH-ALERTS.md." % (", ".join(missing), total_new))
        return 0

    store = Store(url, svc)
    rows = store.subscriptions()
    print("send: %d subscription(s) on file" % len(rows))
    counts = deliver(rows, new_by_slug, pywebpush_sender(priv),
                     on_gone=lambda r: store.delete(r["id"]))
    print("send: %s" % json.dumps(counts))

    # State moves forward even if some sends failed: a failed push is a lost
    # buzz, a re-sent one is spam. The failure is in the log and the counts.
    next_state["lastSent"] = {"at": now_iso(), "items": total_new, **counts}
    save_state(next_state, args.state)
    return 0


TEST_MESSAGE = {
    "title": "Medical Sales Intelligence Hub",
    "body": "Test alert: phone alerts are working. Your first real one arrives the next morning there is news.",
    "url": HUB_HOME,
    "tag": "msh-test",
}


def cmd_test(_args) -> int:
    """Send TEST_MESSAGE to every subscriber now. Never touches the seen-set."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    svc = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    missing = [n for n, v in (("SUPABASE_URL", url), ("SUPABASE_SERVICE_KEY", svc),
                              ("VAPID_PRIVATE_KEY", priv)) if not v]
    if missing:
        print("test: NOT CONFIGURED — missing %s" % ", ".join(missing))
        return 1
    store = Store(url, svc)
    rows = store.subscriptions()
    print("test: %d subscription(s) on file" % len(rows))
    send = pywebpush_sender(priv)
    counts = {"subscribers": len(rows), "sent": 0, "failed": 0, "pruned": 0}
    for row in rows:
        ok, gone, detail = send(row, TEST_MESSAGE)
        if ok:
            counts["sent"] += 1
            print("  sent   %s" % _host(row["endpoint"]))
        elif gone:
            counts["pruned"] += 1
            store.delete(row["id"])
            print("  pruned %s (%s)" % (_host(row["endpoint"]), detail))
        else:
            counts["failed"] += 1
            print("  FAILED %s (%s)" % (_host(row["endpoint"]), detail))
    print("test: %s" % json.dumps(counts))
    return 1 if counts["failed"] else 0


def _device(ua: str) -> str:
    """A short, human label for a user-agent string (no personal data)."""
    ua = ua or ""
    os_ = ("iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else
           "Android" if "Android" in ua else "Mac" if "Macintosh" in ua else
           "Windows" if "Windows" in ua else "other")
    br = ("Chrome" if ("CriOS" in ua or ("Chrome" in ua and "Edg" not in ua)) else
          "Edge" if ("EdgiOS" in ua or "Edg/" in ua) else
          "Firefox" if ("FxiOS" in ua or "Firefox" in ua) else
          "Safari" if "Safari" in ua else "?")
    m = re.search(r"OS (\d+)[_.](\d+)", ua)
    ver = " iOS %s.%s" % m.groups() if m and os_ in ("iPhone", "iPad") else ""
    return "%s%s %s" % (os_, ver, br)


def cmd_diagnose(_args) -> int:
    """Read-only: who is subscribed (by push service) and where phones got stuck."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    svc = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not (url and svc):
        print("diagnose: NOT CONFIGURED — SUPABASE_URL and SUPABASE_SERVICE_KEY are needed")
        return 1
    store = Store(url, svc)
    rows = store.subscriptions()
    hosts: dict[str, int] = {}
    for r in rows:
        hosts[_host(r["endpoint"])] = hosts.get(_host(r["endpoint"]), 0) + 1
    print("diagnose: %d subscription(s): %s" % (len(rows), json.dumps(hosts)))
    print("  (web.push.apple.com = iPhone/iPad/Safari; fcm.googleapis.com = Chrome/Android; "
          "updates.push.services.mozilla.com = Firefox)")
    try:
        ev = store.events()
    except SupabaseError as exc:
        print("diagnose: could not read push_events: %s" % exc)
        return 1
    print("diagnose: last %d page event(s), newest first:" % len(ev))
    for e in ev:
        print("  %s  %-20s standalone=%-5s permission=%-8s %-24s %s" % (
            (e.get("created_at") or "")[:19], e.get("stage"), e.get("standalone"),
            e.get("permission"), _device(e.get("user_agent")), _clip(e.get("detail") or "", 90)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keys", help="mint a VAPID key pair").set_defaults(fn=cmd_keys)
    b = sub.add_parser("build-config", help="write alerts/config.json")
    b.add_argument("--news-dir", default=NEWS_DIR)
    b.add_argument("--config", default=CONFIG_PATH)
    b.set_defaults(fn=cmd_build_config)
    s = sub.add_parser("send", help="send the digest to every subscriber")
    s.add_argument("--news-dir", default=NEWS_DIR)
    s.add_argument("--state", default=STATE_PATH)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_send)
    sub.add_parser("test", help="send a test alert to every subscriber now").set_defaults(fn=cmd_test)
    sub.add_parser("diagnose", help="read-only: subscribers by push service, and recent page events"
                   ).set_defaults(fn=cmd_diagnose)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
