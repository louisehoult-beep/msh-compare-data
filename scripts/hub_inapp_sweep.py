#!/usr/bin/env python3
"""Step B of the Hub-in-the-app plan (19/11/2026): load every Hub member page the
way the Live Desk app's Hub tab will (app user agent, logged-in member) and
flag what would break there. Run it before and after msh-compare-data goes
private: the raw-GitHub fallback dies with the flip, so every data read must
go through the gate (/wp-json/msh/v1/file, snippet 2874).

    python3 scripts/hub_inapp_sweep.py --login            # once: opens a window; the MEMBER logs in by hand
    python3 scripts/hub_inapp_sweep.py                    # sweep every page under 675
    python3 scripts/hub_inapp_sweep.py --pages 675 4404   # just these
    python3 scripts/hub_inapp_sweep.py --inject-inapp hub/wpcode/livedesk-in-app-mode.php   # preview step C on top

Claude never types a password: --login waits for a person to sign in, then
saves the browser session (cookies only) to ~/.claude/livedesk/hub-sweep-state.json
(mode 600, outside the repo). Use a member test account, not an admin:
an admin sees pages a member cannot.

Per page: final URL (sent to /login/ = gating problem), HTTP status, a bot
check page, console and page errors, MSH_GATE present, gate reads and their
status, raw-GitHub reads (GATE MISS: blank after the flip), and visible
Join / Register / pricing links (must be none once step C is live).
Writes sweep-<time>.json and sweep-<time>.md to --out.
"""
import argparse, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

SITE = "https://medsalesintelligencehub.co.uk"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Mobile/15E148 MSHLiveDeskApp/ios")
STATE = os.path.expanduser("~/.claude/livedesk/hub-sweep-state.json")
BUY = re.compile(r"/(register|join-the-hub|checkout|cart|account|my-account)/", re.I)
PROBE = """() => {
  const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const buy = [...document.querySelectorAll('a[href]')].filter(a => /\\/(register|join-the-hub|checkout|cart|account|my-account)\\//i.test(a.href)).filter(vis);
  const main = document.querySelector('main, .entry-content, .wp-site-blocks') || document.body;
  return {title: document.title, gate: !!(window.MSH_GATE && window.MSH_GATE.nonce),
          buyVisible: buy.map(a => (a.innerText || '').trim().slice(0, 40) + ' -> ' + new URL(a.href).pathname).slice(0, 10),
          textLen: (main.innerText || '').trim().length,
          emptyMounts: [...document.querySelectorAll('[id^="msh-"]:empty, [data-msh-app]:empty, [class*="mount"]:empty')].map(e => e.id || e.className).slice(0, 10)};
}"""


def rest(path):
    req = urllib.request.Request(SITE + path, headers={"User-Agent": "hub-inapp-sweep"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def descendants(root=675):
    out, todo = [root], [root]
    while todo:
        pid = todo.pop()
        page = 1
        while True:
            rows = rest(f"/wp-json/wp/v2/pages?parent={pid}&per_page=100&page={page}&_fields=id")
            ids = [r["id"] for r in rows]
            out += ids; todo += ids
            if len(rows) < 100: break
            page += 1
    return out


def link_of(pid):
    try:
        return rest(f"/wp-json/wp/v2/pages/{pid}?_fields=link")["link"]
    except Exception:
        return f"{SITE}/?page_id={pid}"


def login():
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context(user_agent=UA, viewport={"width": 390, "height": 844})
        pg = ctx.new_page(); pg.goto(SITE + "/login/")
        print("Log in to the Hub in the window that opened (a member test account). Waiting up to 10 minutes...")
        for _ in range(600):
            if any(c["name"].startswith("wordpress_logged_in") for c in ctx.cookies()):
                break
            time.sleep(1)
        else:
            sys.exit("No login seen; nothing saved.")
        ctx.storage_state(path=STATE); os.chmod(STATE, 0o600)
        print("Saved the session to", STATE); b.close()


def sweep(pages, inject, out):
    from playwright.sync_api import sync_playwright
    if not os.path.exists(STATE):
        print("No saved member session: running LOGGED OUT (expect /login/ redirects). Run --login first for a real sweep.")
    tag = ""
    if inject:
        snip = open(inject).read()
        js = re.search(r'<script id="msh-in-app-js">(.*?)</script>', snip, re.S).group(1)
        hidden = [re.sub(r"^https?://[^/]+", "", link_of(i)).lower() for i in (685, 1174, 687, 167, 166, 165, 4802, 4463, 4504)]
        js = re.sub(r"<\?php echo wp_json_encode\( array_values.*?\?>", json.dumps(hidden), js, flags=re.S)
        js = re.sub(r"<\?php echo wp_json_encode\( \$home.*?\?>", json.dumps("/medical-sales-hub/"), js, flags=re.S)
        tag = '<style>html.msh-in-app .msh-inapp-hide{display:none!important}</style><script>' + js + "</script>"
    urls = [(pid, link_of(pid)) for pid in pages]
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA, viewport={"width": 390, "height": 844},
                            storage_state=STATE if os.path.exists(STATE) else None)
        if tag:
            def inj(route):
                r = route.fetch(); t = r.text()
                route.fulfill(response=r, body=t.replace("<head>", "<head>" + tag, 1))
            ctx.route(re.compile(r"^https://medsalesintelligencehub\.co\.uk/.*"),
                      lambda route: inj(route) if route.request.resource_type == "document" else route.continue_())
        for pid, url in urls:
            pg = ctx.new_page(); errs, gate, raw = [], [], []
            pg.on("console", lambda m: m.type == "error" and errs.append(m.text[:160]))
            pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
            pg.on("response", lambda r: ("/wp-json/msh/v1/file" in r.url and gate.append(r.status)) or
                  (("raw.githubusercontent.com" in r.url or "github.io" in r.url) and raw.append(r.url[:120])))
            row = {"id": pid, "url": url}
            try:
                resp = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
                pg.wait_for_load_state("networkidle", timeout=20000)
            except Exception as e:
                row["load"] = str(e)[:120]
                resp = None
            try:
                row.update(pg.evaluate(PROBE))
            except Exception as e:
                row["probe"] = str(e)[:120]
            row.update({"status": resp.status if resp else None, "final": pg.url, "errors": errs[:8],
                        "gateReads": len(gate), "gateBad": [s for s in gate if s != 200], "rawReads": raw[:5]})
            flags = []
            if "/login" in pg.url and "/login" not in url: flags.append("SENT TO LOGIN")
            if "checking your browser" in (row.get("title") or "").lower(): flags.append("BOT CHECK")
            if row["status"] and row["status"] >= 400: flags.append(f"HTTP {row['status']}")
            if row["errors"]: flags.append("CONSOLE ERRORS")
            if row["rawReads"]: flags.append("GATE MISS (raw GitHub)")
            if row["gateBad"]: flags.append("GATE ERROR")
            if row.get("buyVisible"): flags.append("JOIN/PRICING VISIBLE")
            if row.get("emptyMounts"): flags.append("EMPTY MOUNT")
            if (row.get("textLen") or 0) < 200: flags.append("NEAR-BLANK")
            row["flags"] = flags
            results.append(row); pg.close()
            print(f"{pid:>5} {' | '.join(flags) or 'ok'}  {url}")
        b.close()
    os.makedirs(out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    jp = os.path.join(out, f"sweep-{stamp}.json"); json.dump(results, open(jp, "w"), indent=1)
    md = ["| Page | Flags | URL |", "|---|---|---|"] + [f"| {r['id']} | {', '.join(r['flags']) or 'ok'} | {r['url']} |" for r in results]
    open(os.path.join(out, f"sweep-{stamp}.md"), "w").write("\n".join(md) + "\n")
    bad = sum(1 for r in results if r["flags"])
    print(f"{len(results)} pages, {bad} flagged. {jp}")
    return 1 if bad else 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--login", action="store_true")
    a.add_argument("--pages", nargs="*", type=int)
    a.add_argument("--inject-inapp")
    a.add_argument("--out", default="hub-inapp-sweep")
    o = a.parse_args()
    if o.login: login(); sys.exit(0)
    sys.exit(sweep(o.pages or descendants(), o.inject_inapp, o.out))
