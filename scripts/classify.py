"""Domain classification shared by build.py and run_panel.py.

A cited domain is either a local business's own website or something else
(directory, aggregator, review site, social, reference, lead-gen). The list
below started as the July 2026 study's list (EVOIX, analyze.py) and grows
only by appending; a change here is an analysis change and is logged on the
method page, never applied silently.
"""

import re
from urllib.parse import urlparse

DIRECTORIES = {
    "yelp.com", "expertise.com", "angi.com", "angieslist.com", "thumbtack.com",
    "bbb.org", "houzz.com", "reddit.com", "facebook.com", "instagram.com",
    "google.com", "maps.google.com", "mapquest.com", "yellowpages.com",
    "bestprosintown.com", "threebestrated.com", "avvo.com", "findlaw.com",
    "justia.com", "superlawyers.com", "lawyers.com", "martindale.com",
    "healthgrades.com", "zocdoc.com", "webmd.com", "vitals.com", "ratemds.com",
    "zillow.com", "realtor.com", "homeadvisor.com", "porch.com",
    "buildzoom.com", "nextdoor.com", "wikipedia.org", "quora.com",
    "cladsiding.com", "roofmyspace.com", "provenroofer.com", "birdeye.com",
    "yellowbook.com", "manta.com", "chamberofcommerce.com", "foursquare.com",
    "tripadvisor.com", "linkedin.com", "youtube.com", "homestars.com",
    "trustpilot.com", "clutch.co", "upcity.com", "care.com", "fash.com",
    "lawinfo.com", "nolo.com", "opencorporates.com", "dnb.com",
    "checkbook.org", "wallethub.com", "niche.com", "patch.com",
    # appended 2026-11-02 (seen in run 0 top tables, missed by the July list)
    "experience.com", "lawnstarter.com", "homeguide.com", "trustanalytica.com",
    "bing.com", "apple.com", "tiktok.com", "x.com", "twitter.com",
    # appended 2026-11-02 after run 1 (analysis a4): directories, aggregators, ranking and listicle
    # sites, media, reference, government, associations, manufacturer and insurer finders seen on the
    # four November lanes. delandlocal.com is EVOIX's own DeLand directory and is classed here so it
    # never counts as a business's own site; the method page discloses it.
    "todayshomeowner.com", "usnews.com", "homelight.com", "effectiveagents.com",
    "industryoversight.com", "fastexpert.com", "deltadental.com", "delandlocal.com",
    "healthhives.com", "dentistsranked.com", "yahoo.com", "contractorsranked.com",
    "bestlawyers.com", "ficpa.org", "floridapros.org", "floridaroofingdirectory.com",
    "gaf.com", "consumeraffairs.com", "ratemyagent.com", "rate-my-agent.com", "taxbuzz.com",
    "floridahomenetwork.com", "carrier.com", "ratingsnearme.com", "tebra.com", "homes.com",
    "realestateagents.com", "agentpronto.com", "pests.org", "forbes.com", "ufl.edu",
    "homedepot.com", "daytonachamber.com", "floridabusinessesnear.me", "orlandomagazine.com",
    "clearlyrated.com", "bestpickreports.com", "volusia.org", "myfloridalicense.com",
    "floridabar.org", "opencare.com", "palmer.edu", "healthline.com", "realtrends.com",
    "fdacs.gov", "aisyndicate.com",
}

# Not on the list, but cited for the same template across this many of the 10
# cities in one month (all engines pooled): a regional business, a franchise or
# a business site publishing "best in {city}" listicles. Its own class, never
# folded into "directory".
MULTI_CITY_THRESHOLD = 5

ANALYSIS_VERSION = "a5"  # a1 July 2026 two-class; a2 appended list rows; a3 multi-city class, per-month decision; a4 list appended after run 1; a5 name extraction filters


def norm_domain(url):
    d = urlparse(url).netloc.lower()
    return re.sub(r"^www\.", "", d)


def root(domain):
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def in_directory_list(domain):
    return root(domain) in DIRECTORIES or domain in DIRECTORIES
