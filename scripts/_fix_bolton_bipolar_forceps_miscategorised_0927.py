"""One-off: correct 50 Bolton Surgical Limited product-override entries that
the 20/09/2026 "Policy 5 product-level split" (^o550) filed under
surgical:forceps or surgical:scissor.

Found while working the Electrosurgical Consumables and Related Accessories
framework (coverage batch, 27/09/2026): every one of these 50 names
explicitly says "Bipolar" (a diathermy generator-connector cable or a
diathermy bipolar forceps) -- confirmed against the supplier's own site,
which files every one of them under /product/electrosurgery/reusable/
bipolar/... (boltons.co.uk), never under its plain hand-instrument forceps/
scissors paths. A bipolar instrument only functions plugged into an
electrosurgical generator; it is a different product from the plain,
unpowered surgical:forceps/surgical:scissor Policy 5 filed it as. The
correct type is theatres:electro (Electrosurgery consumables), the type
this framework's own routeNote names explicitly ("...forceps",
data/compare-suppliers.json). Entries mutated in place (hub field only) so
there is one row per product, not a shadowing duplicate; the original
decidedIn/evidence/why are kept and this note explains the change --same
pattern as the file's existing `keyRepointed` field on other entries.

Run once, then delete.
"""
import json

PATH = "data/differentiator-category-map.json"

NOTE = ("Corrected 27/09/2026 (Electrosurgical Consumables coverage batch): "
        "this was filed as %s by the 20/09/2026 Policy 5 product-level "
        "split (^o550), which read the word \"Forceps\"/\"Scissors\" in "
        "the name as the plain surgical-instrument type. The product name "
        "also says \"Bipolar\" -- it is a diathermy item that only "
        "functions on an electrosurgical generator, filed by the "
        "supplier's own site under /product/electrosurgery/reusable/"
        "bipolar/..., not under a hand-instrument path. Retyped to "
        "theatres:electro (Electrosurgery consumables). Not a new "
        "identity/vocabulary ruling -- both types already exist in the "
        "gated vocabulary; this only picks the one the product's own name "
        "and the supplier's own site structure both say is correct.")


def main():
    d = json.load(open(PATH))
    entries = d["entries"]
    fixed = 0
    for e in entries:
        if (e.get("supplier") == "Bolton Surgical Limited"
                and e.get("kind") == "product-override"
                and e.get("hub") in ("surgical:forceps", "surgical:scissor")
                and "bipolar" in e.get("division", "").lower()):
            old_hub = e["hub"]
            e["hub"] = "theatres:electro"
            e["keyRepointed"] = NOTE % old_hub
            fixed += 1
    json.dump(d, open(PATH, "w"), indent=1, ensure_ascii=False)
    print("corrected", fixed, "entries")


if __name__ == "__main__":
    main()
