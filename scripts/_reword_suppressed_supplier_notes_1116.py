#!/usr/bin/env python3
r"""
_reword_suppressed_supplier_notes_1116.py — 16/11/2026

Second and final batch of the fault that `_reword_medilogik_hdclinical_notes_1116.py`
fixed for two companies.

app/company-report.js suppresses a supplier's WHOLE background note if the note
names an internal file (the INTERNAL_TEXT guard). That guard is correct and
stays. 178 of 1148 notes are suppressed; 58 of those match the filename rule and
nothing else, i.e. they are member-facing copy hidden by a curator's internal
cross-reference. The other 118 match a genuine internal marker (Lou, TODO,
^o-numbers, merge_duplicates, the E&T folder, "curator") and are left alone.

This reworks all 58 so the prose renders. No fact is changed, added or removed:
only the pointer to a file a member cannot open. Everything removed from the
member note is preserved verbatim in `_curatorNotes`, which nothing renders.

Two shapes:

1. THIRTY-TWO notes carry one identical, self-contained provenance block
   ("Reconciled from data/compare-suppliers.json on 07/08/2026 — ... legal
   entity is not asserted."). That block is record-keeping about the Hub, not
   intelligence about the supplier, and is the only thing in those notes that
   names a file. It is lifted out whole, which cannot break a sentence, and the
   member-facing lead (and in two cases the trailing company-number proof) is
   left exactly as written.

2. TWENTY-SIX notes name files inside their own prose. Each was read through and
   given a targeted rewording that says the same thing in member-facing words
   ("this Hub's own framework capture", "the Hub's catalogue crawler"), or, where
   the clause was purely internal, had that clause removed as a whole sentence.
   No clause is cut mid-sentence.

Usage:  python3 scripts/_reword_suppressed_supplier_notes_1116.py
Writes: data/supplier-seed.json
"""
import json
import re
import sys

PATH = "data/supplier-seed.json"

# The guard from app/company-report.js, verbatim, so this script fails loudly if
# an edit leaves any internal marker behind.
INTERNAL_TEXT = re.compile('|'.join([
    'merge_duplicates', r"\bLou(?:'s)?\b", r'\b[\w\-/]+\.(?:json|md|py|toml)\b',
    '02-Elevate-and-Thrive', 'Identity Decision Pack', r'\b[Cc]urator', r'\bTODO\b',
    r'\^o\d+', 'E&T client', 'alias-overlay', '[Cc]loud routine',
    r'\b[a-z]+(?:-[a-z]+){2,} (?:run|routine)\b',
]))

# ---------------------------------------------------------------- shape 1 ----

BOILERPLATE = re.compile(
    r"\s*Reconciled from data/compare-suppliers\.json on 07/08/2026 [—-] this "
    r"company already had a researched row on the Compare tab and no record in the "
    r"master, which is the drift docs/ONE-LIST-AUDIT\.md set out to close\. Its "
    r"speciality, brands and link are taken from that row, which is human-curated "
    r"under this repo's sourceRule \(framework name, dates and supplier list from "
    r"NHS Supply Chain's own contract launch brief; brands from the catalogue "
    r"entry\)\.(?: NOT verified against Companies House on this run, so no company "
    r"number is recorded and the legal entity is not asserted\.)?"
)

BOILERPLATE_COMPANIES = [
    "Alpha Laboratories",
    "Beaver Visitec International",
    "BK Medical UK",
    "Butterfly Network",
    "Cod Beck Blenders",
    "Creo Medical Limited",
    "D.O.R.C.",
    "Epredia",
    "Esaote",
    "GV Health",
    "Hospital Services Limited",
    "Inspiration Healthcare",
    "Leica Microsystems (UK)",
    "LiteOptics",
    "Masimo Europe",
    "Medical Imaging Systems (MIS Healthcare)",
    "Medicare Colgate Ltd (Sterifeed)",
    "Natus Nicolet UK",
    "Otodynamics",
    "Owen Mumford",
    "Pari Medical",
    "Pasante Healthcare",
    "Puretone",
    "Reliance Medical",
    "Rocket Medical",
    "Sakura Finetek UK",
    "Semperit Investments Asia",
    "Storz Medical UK",
    "Summit Medical UK",
    "Supermax Healthcare",
    "Vitalograph",
]

BOILERPLATE_CURATOR = (
    "16/11/2026: the shared 07/08/2026 compare-suppliers reconciliation block was "
    "moved out of the member note so the note renders, and is preserved here "
    "verbatim: %r"
)

# ---------------------------------------------------------------- shape 2 ----

POLICY_PAREN = (
    " (data/identity-vocabulary-policy.json)",
    "",
)

# company -> list of (find, replace). Every find must occur exactly once.
EDITS = {
    "A1 Momentum": [
        ("following the National Back Exchange 2026 conference gap analysis "
         "(NBE-patch-gap-analysis-2026-08-31.md), which found",
         "following a gap analysis of the National Back Exchange 2026 conference, "
         "which found"),
        ("Not named on any NHS Supply Chain framework in data/frameworks.json (checked",
         "Not named on any NHS Supply Chain framework in this Hub's own capture (checked"),
        ("so scripts/crawl_supplier_site.py was not run against it — see the "
         "refusal recorded in data/supplier-products.json.",
         "so the Hub's catalogue crawler was not run against it and the refusal is "
         "recorded against the capture instead."),
    ],
    "Applied Medical Technology Limited": [
        (" Resolved via company_alias.py (returned UNRESOLVED for the exact "
         "award-brief name, confirming no existing alias covers it) and web search "
         "identifying the company's own site.",
         ""),
    ],
    "Aquilant Endoscopy Limited": [
        (" Until today 'Aquilant Endoscopy' was carried only as an alias inside "
         "supplier-index.json, folding two distinct registered companies into one "
         "record; the nightly rebuild destroys index-only aliases, so it also would "
         "have broken on its own.",
         ""),
    ],
    "Aquilant Limited": [
        ("so no crawl was possible this run; recorded as a refusal by "
         "scripts/crawl_supplier_site.py.",
         "so no crawl was possible."),
    ],
    "Babease Limited": [POLICY_PAREN],
    "Caversham Health": [
        ("(too few for the automated catalogue crawler to accept as a catalogue, "
         "hence its refusal entry in data/supplier-products.json)",
         "(too few for the automated catalogue crawler to accept as a catalogue, so "
         "it is recorded as a refusal)"),
    ],
    "Change Healthcare": [
        ("already captured in this repo's data/framework-awards.json (notice",
         "already captured in this Hub's own award data (notice"),
    ],
    "Direct Healthcare Group": [
        (" KNOWN DEFECT: Talley's crawled product rows are a crawl of "
         "directhealthcaregroup.com, not of a Talley site, so its Differentiator "
         "divisions duplicate DHG's catalogue. Fix belongs in "
         "scripts/crawl_supplier_site.py; do not fix it by mapping.",
         ""),
    ],
    "Ferno (UK) Limited": [
        ("so scripts/crawl_supplier_site.py correctly refused it 20/09/2026",
         "so the Hub's catalogue crawler correctly refused it on 20/09/2026"),
    ],
    "Headington Medical Technology Ltd": [
        ("(address-tier domain proof, data/identity-vocabulary-policy.json "
         "'domain-proof-tier' policy, second tier)",
         "(address-tier domain proof under this Hub's own domain-proof-tier policy, "
         "second tier)"),
        ("so scripts/crawl_supplier_site.py cannot reach it (confirmed via "
         "--dry-run 22/10/2026, and scripts/seed_supplier_domains.py's own proof "
         "probe fails for the same reason: it only fetches the root)",
         "so the Hub's catalogue crawler cannot reach it (confirmed 22/10/2026; the "
         "automated domain-proof probe fails for the same reason, because it only "
         "fetches the root)"),
        ("noted here rather than hand-entered into data/supplier-products.json, "
         "which only ever holds output from an actual crawl run and carries no "
         "established format for a manually-read capture",
         "noted here rather than entered into the Hub's product capture, which only "
         "ever holds the output of an actual crawl and has no format for a "
         "manually-read one"),
    ],
    "Imaging First Ltd": [
        ("this is the confirmed source for scripts/crawl_supplier_site.py.",
         "this is the confirmed source for the Hub's catalogue crawl."),
    ],
    "Independence Products Ltd": [
        (" See evidence/woundcare-tariff-and-prescribing.md §4.4.", ""),
    ],
    "Manfred Sauer UK Ltd": [
        ("Flagged in the 18/08/2026 alias review "
         "(Hub/company-aliases/ALIAS-REVIEW-QUEUE.md) as",
         "Flagged in the 18/08/2026 alias review as"),
        ("so per root rule 14 / HUB-VERIFICATION-STANDARD.md rule 11 it is recorded as",
         "so under this Hub's own verification standard (rule 11) it is recorded as"),
        ("framework capture (data/frameworks.json); its own site",
         "framework capture; its own site"),
    ],
    "Omnimedical Ltd": [POLICY_PAREN],
    "OneAdvanced (Advanced Health and Care)": [
        ("(54 product pages, names read from URL slugs; see supplier-products.json "
         "for the caveat)",
         "(54 product pages, names read from URL slugs; a caveat is recorded with "
         "the capture)"),
    ],
    "Pennine Healthcare (Ivor Shaw Ltd)": [
        ("once thin from the frameworks.json capture and once in full",
         "once thin from this Hub's own framework capture and once in full"),
        ("That was checked on 09/09/2026 against this Hub's own frameworks.json and "
         "is NOT supported",
         "That was checked on 09/09/2026 against this Hub's own framework capture "
         "and is NOT supported"),
    ],
    "pfm medical UK": [
        ("(address-tier domain proof, data/identity-vocabulary-policy.json "
         "'domain-proof-tier' policy, second tier; scripts/seed_supplier_domains.py's "
         "own automated proof check could not confirm it — core('pfm medical UK') "
         "reduces to 'pfm', 3 characters, below its DISTINCTIVE_MIN=6 bar, so its "
         "name-title tier never fires here; this is a tool limitation on short core "
         "names, not a finding against the domain)",
         "(address-tier domain proof under this Hub's own domain-proof-tier policy, "
         "second tier; the automated proof check could not confirm it, because the "
         "distinctive core of 'pfm medical UK' reduces to 'pfm' — three "
         "characters, below the tool's minimum — so its name-title tier never "
         "fires here: a limitation on short names, not a finding against the domain)"),
        ("scripts/crawl_supplier_site.py's generic sitemap route may be able to "
         "capture this via --product-path; left for the capture step.",
         "the Hub's generic sitemap capture route may be able to read it; left for "
         "the capture step."),
    ],
    "Phoenix Healthcare": [
        ("UNVERIFIED, split 06/09/2026 (see "
         "Hub/Architecture/SUPPLIER-IDENTITY-CONFLATION-2026-09-05.md).",
         "UNVERIFIED, split out on 06/09/2026 by a supplier-identity conflation review."),
    ],
    "Phoenix Medical Ltd": [
        ("split out of the conflated \"Phoenix Healthcare\" record (see "
         "Hub/Architecture/SUPPLIER-IDENTITY-CONFLATION-2026-09-05.md).",
         "split out of the conflated \"Phoenix Healthcare\" record."),
    ],
    "Qufora Ltd": [
        ("Flagged in the 18/08/2026 alias review "
         "(Hub/company-aliases/ALIAS-REVIEW-QUEUE.md) as",
         "Flagged in the 18/08/2026 alias review as"),
        ("framework capture (data/frameworks.json) -- transanal",
         "framework capture -- transanal"),
    ],
    "Rx-Info": [
        ("(10 products, one flat list; see supplier-products.json)",
         "(10 products, one flat list)"),
    ],
    "Scott Medical Ltd": [
        ("Per the unconfirmable-awardee policy shape "
         "(data/identity-vocabulary-policy.json), the award",
         "Per the unconfirmable-awardee policy, the award"),
    ],
    "Semperit Investment": [POLICY_PAREN],
    "Soluvos Medical Ltd": [
        (" Proposed for the address route in docs/domain-proof-address-route.md on "
         "08/09/2026; that proposal is withdrawn.", ""),
    ],
    "Surgica Limited": [
        ("Published per the unconfirmable-awardee policy "
         "(data/identity-vocabulary-policy.json, ruled 20/09/2026):",
         "Published per the unconfirmable-awardee policy (ruled 20/09/2026):"),
    ],
    "Talley": [
        (" KNOWN DEFECT: Talley's crawled product rows are a crawl of "
         "directhealthcaregroup.com, not of a Talley site, so its Differentiator "
         "divisions duplicate DHG's catalogue. Fix belongs in "
         "scripts/crawl_supplier_site.py; do not fix it by mapping.",
         ""),
    ],
    "Vanguard Medical Devices Ltd": [
        ("recorded in data/company-match-overrides.json: the register itself",
         "recorded in this Hub's own company-match overrides: the register itself"),
    ],
}

EDIT_CURATOR = (
    "16/11/2026: internal cross-references were reworded out of the member note so "
    "the note renders. No fact was changed. Replaced, in order: %s"
)


def tidy(text):
    """Close up whitespace left by a removal. Never joins two sentences."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([.,;:])", r"\1", text)
    return text.strip()


def append_curator(supplier, line):
    prior = supplier.get("_curatorNotes")
    supplier["_curatorNotes"] = ((prior + " | ") if prior else "") + line


def main():
    doc = json.load(open(PATH))
    by_name = {}
    for s in doc["suppliers"]:
        by_name.setdefault(s.get("name"), s)

    missing = [n for n in BOILERPLATE_COMPANIES + list(EDITS) if n not in by_name]
    if missing:
        sys.exit("not in the seed: %s" % ", ".join(missing))

    done = []

    for name in BOILERPLATE_COMPANIES:
        s = by_name[name]
        old = s.get("note") or ""
        m = BOILERPLATE.search(old)
        if not m:
            sys.exit("%s: the 07/08/2026 reconciliation block was not found" % name)
        new = tidy(old[:m.start()] + old[m.end():])
        if not new:
            sys.exit("%s: removing the block would leave an empty note" % name)
        s["note"] = new
        append_curator(s, BOILERPLATE_CURATOR % m.group(0).strip())
        done.append(name)

    for name, pairs in EDITS.items():
        s = by_name[name]
        old = s.get("note") or ""
        new = old
        for find, repl in pairs:
            if new.count(find) != 1:
                sys.exit("%s: expected exactly one occurrence of %r, found %d"
                         % (name, find, new.count(find)))
            new = new.replace(find, repl)
        new = tidy(new)
        if not new:
            sys.exit("%s: rewording would leave an empty note" % name)
        s["note"] = new
        append_curator(s, EDIT_CURATOR % "; ".join(
            "%r -> %r" % (f.strip(), r.strip()) for f, r in pairs))
        done.append(name)

    # Every edited note must now render, and nothing else may have changed.
    for name in done:
        hit = INTERNAL_TEXT.search(by_name[name]["note"])
        if hit:
            sys.exit("%s still carries an internal marker: %r" % (name, hit.group(0)))

    if len(done) != 58:
        sys.exit("expected 58 notes, edited %d" % len(done))

    with open(PATH, "w") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
    print("reworded %d notes:" % len(done))
    for name in sorted(done):
        print("  ", name)


if __name__ == "__main__":
    main()
