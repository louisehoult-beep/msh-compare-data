#!/usr/bin/env python3
"""
test_company_press_story_links.py — prove the press writer refuses to publish an
item whose own links do not support the corroboration it claims, and that it
refuses on exactly the evidence verify.py's gate refuses on.

WHY THIS EXISTS (18/09/2026)
  The gate has caught "corroborated by two publishers, but one link carries a
  different story about the same company" since 18/08/2026. The writer did not
  test the same thing, so it kept writing such items out and the whole daily
  sweep failed the gate over one of them — on 18/09/2026 Stryker's cyberattack
  regenerated with one fewer source than the day before and took every other
  supplier's news down with it. The writer now drops the item instead.

  The two tests are deliberately SEPARATE code: a gate that re-ran the writer's
  own logic would have passed the very file that was wrong. This file is what
  holds them to the same answer instead.

  python3 test_company_press_story_links.py     exit 0 = both hold
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

import refresh_company_press as writer      # noqa: E402
import verify                               # noqa: E402

FAILURES = []


def check(label, condition):
    if condition:
        print("ok    %s" % label)
    else:
        print("FAIL  %s" % label)
        FAILURES.append(label)


def src(publisher, url, url_type="publisher"):
    return {"publisher": publisher, "url": url, "urlType": url_type}


# --- the two boilerplate lists must not drift apart ------------------------
# Each list is a set of words its own test can no longer see. If someone adds a
# word to one side only, the writer and the gate stop agreeing about what a URL
# says, and the sweep starts failing again on items the writer thought were fine.
check("the writer's URL boilerplate is the same list the gate uses",
      writer.URL_BOILERPLATE == verify.PRESS_URL_BOILERPLATE)


# --- the live case, 18/09/2026 --------------------------------------------
# Stryker's cyberattack as it regenerated that morning: The Independent carried
# the story but under a slug that says nothing about it, and the one link that
# does corroborate is the only one left. Two publishers, but not two that can be
# shown to be about this story.
STRYKER_HEAD = "US medical equipment company Stryker says cyberattack disrupted its global networks."
STRYKER_NAME_TOKS = {"stryker"}
THIN = [
    src("The Independent", "https://www.independent.co.uk/news/iran-microsoft-b2936713.html"),
    src("Healthcare IT News",
        "https://www.healthcareitnews.com/news/iran-linked-medical-device-cyberattack-contained-says-stryker"),
]
check("the writer drops the 18/09/2026 Stryker item rather than publishing it",
      writer.story_links_unsupported(STRYKER_HEAD, THIN, STRYKER_NAME_TOKS) is not None)

# The same item as it stood on 17/09, when a third outlet was still in the
# results: two links corroborate, so it publishes. The fix must not throw away
# news that IS supported.
FULL = THIN + [
    src("American Hospital Association",
        "https://www.aha.org/news/headline/2026-03-12-medical-technology-company-stryker-disrupted-globally-cyberattack"),
]
check("the writer keeps the same story when two links do corroborate it",
      writer.story_links_unsupported(STRYKER_HEAD, FULL, STRYKER_NAME_TOKS) is None)


# --- the 18/08/2026 defect, at the writer this time ------------------------
ACQ_HEAD = "Smith+Nephew and Imperial College London launch centre for surgical robotics"
ACQ_TOKS = {"smith", "nephew"}
ACQ = [
    src("BioSpace",
        "https://www.biospace.com/press-releases/smith-nephew-imperial-college-london-launch-centre-surgical-robotics"),
    src("MedTech Dive",
        "https://www.medtechdive.com/news/smith-nephew-acquire-integrity-orthopaedics/809570/"),
    src("Reuters",
        "https://www.reuters.com/legal/transactional/smith-nephew-buy-integrity-orthopaedics-450-million/"),
]
check("the writer drops an item corroborated only by a different story about the same company",
      writer.story_links_unsupported(ACQ_HEAD, ACQ, ACQ_TOKS) is not None)


# --- absence of evidence is not evidence -----------------------------------
ID_URLS = [
    src("Korea Biomedical Review", "https://www.koreabiomed.com/news/articleView.html?idxno=27140"),
    src("Healthcare IT News",
        "https://www.healthcareitnews.com/news/iran-linked-medical-device-cyberattack-contained-says-stryker"),
]
check("an ID-style URL is not counted against the item",
      writer.story_links_unsupported(STRYKER_HEAD, ID_URLS, STRYKER_NAME_TOKS) is None)

check("a Google News redirect is not read as the publisher's own slug",
      writer.story_links_unsupported(
          STRYKER_HEAD,
          [src("The Independent", "https://news.google.com/rss/articles/CBMicEFV", "google-news-redirect"),
           src("Healthcare IT News",
               "https://www.healthcareitnews.com/news/iran-linked-medical-device-cyberattack-contained-says-stryker")],
          STRYKER_NAME_TOKS) is None)

check("a headline that is only the company's own name is not judged here",
      writer.story_link_evidence("Stryker", THIN, STRYKER_NAME_TOKS)[0] == 0)


# --- the writer's answer must match the gate's, item for item --------------
# The gate's copy of this test lives inline in verify.check_company_press and is
# reached through a whole published document, so it is exercised by
# test_verify.py. What is pinned here is the READING of the evidence: given the
# same links, the writer must reach the gate's conclusion, not its own.
def gate_reading(headline, sources, name_toks):
    """Re-implement the gate's arithmetic from verify's own constants."""
    import re
    import press_match
    topic = {t for t in press_match.norm(headline).split() if len(t) > 3} - name_toks
    if len(topic) < 2:
        return None
    agree, assessed, disagree = set(), 0, []
    for s in sources:
        if s.get("urlType") != "publisher":
            continue
        path = str(s.get("url") or "").split("//")[-1]
        path = path[path.find("/"):] if "/" in path else ""
        slug = press_match.norm(re.sub(r"[-/_.?=&]", " ", path))
        slug_toks = ({t for t in slug.split() if len(t) > 3}
                     - name_toks - verify.PRESS_URL_BOILERPLATE)
        if len(slug_toks) < 3:
            continue
        assessed += 1
        if topic & slug_toks:
            agree.add(str(s.get("publisher") or "").lower())
        else:
            disagree.append(s.get("publisher"))
    return assessed >= 2 and len(agree) < 2 and bool(disagree)


for label, head, sources, toks in (
        ("the thin Stryker item", STRYKER_HEAD, THIN, STRYKER_NAME_TOKS),
        ("the corroborated Stryker item", STRYKER_HEAD, FULL, STRYKER_NAME_TOKS),
        ("the Smith+Nephew acquisition mix-up", ACQ_HEAD, ACQ, ACQ_TOKS),
        ("an ID-style URL", STRYKER_HEAD, ID_URLS, STRYKER_NAME_TOKS)):
    writer_refuses = writer.story_links_unsupported(head, sources, toks) is not None
    check("writer and gate agree on %s" % label,
          writer_refuses == bool(gate_reading(head, sources, toks)))


print()
if FAILURES:
    print("FAILED — %d case(s): %s" % (len(FAILURES), "; ".join(FAILURES)))
    sys.exit(1)
print("All story-link corroboration cases hold.")
