"""One-off: record that every matrix-sourced lot was opened at source and checked
cell by cell (17/11/2026).

WHY. The lots were cited to an NHS Supply Chain product or supplier matrix, but
nobody had opened the spreadsheets — so the standing rule was that a
matrix-sourced lot could not be stated as fact to a prospect. All 17 matrices
cited in data/framework-lots.json were downloaded on 17/11/2026 and every
(supplier, lot) pair the Hub holds from them — 1,133 pairs across 17 frameworks
— was located in the sheet's own cells with openpyxl, by a reader written from
the spreadsheets rather than from scripts/refresh_framework_lots.py, so it could
disagree with the writer. None did: 1,133 of 1,133 confirmed, no lot the Hub
holds absent from its matrix, and no mark in a matrix missing from the Hub.

Worked examples, for anyone re-checking:
  Office Supplies, Product-Matrices-Office-Supplies-1-June-2026-FOS.xlsx,
  sheet 'Product Matrix', header row 13 (lots 1, 2, 3, 4a, 4b, 5, 6a, 6b, 7),
  row 26 'Valley Northern Ltd' marked X in columns C, E, F, H, I = Lots 2, 4a,
  4b, 6a, 6b. Exactly what the Hub holds.
  Surgical Instruments, Product-Matrix-Surgical-Instruments-8-September-2026-MSC.xlsx,
  sheet 'Product Matrix by Lot', row 55 'Valley Northern Limited' marked X in
  column B = 'Lot 1 - Single Use Instruments'. Exactly what the Hub holds.

So the read date on these notes is moved to the date of that check and the
sentence says what was done. Only entries whose lotSourceUrl is a matrix
(.xlsx) are touched; notice-sourced lots were not re-read today and keep their
own date. Idempotent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_format import write_like, describe  # noqa: E402

OLD = "Lot source read 2026-11-15."
NEW = ("Lot source read 2026-11-15; the matrix was opened and this lot confirmed in "
       "its own cells on 2026-11-17.")
PATHS = ["data/supplier-seed.json", "data/supplier-index.json"]


def main():
    for path in PATHS:
        with open(path, "rb") as f:
            doc = json.loads(f.read().decode("utf-8"))
        n = 0
        for sup in doc["suppliers"]:
            for fw in sup.get("frameworks") or []:
                url = str(fw.get("lotSourceUrl") or "")
                note = fw.get("note") or ""
                if url.endswith(".xlsx") and OLD in note:
                    fw["note"] = note.replace(OLD, NEW)
                    n += 1
        if n:
            fmt, round_trips = write_like(path, doc)
            print(describe(path, fmt, round_trips))
        print("%s: stamped %d matrix-sourced lot note(s)" % (path, n))


if __name__ == "__main__":
    main()
