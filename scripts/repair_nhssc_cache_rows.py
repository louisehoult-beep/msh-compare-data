#!/usr/bin/env python3
"""Re-read every data/nhssc-cache.json row the old positional card parser
misread, straight from the NHS Supply Chain pilot catalogue by its NPC.

WHY (28/09/2026)
  Until today both cache writers split each search card's text by position.
  scripts/nhssc_card.py now reads each field from its own element, so new rows
  are right — but the ~4,800 rows already written stay wrong until something
  re-reads them, and the weekly refresh cannot be relied on to: it only sees
  what a term search returns, and since merge_items() it carries forward, by
  design, every line it did not see.

WHAT IT DOES
  1. Picks every item whose fields carry an old-parser fingerprint
     (nhssc_card.row_defects: mpc == npc, a badge as the brand, a one-token
     description, an all-letter MPC stored as a status).
  2. Queries pilot.supplychain.nhs.uk/search?query=<NPC> and accepts only the
     card whose own NPC badge is that exact code — the NPC is the identity, so
     there is nothing to guess.
  3. Replaces that item's name/supplier/desc/mpc/status/pack (and img, when the
     card has one) in EVERY entry that holds the NPC, name-keyed and NPC:-keyed.
  4. A row the catalogue no longer serves ("No results" for its own NPC) is
     kept and listed in the report; nothing is dropped and nothing is repaired
     by inference. The one exception is an MPC that is provably the NPC (the
     old parser's fallback, never a real MPC): it is blanked, an honest empty
     in place of a known-wrong value. 10 NPCs / 18 rows on 28/09/2026, all
     re-checked by hand and all "No results" live.

Fetches are checkpointed to --checkpoint so an interrupted run resumes.

Run:  python3 scripts/repair_nhssc_cache_rows.py [--checkpoint PATH] [--limit N] [--dry-run]
"""
import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nhssc_card import EXTRACT_JS, parse_card, row_defects  # noqa: E402

CACHE_PATH = "data/nhssc-cache.json"
CONC = 6
FIELDS = ("name", "supplier", "desc", "mpc", "status", "pack")


def affected_npcs(cache):
    out = {}
    for key, rec in (cache.get("products") or {}).items():
        for it in rec.get("items") or []:
            d = row_defects(it)
            npc = (it.get("npc") or "").strip()
            if d and npc:
                out.setdefault(npc, set()).update(d)
    return out


async def fetch_all(npcs, checkpoint):
    from playwright.async_api import async_playwright
    done = {}
    if checkpoint and os.path.exists(checkpoint):
        done = json.load(open(checkpoint))
    todo = [n for n in npcs if n not in done]
    print("to fetch: %d (already checkpointed: %d)" % (len(todo), len(done)), flush=True)
    lock = asyncio.Lock()
    counter = [0]

    async def worker(browser, batch):
        ctx = await browser.new_context(viewport={"width": 1200, "height": 900})
        page = await ctx.new_page()
        for npc in batch:
            got = None
            for attempt in range(2):
                try:
                    await page.goto("https://pilot.supplychain.nhs.uk/search?query=" + npc,
                                    timeout=20000, wait_until="domcontentloaded")
                    try:
                        await page.wait_for_selector("div.cardWrapper", timeout=8000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)
                    cards = await page.evaluate(EXTRACT_JS)
                    got = None
                    for c in cards:
                        p = parse_card(c)
                        if p and p["npc"] == npc:
                            got = p
                            break
                    break
                except Exception:
                    got = "error"
            async with lock:
                done[npc] = got
                counter[0] += 1
                if counter[0] % 100 == 0:
                    json.dump(done, open(checkpoint, "w"))
                    print("%d/%d fetched" % (counter[0], len(todo)), flush=True)
        await ctx.close()

    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        shards = [todo[i::CONC] for i in range(CONC)]
        await asyncio.gather(*[worker(b, sh) for sh in shards])
        await b.close()
    json.dump(done, open(checkpoint, "w"))
    return done


def apply(cache, fetched):
    """Write fetched cards over the misread rows. Returns counts and the
    NPCs left untouched, by reason."""
    stats = {"items_rewritten": 0, "items_unchanged_values": 0, "mpc_blanked_not_served": 0}
    missing = {}
    for key, rec in (cache.get("products") or {}).items():
        for it in rec.get("items") or []:
            npc = (it.get("npc") or "").strip()
            if not npc or not row_defects(it):
                continue
            if npc not in fetched:
                continue  # outside a --limit run
            p = fetched.get(npc)
            if not isinstance(p, dict):
                missing[npc] = "fetch error" if p == "error" else "not served by the catalogue"
                if p is None and "mpc-is-npc" in row_defects(it):
                    it["mpc"] = ""
                    stats["mpc_blanked_not_served"] += 1
                continue
            before = {f: it.get(f) for f in FIELDS}
            for f in FIELDS:
                it[f] = p[f]
            if p.get("img"):
                it["img"] = p["img"]
            if before == {f: it.get(f) for f in FIELDS}:
                stats["items_unchanged_values"] += 1
            else:
                stats["items_rewritten"] += 1
    return stats, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default="/tmp/nhssc-repair-checkpoint.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = json.load(open(CACHE_PATH))
    aff = affected_npcs(cache)
    npcs = sorted(aff)
    if args.limit:
        npcs = npcs[:args.limit]
    print("affected NPCs: %d" % len(aff), flush=True)
    fetched = asyncio.run(fetch_all(npcs, args.checkpoint))
    stats, missing = apply(cache, fetched)
    left = sum(1 for rec in cache["products"].values() for it in rec.get("items") or [] if row_defects(it))
    print(json.dumps(stats), "| NPCs not re-read: %d | items still carrying a fingerprint: %d"
          % (len(missing), left))
    for npc, why in sorted(missing.items()):
        print("  not re-read: %s (%s; %s)" % (npc, why, ",".join(sorted(aff.get(npc, [])))))
    if args.dry_run or args.limit:
        print("dry run / limited run: cache not written")
        return
    cache.setdefault("_meta", {})["rowRepair"] = {
        "when": time.strftime("%d/%m/%Y"), "script": "scripts/repair_nhssc_cache_rows.py",
        "npcsReRead": len([n for n in npcs if isinstance(fetched.get(n), dict)]),
        "notServed": len(missing), **stats}
    json.dump(cache, open(CACHE_PATH, "w"))
    print("written:", CACHE_PATH)


if __name__ == "__main__":
    main()
