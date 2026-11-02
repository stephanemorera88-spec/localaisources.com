"""Regression tests for name extraction (analysis a5). Run: python3 -m unittest scripts/test_extract.py
Each case is a real string the first November 2026 build published as a business name, or a real name it must keep."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

SRC = [{"url": "https://www.totalcomfortfl.com/"}, {"url": "https://mechanicalone.com/ac-repair"}]


def names(md, sources=None):
    return build.extract_names(md, sources)


class DropsJunk(unittest.TestCase):
    def test_address_is_not_a_name(self):
        self.assertEqual(names("**695 McGregor Rd**"), [])
        self.assertEqual(names("**2552 Jasmine Rd, Port Orange, FL 32128**"), [])

    def test_rating_is_not_a_name(self):
        self.assertEqual(names("**9/5 from 305 Google reviews**"), [])
        self.assertEqual(names("**61 Google reviews**"), [])
        self.assertEqual(names("**4.8 stars**"), [])

    def test_advice_heading_is_not_a_name(self):
        for s in ("Verify Licensing & Insurance", "Get Multiple Estimates", "Check Local References",
                  "Ask About Wind Mitigation", "How to Choose the Right Chiropractor for You"):
            self.assertEqual(names(f"**{s}**"), [], s)

    def test_model_thinking_heading_is_not_a_name(self):
        for s in ("Searching for recommendations", "Looking for licensing sources", "Gathering information for reliable answers"):
            self.assertEqual(names(f"**{s}**"), [], s)

    def test_generic_topic_phrase_is_not_a_name(self):
        for s in ("Storm Damage & Insurance", "Insurance Claim Expertise", "Emergency Services"):
            self.assertEqual(names(f"**{s}**"), [], s)

    def test_phone_suffix_is_stripped_not_kept(self):
        self.assertEqual(names("**Del-Air at (386) 387-8075**"), ["Del-Air"])
        self.assertEqual(names("**(386) 492-8418**"), [])


class KeepsRealNames(unittest.TestCase):
    def test_trade_word_keeps_a_plain_phrase(self):
        self.assertEqual(names("**Best Choice Roofing**"), ["Best Choice Roofing"])
        self.assertEqual(names("**Top Notch Roofing Inc**"), ["Top Notch Roofing Inc"])
        self.assertEqual(names("**Comer Roofing**"), ["Comer Roofing"])

    def test_cited_domain_keeps_a_plain_word_name(self):
        self.assertEqual(names("**Total Comfort**", SRC), ["Total Comfort"])
        self.assertEqual(names("**Mechanical One**", SRC), ["Mechanical One"])
        self.assertEqual(names("**Sunshine State**", [{"url": "https://sunshinestateac.com/"}]), ["Sunshine State"])
        self.assertEqual(names("**Sunshine State**", []), [])

    def test_bundled_names_are_split(self):
        self.assertEqual(names("**GRIT Roofing, Pier Roofing, and Heritage Roofing**"),
                         ["GRIT Roofing", "Pier Roofing", "Heritage Roofing"])

    def test_ampersand_name_is_not_split(self):
        self.assertEqual(names("**Beery Roofing & Redesign**"), ["Beery Roofing & Redesign"])
        self.assertEqual(names("**American Air, Plumbing, and Electrical**"), ["American Air, Plumbing, and Electrical"])

    def test_table_body_rows_count_and_header_does_not(self):
        md = "| Company | Rating |\n|---|---|\n| **RDG Roofing** | 4.8 |\n| Gulledge Roofing | 4.9 |"
        self.assertEqual(names(md), ["RDG Roofing", "Gulledge Roofing"])

    def test_dedup_keeps_first_spelling(self):
        self.assertEqual(names("**ROC Roofing** ... **Roc Roofing**"), ["ROC Roofing"])


if __name__ == "__main__":
    unittest.main()
