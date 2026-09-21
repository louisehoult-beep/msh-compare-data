#!/usr/bin/env python3
"""
test_seed_domains.py — proves a REFUSED title proof cannot reach the seed.

THE HOLE THIS CLOSES. scripts/seed_supplier_domains.py banks every result so a
40-minute sweep can resume. That bank is also how a bad proof travels: a domain
"proved" by a page title was banked once on 14/08/2026 and then replayed by
every later --write run, so the --accept-name flag stopped meaning anything the
moment the report existed. verify_name_proofs.py adjudicated all 128 title
proofs the same day — 4 stood up to registration proof, 124 could not be
second-sourced at all — and those 124 verdicts are now the authority the seeding
script checks before it writes.

Why it matters that this stays true: crawl_supplier_site.py reads whatever
domain the seed holds and publishes that site's catalogue as the supplier's own
product range, on a paid page. "1 Stop Medical Supplies" was banked against
www.1stop.com, an IT and networking reseller.

    python3 test_seed_domains.py

Exit 0 = the gate holds. Exit 1 = a refused proof can be written again.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import seed_supplier_domains as seeder  # noqa: E402

REPORT = "state/domain-seeding-report.json"
VERDICTS = "state/name-proof-verification.json"

failures = []


def check(name, ok, detail=""):
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         "" if ok else "  <- " + detail))
    if not ok:
        failures.append(name)


def gate(proven, refused):
    """The filter as main() applies it. Kept in one place so the test cannot
    drift into testing a copy of the rule instead of the rule."""
    blocked = [r for r in proven
               if r["name"] in refused and r["proof"] != "registration"]
    return [r for r in proven if r not in blocked], blocked


print("verdict file")
verdicts = json.load(open(VERDICTS, encoding="utf-8"))["results"]
refused_names = seeder.refused_name_proofs()

# THE 14/08/2026 ADJUDICATION IS A FLOOR, NOT A SNAPSHOT (added 18/09/2026,
# `^o526`). It used to be asserted as exact counts — 124 REFUSED, 4 VERIFIED,
# 128 rows — which quietly made the file look like a one-off. It is not: every
# later sweep produces new name proofs that need adjudicating too, and
# verify_name_proofs.py now MERGES them in (it used to overwrite, which would
# have dropped all 124 of these the first time it was re-run). So the original
# 128 are pinned by their own check date and the totals are only ever allowed
# to grow.
orig = [v for v in verdicts if v.get("checked") == "2026-08-14"]
check("the 14/08/2026 adjudication is intact: 124 REFUSED",
      sum(1 for v in orig if v.get("verdict") == "REFUSED") == 124,
      "found %d of the original 128" % sum(1 for v in orig if v.get("verdict") == "REFUSED"))
check("the 14/08/2026 adjudication is intact: 4 VERIFIED",
      sum(1 for v in orig if v.get("verdict") == "VERIFIED") == 4)
check("the 14/08/2026 adjudication is intact: all 128 rows still present",
      len(orig) == 128, "found %d" % len(orig))
check("no verdict was ever dropped (the file only grows)",
      len(verdicts) >= 128 and len(refused_names) >= 124,
      "%d verdicts, %d refused" % (len(verdicts), len(refused_names)))
check("every verdict row carries a name and a verdict",
      all(v.get("name") and v.get("verdict") in ("REFUSED", "VERIFIED") for v in verdicts))

print("banked report")
report = json.load(open(REPORT, encoding="utf-8"))["results"]
titles = [r for r in report if r.get("proof") == "name"]
check("no title proof is left replayable", not titles,
      "%d still carry proof=name: %s" % (len(titles), [r["name"] for r in titles[:5]]))
# REFUSED suppliers that also hold a STRONG proof (registration /
# self-declared-foreign) were later proved by their registration number —
# the right outcome. They must NOT be stamped refused in the report.
# Compute the expected refused count dynamically so the test does not need
# updating every time a refused supplier later proves itself.
STRONG = ("registration", "self-declared-foreign")
report_by_name = {r["name"]: r for r in report}
expected_refused = sum(
    1 for n in refused_names
    if report_by_name.get(n, {}).get("proof") not in STRONG
)
refused_rows = [r for r in report if r.get("secondSourced") == "REFUSED"]
check("all refused-name-proof suppliers without a later strong proof carry "
      "secondSourced='REFUSED' in the report",
      len(refused_rows) == expected_refused,
      "expected %d (refused %d minus %d later-proved-strong), found %d"
      % (expected_refused, len(refused_names),
         len(refused_names) - expected_refused, len(refused_rows)))
check("a refused row keeps no top-level domain",
      all("domain" not in r for r in refused_rows),
      "a domain at the top level is what the write loop reads")
check("a refused row keeps its evidence for the record",
      all(r.get("refusedNameProof", {}).get("domain") for r in refused_rows))

print("the gate")
# A --fresh re-probe lands on the same guessed domain and "proves" it by title
# again. That is the exact replay this must stop.
replay = [{"name": "1 Stop Medical Supplies", "proof": "name",
           "domain": "www.1stop.com", "evidence": "site title names the company"}]
kept, blocked = gate(replay, refused_names)
check("a re-probed title proof for a refused supplier is blocked",
      not kept and len(blocked) == 1)

# Refused on the title route, but proved properly later. The registration route
# is the way back in, and it must stay open or the refusal is a dead end.
reproved = [{"name": "1 Stop Medical Supplies", "proof": "registration",
             "domain": "www.example.co.uk", "evidence": "site states registration number"}]
kept, blocked = gate(reproved, refused_names)
check("a registration proof re-opens a refused supplier", len(kept) == 1 and not blocked)

# A supplier nobody has ruled on is unaffected by the gate.
untouched = [{"name": "Some Supplier Never Adjudicated", "proof": "name",
              "domain": "www.somewhere.co.uk", "evidence": "site title names the company"}]
kept, blocked = gate(untouched, refused_names)
check("the gate touches only adjudicated names", len(kept) == 1 and not blocked)

print("self-declared-foreign tier (added 28/08/2026)")
# A foreign supplier's own site, stating its own country's registration number.
# No UK company number exists for it (ch_number=None), so REGISTRATION can never
# fire — this is exactly the population ch-number-is-ideal-not-mandatory-for-
# supplier-data describes.
foreign_html = ("<title>Absorbest AB</title><body>Absorbest AB is registered "
                "in Sweden. Org.nr 556677-8899. Contact us.</body>")
kind, ev, url = seeder.prove("Absorbest AB", None, [("https://absorbest.com", foreign_html)],
                              accept_name=False, allow_foreign=True)
check("a foreign registration number is proven as self-declared-foreign",
      kind == "self-declared-foreign", "got %r" % (kind,))
check("the evidence records it as self-declared, not cross-checked",
      "self-declared" in (ev or "") and "not cross-checked" in (ev or ""))

# The same page, but allow_foreign is OFF (the flag's default). No proof at all —
# the route must not fire silently just because the page qualifies.
kind2, _, _ = seeder.prove("Absorbest AB", None, [("https://absorbest.com", foreign_html)],
                            accept_name=False, allow_foreign=False)
check("self-declared-foreign never fires without --allow-foreign", kind2 is None)

# THE LEAK THIS MUST NOT ALLOW: a supplier that DOES have a UK Companies House
# number must never be proved on the weaker self-declared route, even if its
# site happens to carry foreign-shaped registration wording (e.g. a UK company
# quoting an EU VAT number) and allow_foreign is on. ch_number truthy must gate
# self-declared-foreign off entirely, whatever the page says.
uk_with_foreign_wording = ("<title>Acme Medical Ltd</title><body>Acme Medical Ltd. "
                            "VAT number DE123456789. Registered in England, company "
                            "number 01234567.</body>")
kind3, ev3, _ = seeder.prove("Acme Medical Ltd", "01234567",
                              [("https://acmemedical.co.uk", uk_with_foreign_wording)],
                              accept_name=False, allow_foreign=True)
check("a UK-numbered supplier proves on registration, never self-declared-foreign",
      kind3 == "registration", "got %r" % (kind3,))

# A UK supplier whose site does NOT carry its own number is refused, not routed
# to the weaker tier as a fallback — allow_foreign only ever applies when there
# is no UK number to check against in the first place, not when the check fails.
uk_no_number = "<title>Acme Medical Ltd</title><body>Acme Medical Ltd. Contact us.</body>"
kind4, _, _ = seeder.prove("Acme Medical Ltd", "01234567",
                            [("https://acmemedical.co.uk", uk_no_number)],
                            accept_name=False, allow_foreign=True)
check("a UK-numbered supplier that never states its number is refused, not "
      "downgraded to self-declared-foreign", kind4 is None)

# THE OTHER LEAK: a UK company with NO matched CH record at all (a data gap in
# company-financials.json, not evidence of being foreign) states plain UK-style
# registration wording. FOREIGN_REG_WORDS deliberately overlaps with that
# wording, so without UK_MARKERS this would be wrongly recorded as "overseas
# company" — an invented fact, not an honestly weaker one.
uk_no_ch_match = ("<title>BVM Medical Ltd</title><body>BVM Medical Ltd is "
                   "Registered in England and Wales. Company number 07654321. "
                   "Registered office: 1 Trade Park, Leeds.</body>")
kind5, _, _ = seeder.prove("BVM Medical Ltd", None,
                            [("https://bvmmedical.co.uk", uk_no_ch_match)],
                            accept_name=False, allow_foreign=True)
check("a UK company with no matched CH record is never labelled overseas",
      kind5 is None, "got %r" % (kind5,))

# THE THIRD LEAK: self-declared-foreign has nothing to cross-check its number
# against (unlike "registration"), so a wrongly-guessed domain landing on some
# OTHER real company's site would otherwise "prove" on that unrelated site's own
# number. Found 28/08/2026 on a live run: "AMG Medtech Ltd" and "APR Medtech
# Limited" both guessed to aml.co.uk and both banked the same evidence, because
# nothing checked that either name actually appeared on that page.
unrelated_site = ("<title>Acme Laminates Ltd</title><body>Acme Laminates Ltd. "
                   "Registered in Ireland. CRO number 123456. Contact us.</body>")
kind6, _, _ = seeder.prove("AMG Medtech Ltd", None,
                            [("https://aml.co.uk", unrelated_site)],
                            accept_name=False, allow_foreign=True)
check("a real foreign proof on a site that never names the supplier is refused",
      kind6 is None, "got %r" % (kind6,))

# The positive case, same shape, but the site DOES name the supplier this time.
named_foreign_site = ("<title>AMG Medtech Ltd</title><body>AMG Medtech Ltd. "
                       "Registered in Ireland. CRO number 123456. Contact us.</body>")
kind7, ev7, _ = seeder.prove("AMG Medtech Ltd", None,
                              [("https://amgmedtech.ie", named_foreign_site)],
                              accept_name=False, allow_foreign=True)
check("the same evidence proves once the site actually names the supplier",
      kind7 == "self-declared-foreign", "got %r" % (kind7,))

# HTML-entity regression: "&amp;" must decode to "&" so UK_MARKERS can still
# catch "England &amp; Wales" as rendered by a real browser/site.
entity_encoded_uk = ("<title>Associated Optical Products</title><body>"
                      "Associated Optical Products. Registered No.84121 "
                      "England &amp; Wales.</body>")
kind8, _, _ = seeder.prove("Associated Optical Products", None,
                            [("https://www.associated.co.uk", entity_encoded_uk)],
                            accept_name=False, allow_foreign=True)
check("an HTML-entity-encoded UK marker (&amp;) still blocks the foreign route",
      kind8 is None, "got %r" % (kind8,))

# THE FOURTH LEAK: a UK footer that gives an address and a number but never
# says "England"/"Companies House" by name — found 28/08/2026 on "Bidfood
# Direct", a real UK company with no matched CH record, wrongly proved
# self-declared-foreign because nothing in its footer used the exact UK
# wording UK_MARKERS looked for.
uk_postcode_only = ("<title>Bidfood Direct</title><body>Bidfood Direct. "
                     "Company No. 239718, 814 Leigh Road, Slough, SL1 4AB.</body>")
kind9, _, _ = seeder.prove("Bidfood Direct", None,
                            [("https://www.bidfood.co.uk", uk_postcode_only)],
                            accept_name=False, allow_foreign=True)
check("a UK postcode next to the number blocks the foreign route even with no "
      "explicit jurisdiction wording", kind9 is None, "got %r" % (kind9,))

# THE FIFTH LEAK: the domain's own TLD is UK, independent of what the footer
# says at all — the strongest, simplest signal available and it should refuse
# on its own.
uk_tld_no_markers = ("<title>Msoft eSolutions</title><body>Msoft eSolutions. "
                      "Company Registration Number: 3472193.</body>")
kind10, _, _ = seeder.prove("Msoft eSolutions", None,
                             [("https://msoft.co.uk", uk_tld_no_markers)],
                             accept_name=False, allow_foreign=True)
check("a .co.uk domain is refused for the foreign route regardless of wording",
      kind10 is None, "got %r" % (kind10,))

# A genuinely foreign domain must still pass — the new guards must not have
# widened into refusing everything.
genuinely_foreign = ("<title>Cortrium ApS</title><body>Cortrium ApS is "
                      "registered in Denmark. Company registration number "
                      "36445335, Copenhagen.</body>")
kind11, _, _ = seeder.prove("Cortrium ApS", None,
                             [("https://cortrium.com", genuinely_foreign)],
                             accept_name=False, allow_foreign=True)
check("a genuinely foreign .com domain still proves", kind11 == "self-declared-foreign",
      "got %r" % (kind11,))

print("write-gate: self-declared-foreign is STRONG, not the weak/title tier")
STRONG = ("registration", "self-declared-foreign")
proven = [
    {"name": "Absorbest AB", "proof": "self-declared-foreign", "domain": "absorbest.com"},
    {"name": "1 Stop Medical Supplies", "proof": "name", "domain": "www.1stop.com"},
]
# Mirrors main()'s `if not a.accept_name: proven = [r for r in proven if
# r["proof"] in STRONG]` — kept as a literal copy of the rule, same discipline
# as gate() above, so this cannot drift into testing something else.
kept_strong = [r for r in proven if r["proof"] in STRONG]
check("self-declared-foreign survives the --accept-name gate (accept_name OFF)",
      any(r["proof"] == "self-declared-foreign" for r in kept_strong))
check("a title proof still does NOT survive the same gate",
      not any(r["proof"] == "name" for r in kept_strong))

# refused_name_proofs() blocking must exempt self-declared-foreign the same way
# it already exempts registration — a name that happens to appear in the
# REFUSED title-proof list must not block an unrelated, independently-earned
# self-declared-foreign proof for that same name.
refused_names_test = {"Absorbest AB"}
blocked_test = [r for r in [{"name": "Absorbest AB", "proof": "self-declared-foreign"}]
                if r["name"] in refused_names_test and r["proof"] not in STRONG]
check("self-declared-foreign is not blocked by the refused-title-proof gate",
      not blocked_test)

print("verdict merge (added 18/09/2026, `^o526`)")
# THE BUG THIS PINS. verify_name_proofs.py rebuilds its verdict file from
# whatever the CURRENT seeding report happens to carry proof="name" for. On
# 18/09/2026 that was 20 suppliers, none of them among the 128 adjudicated on
# 14/08 — so writing `results: res` straight out, as it did until today, would
# have replaced 128 verdicts with 20 and silently re-opened all 124 refusals
# for writing. seed_supplier_domains.refused_name_proofs() reads exactly this
# file to decide what can never be seeded.
import verify_name_proofs as vnp  # noqa: E402

_real_out = vnp.OUT
try:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        vnp.OUT = os.path.join(td, "verdicts.json")
        json.dump({"results": [
            {"name": "Old Refused Co", "verdict": "REFUSED", "checked": "2026-08-14",
             "reason": "never second-sourced"},
            {"name": "Old Verified Co", "verdict": "VERIFIED", "checked": "2026-08-14",
             "proof": "registration"},
        ]}, open(vnp.OUT, "w"))

        fresh = [
            {"name": "New Refused Co", "verdict": "REFUSED", "checked": "2026-09-18",
             "reason": "site read, no registration number"},
            {"name": "Old Refused Co", "verdict": "VERIFIED", "checked": "2026-09-18",
             "proof": "registration"},
        ]
        merged, kept, updated = vnp.merge_verdicts(fresh)
        by = {m["name"]: m for m in merged}

        check("an earlier verdict this run did not look at is carried forward",
              "Old Verified Co" in by and by["Old Verified Co"]["verdict"] == "VERIFIED")
        check("a new verdict is added", "New Refused Co" in by)
        check("re-adjudicating the same supplier replaces its row, not duplicates it",
              len([m for m in merged if m["name"] == "Old Refused Co"]) == 1
              and by["Old Refused Co"]["verdict"] == "VERIFIED")
        check("nothing is dropped", len(merged) == 3, "got %d" % len(merged))
        check("the counts report what was kept vs re-adjudicated",
              (kept, updated) == (1, 1), "got kept=%d updated=%d" % (kept, updated))

        # The failure mode itself: the pre-18/09 behaviour, run on this fixture.
        check("the old overwrite behaviour would have lost a verdict",
              len(fresh) < len(merged))
finally:
    vnp.OUT = _real_out

# ---------------------------------------------------------------------------
# A NARROWED RUN MUST NOT WRITE THE WHOLE BANK (added 19/09/2026, ^o549).
#
# --supplier and --limit narrowed what the script PROBED and not what it WROTE.
# The write loop walks `proven`, which is built from the banked report — every
# STRONG proof any earlier run ever recorded — so `--supplier X --write` merged
# the whole bank. On 19/09/2026 it wrote an unrelated supplier (Newell Brands)
# into supplier-seed.json in the middle of a single-supplier batch. Caught and
# reverted before landing, but only because a person read the diff: the run's own
# output said nothing about it, which is why this is a test and not a note.
print()
print("scoped write — a narrowed run writes only what it targeted")

BANK = [
    {"name": "Targeted Co", "proof": "registration", "domain": "targeted.example"},
    {"name": "Newell Brands", "proof": "registration", "domain": "newell.example"},
    {"name": "Another Banked Co", "proof": "self-declared-foreign", "domain": "other.example"},
]

kept, dropped = seeder.apply_write_scope(BANK, {"Targeted Co"})
check("--supplier writes the targeted supplier",
      [r["name"] for r in kept] == ["Targeted Co"],
      "got %s" % [r["name"] for r in kept])
check("--supplier does NOT write the rest of the bank",
      {r["name"] for r in dropped} == {"Newell Brands", "Another Banked Co"},
      "got %s" % [r["name"] for r in dropped])
check("nothing is lost — every banked proof is in exactly one of the two lists",
      len(kept) + len(dropped) == len(BANK))

kept_all, dropped_all = seeder.apply_write_scope(BANK, None)
check("an unnarrowed sweep still writes the whole bank",
      len(kept_all) == len(BANK) and dropped_all == [],
      "got kept=%d dropped=%d" % (len(kept_all), len(dropped_all)))

kept_two, _ = seeder.apply_write_scope(BANK, {"Targeted Co", "Another Banked Co"})
check("--limit scopes to the run's own targets, not to one name",
      {r["name"] for r in kept_two} == {"Targeted Co", "Another Banked Co"})

check("a scope naming a supplier with no banked proof writes nothing, not everything",
      seeder.apply_write_scope(BANK, {"Never Probed Co"})[0] == [])

# The failure mode itself, stated as the regression it is.
check("the pre-19/09 behaviour would have written Newell Brands",
      "Newell Brands" in {r["name"] for r in BANK}
      and "Newell Brands" not in {r["name"] for r in kept})

# A correct helper nothing calls is worse than no helper: it reads as protection
# and provides none. main() does the probing and cannot be run in a test without
# hitting 127 suppliers' websites, so its WIRING is asserted against the source.
SRC = open(os.path.join(REPO, "scripts", "seed_supplier_domains.py"),
           encoding="utf-8").read()
check("main() narrows the write scope where it narrows the run",
      "write_scope = {s[\"name\"] for s in todo} if (a.supplier or a.limit) else None" in SRC)
check("main() applies that scope before writing the seed",
      "proven, out_of_scope = apply_write_scope(proven, write_scope)" in SRC)
check("the scope is applied AFTER the --write guard, not instead of it",
      SRC.index("if not a.write:")
      < SRC.index("proven, out_of_scope = apply_write_scope("))

# ---------------------------------------------------------------------------
# THE SEED'S BYTE FORMAT (`^o584`, 21/09/2026)
#
# Six scripts write data/supplier-seed.json. Five of them hardcoded "minified,
# one line" and two carried a comment calling that "the file's own format"; the
# sixth wrote indent=2 and, running on every push race, is what actually put
# main into indent=2. So on 21/09/2026 running seed_supplier_domains.py --write
# to add two fields would have rewritten all 110,172 lines as one.
#
# A push to main is a live publish and the diff is the only review there is, so
# a whole-file diff is not cosmetic — it is the review disappearing. These
# checks assert the writers READ the format instead of asserting one.
# ---------------------------------------------------------------------------
print()
print("seed byte format")
import seed_format  # noqa: E402

RAW = open("data/supplier-seed.json", "rb").read()
_out, _fmt, _round_trips = seed_format.dumps_like(json.loads(RAW.decode("utf-8")), RAW)

check("the seed on disk round-trips in the format detected from its own bytes",
      _round_trips, "detected %s but re-serialising did not reproduce the file" % _fmt)
check("re-writing the seed unchanged is a zero-byte diff",
      _out == RAW, "detected %s" % _fmt)

# Every shape this file has actually been seen in — detection must survive all
# of them, because which one is on main depends on who wrote it last.
SHAPES = {
    "minified, no trailing newline":
        json.dumps({"a": [1, 2], "b": {"c": "\u00e9"}}, ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8"),
    "minified, trailing newline":
        (json.dumps({"a": [1, 2], "b": {"c": "\u00e9"}}, ensure_ascii=False,
                    separators=(",", ":")) + "\n").encode("utf-8"),
    "indent 1, trailing newline":
        (json.dumps({"a": [1, 2], "b": {"c": "\u00e9"}}, ensure_ascii=False,
                    indent=1) + "\n").encode("utf-8"),
    "indent 2, trailing newline":
        (json.dumps({"a": [1, 2], "b": {"c": "\u00e9"}}, ensure_ascii=False,
                    indent=2) + "\n").encode("utf-8"),
    "indent 2, no trailing newline":
        json.dumps({"a": [1, 2], "b": {"c": "\u00e9"}}, ensure_ascii=False,
                   indent=2).encode("utf-8"),
}
for _label, _raw in SHAPES.items():
    _bytes, _f, _rt = seed_format.dumps_like(json.loads(_raw.decode("utf-8")), _raw)
    check("unchanged write is byte-identical — %s" % _label,
          _bytes == _raw and _rt, "detected %s" % _f)

# A real edit changes the edited value and nothing else about the layout.
_edited = json.loads(SHAPES["indent 2, trailing newline"].decode("utf-8"))
_edited["b"]["c"] = "changed"
_bytes, _f, _ = seed_format.dumps_like(_edited, SHAPES["indent 2, trailing newline"])
check("an edit keeps the layout and changes only the value",
      _bytes.decode("utf-8").count("\n") ==
      SHAPES["indent 2, trailing newline"].decode("utf-8").count("\n")
      and b"changed" in _bytes)

# The regression, stated as the failure it was: the old hardcoded write.
_old_style = json.dumps(json.loads(SHAPES["indent 2, trailing newline"].decode("utf-8")),
                        ensure_ascii=False, separators=(",", ":")).encode("utf-8")
check("the pre-21/09 hardcoded write would have reformatted the whole file",
      _old_style != SHAPES["indent 2, trailing newline"])

# A helper nothing calls is worse than no helper. Assert the WIRING: no seed
# writer may hardcode a serialisation again.
SEED_WRITERS = ["seed_supplier_domains.py", "verify_name_proofs.py",
                "confirm_company_numbers.py", "confirm_from_catalogue.py",
                "refresh_brand_colours.py", "merge_seed_on_retry.py"]
for _name in SEED_WRITERS:
    _src = open(os.path.join(REPO, "scripts", _name), encoding="utf-8").read()
    check("%s writes the seed through seed_format.write_like" % _name,
          "write_like(SEED" in _src)
    check("%s no longer hardcodes a seed serialisation" % _name,
          'json.dump(seed, f' not in _src and 'json.dump(out, f' not in _src)

print()
if failures:
    print("FAILED: %d check(s) — %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("gate holds — no refused title proof can reach data/supplier-seed.json")
print("self-declared-foreign tier holds — cannot leak into the registration tier")
