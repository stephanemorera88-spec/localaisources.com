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

class DropsJunkA6(unittest.TestCase):
    """Strings the 2026-11-02 independent check found on the a5 pages."""
    def test_licence_type_written_in_bold(self):
        self.assertEqual(names("Always request proof of a **Certified Roofing Contractor (CCC)** license before signing."), [])
        self.assertEqual(names("Look for a **Florida CAC license** on the truck."), [])
        self.assertEqual(names("**CCC1332542**"), [])

    def test_review_site_phrases_and_awards(self):
        self.assertEqual(names("**Google Reviews**: 4.8 stars"), [])
        self.assertEqual(names("**A+ BBB rating** and 20 years in business"), [])
        self.assertEqual(names("**9 Google rating**"), [])
        self.assertEqual(names("**Super Service Award** winner three years running"), [])
        self.assertEqual(names("**Zocdoc, Google Reviews, and WebMD**"), [])

    def test_checklist_headings(self):
        self.assertEqual(names("**Confirm Emergency Services**"), [])
        self.assertEqual(names("**Check Property Specialties**"), [])
        self.assertEqual(names("**Emergency vs. Standard Scheduling**"), [])

    def test_numbered_headings_are_list_items(self):
        self.assertEqual(names("### 1. Karen Arbutine (RE/MAX Central Realty)\nShe has 20 years in Lake Mary."), ["Karen Arbutine (RE/MAX Central Realty)"])
        self.assertEqual(names("## 2) Jenny Wemert & Wemert Group Realty"), ["Jenny Wemert & Wemert Group Realty"])
        self.assertEqual(names("### Top Recommendations"), [])

    def test_real_names_with_tricky_words_survive(self):
        self.assertEqual(names("**Certified Roofing Solutions** has served DeLand since 1998."), ["Certified Roofing Solutions"])
        self.assertEqual(names("**Call Dave Plumbing** is family run."), ["Call Dave Plumbing"])
        self.assertEqual(names("**Trust Roofing**"), ["Trust Roofing"])
        self.assertEqual(names("* **Patriot\u2019s Lawn Care:** Licensed and insured local option."), ["Patriot\u2019s Lawn Care"])
        self.assertEqual(names("### 1. Top Regional & Full-Service Firms"), [])

class DropsJunkA6SecondPass(unittest.TestCase):
    """Strings the second independent check (2026-11-02) found on the first a6 build."""
    def test_regulators_associations_and_the_bar(self):
        self.assertEqual(names("**Florida Department of Business and Professional Regulation (DBPR)**"), [])
        self.assertEqual(names("**Florida Institute of CPAs (FICPA)**"), [])
        self.assertEqual(names("**Better Business Bureau (BBB)**"), [])
        self.assertEqual(names("Check **Florida Bar's website** first."), [])

    def test_directory_brands_as_names(self):
        for junk in ("**Realtor.com**", "**Homes.com**", "**Super Lawyers**", "**Martindale-Hubbell**", "**Consumer Affairs**", "**BBB Directory**", "**BBB A+**"):
            self.assertEqual(names(junk), [], junk)

    def test_labels_cities_and_programmes(self):
        for junk in ("**Doctors:**", "**Referrals**", "**Next Steps**", "**For 24/7 Emergencies**", "**Daytona Beach**", "**Deltona, Florida**",
                     "**GAF Master Elite Contractor**", "**Owens Corning Preferred Contractor**", "**Highly Recommended Local Firms (Deltona & West Volusia)**", "**CPA**"):
            self.assertEqual(names(junk), [], junk)

    def test_top_for_headings_keep_the_name(self):
        self.assertEqual(names("### **1. Top for Sports Injuries: Spine Way Chiropractic**"), ["Spine Way Chiropractic"])
        self.assertEqual(names("### 2. Top Overall: Winter Park Chiropractic (Dr. Daniel Filardo)"), ["Winter Park Chiropractic (Dr. Daniel Filardo)"])

    def test_real_names_near_the_new_rules_survive(self):
        self.assertEqual(names("**Next Level Roofing**"), ["Next Level Roofing"])
        self.assertEqual(names("**Daytona Beach Dental Care**"), ["Daytona Beach Dental Care"])
        self.assertEqual(names("**RDG Roofing:** family owned since 1990"), ["RDG Roofing"])
        self.assertEqual(names("**Deltona Family Chiropractic**"), ["Deltona Family Chiropractic"])
        self.assertEqual(names("- **Orkin:** national chain with a Deltona branch"), ["Orkin"])
        self.assertEqual(names("**Withum:** regional CPA firm"), ["Withum"])

    def test_round_three_leftovers(self):
        self.assertEqual(names("**Florida Super Lawyers**"), [])
        self.assertEqual(names("**Avvo, Google, Martindale-Hubbell, and Super Lawyers**"), [])
        self.assertEqual(names("**AV Preeminent**"), [])
        self.assertEqual(names("**My top pick: American Air, Plumbing, and Electrical**"), ["American Air, Plumbing, and Electrical"])



if __name__ == "__main__":
    unittest.main()
