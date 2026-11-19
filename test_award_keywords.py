"""STRONG_KW stems must match the words they start (fixed 12/11/2026)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import refresh_awards as ra  # noqa: E402
import refresh_open_tenders as ro  # noqa: E402

HIT = ["Surgical stapling", "Surgical Staplers and reloads", "Laparoscopic consumables",
       "Endoscopy stack", "Sutures", "Absorbable Suture", "Wound closure",
       "Polymer Ligating Clips", "Clip appliers", "Trocars",
       "Minimally Invasive Surgery Consumables", "Haemostatic agents",
       "Electrosurgical generator", "Orthopaedic implants", "Ventilators",
       "Hernia repair", "Surgical mesh", "Skin closure strips", "Diathermy pencils",
       "Thoracic consumables", "Robotic surgery system", "Robot-assisted surgery",
       "Surgical robotics", "Hemostatic matrix"]
MISS = ["Office staplers", "Ventilation system upgrade", "Stapleford Road resurfacing",
        "Grounds maintenance"]


def test_strong_kw_hits_and_misses():
    for mod in (ra, ro):
        for t in HIT:
            assert mod.STRONG_KW.search(t), (mod.__name__, t)
        for t in MISS:
            assert not mod.STRONG_KW.search(t), (mod.__name__, t)


def test_both_scripts_share_one_rule():
    assert ra.STRONG_KW.pattern == ro.STRONG_KW.pattern


if __name__ == "__main__":
    test_strong_kw_hits_and_misses()
    test_both_scripts_share_one_rule()
    print("test_award_keywords: OK")
