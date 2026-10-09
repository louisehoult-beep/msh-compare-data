# Company Intelligence render harness

`verify.py` checks the DATA. Nothing checked the RENDERER until 18/08/2026, and on
that day two defects were live at once on the Company Intelligence report: the
company box rendered dark ink on a near-black ground, and every card computed to
`padding: 0` so the text sat hard against the edges. Both were cascade collisions
with the host WordPress page. Neither was a JavaScript error, so nothing failed and
nothing logged. A member found them.

This harness is the check that would have caught both.

## Running it

```
cd tests/company-report
./run.sh                          # app/company-report.js, as committed
./run.sh ../../some-candidate.js  # any candidate build
```

It serves the repo root, drives headless Chrome at a real 1400px viewport, prints
JSON and **exits 1 on any failure**. Data comes from this repo's own `data/`
directory, so what is tested is what would be published; a missing file falls back
to the published raw URL, so it still runs from a bare checkout.

In a browser: `.../tests/company-report/test_company_report.html?src=../../app/company-report.js`,
then read `window.HARNESS_RESULT`.

## Two things that make it a real check rather than a decorative one

**It reproduces the host collision.** The report mounts inside `div.msh` on a page
whose own stylesheet declares `.msh *{margin:0;padding:0;box-sizing:border-box}`.
A bare `.mcr-card` ties that at specificity 0,1,0 and loses on document order,
because the renderer injects its sheet into `<head>` while the page's block sits in
the body. The harness carries that reset, in the body, and self-tests that it wins —
check `harness-reproduces-host-reset`. Without it every style assertion is theatre.

**It declares the breakpoint it measured.** The renderer respaces `.mcr-card` from
`22px 24px` to `16px` under 640px. Some embedded browser panes report
`innerWidth: 0`, which resolves every media query to the narrowest rule — so a run
that does not fix the width tests the phone rule while claiming the desktop one.
That is not hypothetical: during development the padding fault injection PASSED on
the first attempt for exactly this reason. The padding check now also reads the
declaration straight from CSSOM, which is breakpoint-independent.

## Keep it honest

A harness that has never failed is a harness nobody has tested. Before trusting a
change to it, break the renderer on purpose and confirm the right check goes red —
deleting the `padding` from the base `.mcr .mcr-card` rule should fail
`card-padding-nonzero` on every company, and removing a date guard in `alerts()`
should fail `no-shape-mismatch-artefacts` on the companies that have alerts.

It depends on two hooks in the renderer: `MSH_COMPANY_REPORT_DATA` (preload, so it
can run offline) and `MSH_COMPANY_REPORT_BUILD` (the printable pack). If either is
removed the harness says so by name rather than quietly passing.
