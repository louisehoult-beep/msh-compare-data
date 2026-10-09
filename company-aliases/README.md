# Company aliases — one name per company, across every Hub source

**The problem this solves.** The same company arrives under a different name from every
source. NHS Supply Chain writes "Stryker UK Limited". Find a Tender writes "STRYKER UK LTD".
The trade press writes "Stryker". The company's own site writes "Stryker UK". Left alone that
produces duplicate rows on the compare tab, a supplier that looks like two suppliers, and a
"no results" that reads to a paying member as "not on the framework".

**The rule.** Before any company name is published to the Hub, the Rep's Briefing or any
member-facing asset, it is resolved through this registry. A name that will not resolve does
not publish — it becomes a question, not a guess.

## Use it

```bash
python3 company_alias.py resolve "STRYKER UK LTD"
```

```bash
python3 company_alias.py check names.txt
```

`resolve` takes one or more names. `check` takes a file of names, one per line, or `-` for
stdin. Add `--json` for machine-readable output. Exit codes are the check:

| Exit | Meaning |
|---|---|
| 0 | every name resolved to one company |
| 1 | at least one name UNRESOLVED, or the overlay is malformed |
| 2 | at least one name AMBIGUOUS — it matched two different companies |

`python3 company_alias.py selftest` proves the gate still catches what it was built for.
`python3 company_alias.py build` rebuilds the registry; run it after editing the overlay or
the supplier seed.

## What resolves without anybody doing anything

Legal suffixes and territory words are stripped mechanically, so none of these need an entry
anywhere: `Ltd` `Limited` `plc` `LLP` `Inc` `GmbH` `BV` `A/S` `AB` `Oy` `Pty`, and trailing
`UK` `GB` `England` `Ireland` `Europe` `EMEA`. Case, punctuation and `&` versus `and` are
handled too. `Smith and Nephew plc` and `Smith & Nephew` both reach `Smith+Nephew`.

What normalisation **cannot** reach is renames, acquisitions, trading names and brand-versus-
entity. Those need a human to confirm them once, and then they are recorded.

## The three files

| File | Edit it? | What it is |
|---|---|---|
| `alias-overlay.json` | **Yes — by hand** | The only hand-maintained file. For companies the supplier seed does not carry, and for declared ambiguities. |
| `company-alias-registry.json` | **No — generated** | Built from the seed plus the overlay. Overwritten on every build. |
| `ALIAS-REVIEW-QUEUE.md` | Working list | Names found in Hub data that look like an existing company but have not been settled. |

The master alias data is **not** here. It lives in each supplier's record in
`Medical-Sales-Hub/Website/msh-compare-data/data/supplier-seed.json`, which this reads.
**When the company is a Hub supplier, add the alias to the seed, not the overlay** — the
nightly rebuild regenerates `supplier-index.json` from the seed, so an alias written anywhere
else is thrown away, and the compare tab needs it too. Use the overlay only for companies
that are not in the seed at all.

## Why it refuses instead of guessing

There is no fuzzy matching here, on purpose. Substring and edit-distance matching is how
homonyms get merged, and a merged homonym publishes a false statement about a real company
under the Hub's name. "Pentax Medical UK Limited" is not "Pentax UK Limited".

When a name will not resolve, the tool prints names that merely *look* similar, clearly
labelled as not a match. They are a hint for a person, never an answer.

**Two different real companies can legitimately share a name.** `GS Medical` is the live
example: GS MEDICAL HEALTHCARE LTD (10425778, Selby) sits inside GBUK, while GS MEDICAL
LIMITED (NI659208, Antrim) is unrelated to it. Those stay AMBIGUOUS forever and must never be
reconciled. Declared ambiguities live in the overlay with their evidence — which means a new,
accidental collision still fails the build, because it has not been declared.

## Adding an alias

1. Confirm it — Companies House, or the company's own site. Not a hunch, not a comparison table.
2. If the company is in the seed, add the variant to its `aliases` list there. Otherwise add
   an entry to `alias-overlay.json` with `canonical`, `variants`, `reason`, `evidence` and
   `addedOn`. The build exits 1 if any of those are missing.
3. `python3 company_alias.py build && python3 company_alias.py selftest`.
4. If you edited the seed, the msh-compare-data publish gate applies — `python3 verify.py`
   must exit 0 before that repo is pushed, because a push to it is a live publish.
