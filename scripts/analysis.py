"""Data and analysis for localaisources.com. Standard library only.

Everything numeric on the site is computed here from data/runs/*.jsonl and data/panel-v1.json.
build.py turns the results into pages; it never computes a figure of its own.

  load_panel(), load_runs(), load_variance()   read the rows
  extract_names(answer, sources)               business names as the engine wrote them (heuristic, a5)
  analyse_run(rows, failed, panel_size)        per-engine stats; adds names, domains and kinds to every row
  group_businesses(per_engine_rows)            one entry per business across engines (same name, spelling aside)
  variance_stats(rows)                         same-day repeat agreement per engine
"""

import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import (ANALYSIS_VERSION, MULTI_CITY_THRESHOLD, in_directory_list,  # noqa: E402
                      norm_domain)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://localaisources.com"
SITE_NAME = "Local AI Sources"
PUBLISHER = "EVOIX LLC"
PUBLISHER_URL = "https://evoix.io/"
AUTHOR_ID = "https://stephanemorera.com/#person"
CONTACT_URL = "https://evoix.io/contact"
STUDY_URL = "https://evoix.io/research/central-florida-ai-citation-study"

ENGINE_NAMES = {"chat_gpt": "ChatGPT", "perplexity": "Perplexity", "claude": "Claude", "gemini": "Gemini"}
ENGINE_ORDER = ["chat_gpt", "perplexity", "claude", "gemini"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
KIND_LABEL = {"own-site": "own site", "directory": "directory", "multi-city": "multi-city site"}

GENERIC = {
    "pros", "cons", "note", "notes", "summary", "services", "why", "rating", "reviews", "best for",
    "location", "phone", "website", "name", "strengths", "key strengths", "contact info", "contact",
    "address", "specialties", "highlights", "overview", "verdict", "bottom line", "top pick",
    "recommendation", "recommendations", "sources", "tip", "tips", "disclaimer", "company", "business",
    "provider", "firm", "practice", "office", "why they stand out", "what they do", "notable", "details",
    "key features", "features", "why it's great", "why it stands out", "specialty", "focus", "area",
    "service area", "google rating", "yelp rating", "price", "pricing", "hours", "experience", "credentials",
    "how to choose", "what to look for", "final thoughts", "conclusion", "in short", "important", "caveat",
    "top choices", "honorable mentions", "other options", "runner-up", "runners-up", "also consider",
    "my recommendation", "my pick", "quick take", "key takeaways", "takeaway", "tl;dr", "tldr",
}


def day(s):
    """'2026-11-02 09:52:28 +00:00' -> '2026-11-02' in America/New_York (the collection runs in Florida). A value with no
    offset, or a machine without tz data, falls back to the first ten characters."""
    if not s:
        return ""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(str(s)).astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return str(s)[:10]


GENERIC_WORDS_PATH = os.path.join(ROOT, "data", "generic-words.txt")
GENERIC_WORDS = {l.strip().lower() for l in open(GENERIC_WORDS_PATH, encoding="utf-8")
                 if l.strip() and not l.startswith("#")} if os.path.exists(GENERIC_WORDS_PATH) else set()

# A business name usually carries a trade or entity word. Phrases without one need another signal (a5).
BIZ_SUFFIX_RE = re.compile(
    r"\b(inc|llc|co|corp|group|services?|roofing|roofers?|roof|plumbing|plumbers?|air|hvac|cooling|heating|"
    r"mechanical|dental|dentistry|orthodontics|smiles?|law|legal|attorneys?|lawyers?|injury|chiropractic|"
    r"chiropractor|wellness|spine|realty|real estate|properties|homes|team|landscaping|landscapes?|lawn|pest|"
    r"termite|exterminators?|cpa|cpas|accounting|tax|advisors?|associates|contractors?|construction|partners|"
    r"center|centre|clinic|care|family|firm|pa|pllc|brothers|bros|sons|company|solutions|enterprises|exteriors|"
    r"restoration|remodeling|electric|comfort|realtors?|agency|office|studio|practice|dds|dmd|md|esq|"
    r"pros|experts|specialists|doctors?|dentists?|orthodontist|ortho|physicians?|medical|health|rooter|"
    r"irrigation|tree|turf|outdoor|property|properties|mortgage|title|insurance agency|accountants?|bookkeeping)\b")
# Advice headings and the model's own thinking headings ("Searching for recommendations") (a5).
ADVICE_START_RE = re.compile(
    r"^(verify|get|check|ask|look|compare|read|call|request|avoid|confirm|consider|make|use|start|research|"
    r"schedule|review|choose|hire|ensure|be|do|don'?t|never|always|know|understand|watch|beware|insist|prioritize|"
    r"focus|gather|obtain|contact|visit|search|expect|keep|trust|remember|prepare|document|inspect|negotiate|"
    r"evaluate|determine|find|narrow|decide|plan|protect|secure|pay|sign|budget|searching|looking|gathering|"
    r"checking|finding|evaluating|comparing|considering|verifying|reviewing|planning|thinking|assessing|"
    r"identifying|investigating|researching|confirming|browsing|determining|compiling|narrowing|focusing|"
    r"weighing|deciding|how|why|what|where|when|who|if|before|after|pro tip|tip|tips|step|note|important|"
    r"disclaimer|red flags?|questions?|things?|factors?|signs?|reasons?)\b")
# Question words and list headings are never a business name, trade word or not ("How to Choose the Right Chiropractor").
HARD_START_RE = re.compile(r"^(how|why|what|where|when|who|which|if|for|next steps?|before|after|pro tip|tips?|steps?|note|important|"
                           r"disclaimer|red flags?|questions?|things?|factors?|signs?|reasons?|ways?|mistakes?)\b")
# A heading made of ordinary words keeps a trade word sometimes ("Emergency Services", "Free Consultations"); these first
# words mark it as a heading when every token is ordinary vocabulary.
HEADING_FIRST_RE = re.compile(r"^(emergency|free|key|local|same-day|residential|commercial|general|patient|client|customer|"
                              r"our|your|their|typical|average|common|overall|specialt(y|ies)|additional|other|more|most|"
                              r"initial|second|multiple)\b")  # not all/certified/reliable/licensed: real names start with those
RATING_RE = re.compile(r"/\s?5\b|\b\d[\d,]*\+?\s+(google\s+|yelp\s+)?reviews?\b|\bstars?\b|\b\d(\.\d)?\s*(star|rating)")
ADDRESS_RE = re.compile(r"^\d{2,6}\s+\S|\bfl\s+\d{5}\b|\b\d+\s+[a-z0-9 .]+\b(rd|st|ave|blvd|dr|hwy|ln|way|suite|ste|unit|pkwy)\b\.?", re.I)
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
# a6: licence types and numbers, awards, review-site phrases, "X vs. Y" headings, imperative check-list headings that
# survived a5 because they carried a trade word ("Confirm Emergency Services"), and phrases made only of directory names.
LICENCE_RE = re.compile(r"\blicen[sc]e[sd]?\b|\blicensing\b|^[A-Z]{2,3}\d{5,}$|\b(ccc|cac|cfc|cgc|cbc|crc|cpc|cmc)\d{4,}\b")
AWARD_RE = re.compile(r"\bawards?\b|\bbadge\b|\bcertification\b|\baccredit(ed|ation)\b")
REVIEW_SITE_RE = re.compile(r"\b(google|yelp|bbb|facebook|angi|houzz|zillow|healthgrades|zocdoc|avvo)\s+(rating|reviews?|profile|listing|score)\b|\ba\+\s+(bbb|rating)\b|\bbbb\b.*\b(a\+|directory|accredited|rating|listing)|^bbb\b|\bbbb$")
VERSUS_RE = re.compile(r"\bvs\.?\b|\bversus\b")
BRAND_PHRASE_RE = re.compile(r"\bsuper lawyers\b|\bmartindale-?hubbell\b|\bav preeminent\b|\bbest lawyers\b|\bavvo\b|\bangi\b|\byelp\b|\bzocdoc\b")
PICK_PREFIX_RE = re.compile(r"^(my |our |the )?(top|best|first|second|third|runner-?up|editor'?s?) ?(pick|choice|overall|rated)?[^:]{0,30}:\s*(.+)$", re.I)
IMPERATIVE_HARD_RE = re.compile(r"^(verify|check|ask|compare|request|avoid|confirm|ensure|schedule|consider|obtain|contact|visit|expect|"
                                r"insist|prioritize|gather|beware|negotiate|evaluate|determine|narrow|decide|always|never|review)\b")
CONTEXT_LICENCE_RE = re.compile(r"^\s*(license|licence|licensing)s?\b", re.I)  # the noun only: "**X** licensed and insured" describes a business
HEADING_ITEM_RE = re.compile(r"^#{1,4}\s*(?:\*\*)?\s*\d{1,2}[.)]\s+(.+?)\s*#*\s*$")
# a6, second pass (found by the independent check of the first a6 build): regulators, associations and the bar; directory
# brands written as names ("Realtor.com", "Super Lawyers"); manufacturer contractor programmes; bare label words; city names.
REGULATOR_RE = re.compile(r"\b(department of|dept\.? of|institute of|board of|bureau|association|society|chamber of commerce|"
                          r"the florida bar|florida bar|state of florida|commission|dbpr|ficpa|epa|fdacs|osha|irs)\b")
PROGRAMME_RE = re.compile(r"\b(master elite|preferred contractor|platinum preferred|authorized dealer|factory authorized|"
                          r"certified contractor|elite contractor|pro network|comfort specialist)\b")
DIRECTORY_BRANDS = {"superlawyers", "martindalehubbell", "martindale", "consumeraffairs", "betterbusinessbureau", "bbb",
                    "googlebusinessprofile", "googlemaps", "angieslist", "homeadvisor", "thumbtack", "nextdoor", "yelp",
                    "zillow", "realtor", "homes", "redfin", "trulia", "avvo", "justia", "findlaw", "nolo", "zocdoc", "healthgrades",
                    "webmd", "vitals", "houzz", "angi", "porch", "buildzoom", "expertise", "threebestrated", "bestprosintown",
                    "yellowpages", "manta", "facebook", "google", "googlereviews", "bing", "apple", "reddit", "quora", "wikipedia"}
LABEL_WORDS = {"doctors", "doctor", "referrals", "referral", "cpa", "cpas", "attorneys", "lawyers", "dentists", "roofers", "plumbers",
               "realtors", "contractors", "agents", "firms", "companies", "providers", "summary", "verdict", "pros", "cons",
               "notes", "note", "tip", "tips", "sources", "overview", "recommendation", "recommendations", "disclaimer"}
HEADING_SKIP_RE = re.compile(r"\b(top|best|other|more|options?|firms?|companies|picks|providers|choices|tier|category)\b", re.I)  # a numbered heading about a group, not a business


def compact(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _panel_cities():
    try:
        panel = json.load(open(os.path.join(ROOT, "data", "panel-v1.json")))
        return {c.lower() for c in panel.get("cities", [])}
    except Exception:
        return set()


PANEL_CITIES = _panel_cities()


def _directory_words():
    from classify import DIRECTORIES
    words = set()
    for d in DIRECTORIES:
        words.add(d.split(".")[0])
    words |= {"google", "reviews", "review", "rating", "ratings", "and", "or", "maps", "search", "profile", "listing"}
    return words


DIRECTORY_WORDS = _directory_words()


def _directory_compact():
    from classify import DIRECTORIES
    return {compact(d) for d in DIRECTORIES} | {compact(d.split(".")[0]) for d in DIRECTORIES}


DIRECTORY_COMPACT = _directory_compact()


def directory_words_only(low):
    """'Zocdoc, Google Reviews, and WebMD' or 'Google Reviews': every token is a directory name or a review word (a6)."""
    toks = re.findall(r"[a-z][a-z'+-]*", low)
    return bool(toks) and all(t in DIRECTORY_WORDS for t in toks)


def valid_name(n, domains_compact=""):
    n = n.strip().strip(":;,.").strip()
    n = re.sub(r"\s+at\s+\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}.*$", "", n).strip()  # "Del-Air at (386) 387-8075"
    if not (3 <= len(n) <= 70):
        return None
    if not re.search(r"[A-Za-z]", n):
        return None
    low = n.lower()
    if low in GENERIC or low.startswith("http") or n.endswith("?"):
        return None
    if len(n.split()) > 9:
        return None
    if re.match(r"^(step|option|tier|category|section)\b", low):
        return None
    if n[:1].islower() or n.startswith("#"):
        return None
    has_suffix = bool(BIZ_SUFFIX_RE.search(low))
    if PHONE_RE.search(n) or ADDRESS_RE.search(n):
        return None
    if RATING_RE.search(low) or LICENCE_RE.search(n) or LICENCE_RE.search(low) or AWARD_RE.search(low) \
            or REVIEW_SITE_RE.search(low) or VERSUS_RE.search(low) or IMPERATIVE_HARD_RE.match(low):
        return None
    if directory_words_only(low) or REGULATOR_RE.search(low) or PROGRAMME_RE.search(low) or BRAND_PHRASE_RE.search(low):
        return None
    ck = compact(n)
    if ck in DIRECTORY_BRANDS or re.sub(r"(com|org|net|co|me|io)$", "", ck) in DIRECTORY_BRANDS or ck in DIRECTORY_COMPACT:
        return None
    if len(n.split()) == 1 and low in LABEL_WORDS:
        return None
    if re.sub(r",?\s*(florida|fl)\.?$", "", low).strip() in PANEL_CITIES:
        return None
    if HARD_START_RE.match(low):
        return None
    if ADVICE_START_RE.match(low) and not has_suffix:
        return None
    toks = re.findall(r"[A-Za-z][A-Za-z'-]+", n)
    all_generic = bool(GENERIC_WORDS and toks and all(t.lower() in GENERIC_WORDS for t in toks))
    in_domains = compact(n) in (domains_compact or "")
    if all_generic and not in_domains and (not has_suffix or HEADING_FIRST_RE.match(low)):
        return None
    if re.search(r"\b(near|options|option|companies|providers|picks|choices|list|guide|rated|reviewed|top|best|recommended|firms)\b", low) \
            and not re.search(r"\b(inc|llc|co|corp|group|services|service|roofing|plumbing|law|dental|clinic|pa|pllc)\b", low):
        return None
    if re.search(r"\(?\b20\d\d\b", n):
        return None
    words = [w for w in re.split(r"\s+", n) if w]
    caps = sum(1 for w in words if w[:1].isupper() or w[:1].isdigit() or w[:1] in "&(")
    if words and caps / len(words) < 0.6:
        return None
    return n


SEP_RE = re.compile(r"^\|?\s*:?-{2,}")


def split_list(n):
    """'GRIT Roofing, Pier Roofing, and Heritage Roofing' -> three names. Only splits a run of three or more
    comma-separated parts that each have two or more words, so 'Beery Roofing & Redesign' stays whole (a5)."""
    if n.count(",") < 2:
        return [n]
    parts = [p.strip() for p in re.split(r",\s*(?:and\s+|&\s+)?|\s+and\s+(?=[A-Z])", n) if p.strip()]
    if len(parts) >= 3 and all(len(p.split()) >= 2 for p in parts):
        return parts
    return [n]


def extract_names(answer, sources=None):
    """Business names as they appear in the answer: bold runs and table body rows (first cell).
    Header rows (the line before a |---| separator) are skipped. Automatic and heuristic;
    labelled as such on every page. `sources` (the row's cited URLs) lets a plain-word name such as
    'Total Comfort' survive when totalcomfortfl.com is among the citations (a5)."""
    domains_compact = "".join(compact(s.get("url", "")) for s in (sources or []))
    found = []
    text = answer or ""
    for m in re.finditer(r"\*\*([^*\n]{3,80})\*\*", text):
        if CONTEXT_LICENCE_RE.match(text[m.end():m.end() + 24]):
            continue  # "**Certified Roofing Contractor (CCC)** license" is a licence type, not a business (a6)
        raw = re.sub(r"^\d+[.)]\s*", "", m.group(1))
        raw = re.sub(r"\[\d+\]", "", raw)
        if raw.strip().endswith(":") and len(raw.split()) == 1 and raw.strip(": ").lower() in LABEL_WORDS | GENERIC_WORDS:
            continue  # "**Doctors:**", "**Pros:**" are labels; "**Orkin:**" is a business (a6)
        pm = PICK_PREFIX_RE.match(raw.strip())
        if pm:
            raw = pm.group(4)  # "My top pick: American Air, Plumbing, and Electrical" keeps the name (a6)
        for part in split_list(raw):
            n = valid_name(part, domains_compact)
            if n:
                found.append(n)
    lines = [l.strip() for l in text.splitlines()]
    for s in lines:
        hm = HEADING_ITEM_RE.match(s)   # "### 1. Karen Arbutine (RE/MAX Central Realty)": a numbered heading is a list item (a6)
        if hm:
            raw = re.sub(r"\*\*", "", hm.group(1)).strip()
            if ":" in raw:
                raw = raw.rsplit(":", 1)[1].strip()   # "Top for Sports Injuries: Spine Way Chiropractic" keeps the name (a6)
            if not raw or HEADING_SKIP_RE.search(raw):
                continue
            raw = re.sub(r"\[\d+\]", "", raw)
            for part in split_list(raw):
                n = valid_name(part, domains_compact)
                if n:
                    found.append(n)
    for i, s in enumerate(lines):
        if not s.startswith("|") or SEP_RE.match(s):
            continue
        if i + 1 < len(lines) and SEP_RE.match(lines[i + 1]):
            continue  # header row
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        c = cells[0]
        c = re.sub(r"\*\*", "", c)
        c = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", c)
        c = re.sub(r"\[\d+\]", "", c)
        c = re.sub(r"^\d+[.)]\s*", "", c)
        for part in split_list(c):
            c2 = valid_name(part, domains_compact)
            if c2:
                found.append(c2)
    out, seen = [], set()
    for n in found:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


def row_cost(r):
    """One spend figure per row: the DataForSEO task charge, which is what the collector caps on.
    Provider spend (money_spent) is the fallback for rows that have no task cost."""
    c = r.get("cost")
    if c is None:
        c = r.get("money_spent")
    return float(c or 0)


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------

def load_panel():
    return json.load(open(os.path.join(ROOT, "data", "panel-v1.json")))


def load_runs():
    """Returns {run_id: {"rows": [...answered rows...], "failed": Counter(engine -> failed calls)}}.
    A prompt that failed once and succeeded on resume is not counted as failed."""
    runs = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "runs", "*.jsonl"))):
        name = os.path.basename(path)[:-6]
        if name.endswith("-variance"):
            continue
        raw = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        rows, seen = [], set()
        for r in raw:
            if r.get("error") or not r.get("answer"):
                continue
            key = (r.get("query_id"), r.get("engine"), r.get("sample", 1))
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
        unknown = {r.get("engine") for r in raw} - set(ENGINE_ORDER)
        if unknown:
            sys.exit(f"{path}: unknown engine key(s) {sorted(unknown)}; expected one of {ENGINE_ORDER}")
        ok_keys = {(r["query_id"], r["engine"]) for r in rows}
        failed = Counter()
        retried = Counter()
        failed_seen = set()
        for r in raw:
            k = (r.get("query_id"), r.get("engine"))
            if r.get("error") or not r.get("answer"):
                if k in ok_keys:
                    retried[r.get("engine")] += 1   # errored, then answered on a later attempt
                elif k not in failed_seen:
                    failed_seen.add(k)
                    failed[r.get("engine")] += 1
        if rows:
            runs[name] = {"rows": rows, "failed": failed, "retried": retried}
    return runs


def load_variance():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "runs", "*-variance.jsonl"))):
        run_id = os.path.basename(path)[:-15]
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        rows = [r for r in rows if not r.get("error") and r.get("answer")]
        if rows:
            out[run_id] = rows
    return out


def analyse_run(rows, failed, panel_size):
    """Per-engine stats plus per-row derived fields (names, domains, kinds). Mutates rows.

    Domain kinds, decided per run across all engines so one domain has one kind per month:
      directory   on the list in classify.py (directories, aggregators, review, social, reference, lead-gen)
      multi-city  not on the list, but cited for the same template across MULTI_CITY_THRESHOLD or more
                  cities this month (a regional business, a franchise, or a listicle-publishing business site)
      own-site    everything else, read as a local business's own website
    """
    by_engine = defaultdict(list)
    cities_per_domain = defaultdict(set)
    for r in rows:
        by_engine[r["engine"]].append(r)
        for s in r.get("sources") or []:
            if s.get("url"):
                cities_per_domain[norm_domain(s["url"])].add(r["city"])

    def kind_of(d):
        if in_directory_list(d):
            return "directory"
        if len(cities_per_domain[d]) >= MULTI_CITY_THRESHOLD:
            return "multi-city"
        return "own-site"

    stats = {}
    for eng in sorted(set(by_engine) | set(failed)):
        recs = by_engine.get(eng, [])
        cited = Counter()
        kinds = {}
        counts = Counter()
        with_sources = named_any = named_total = 0
        for r in recs:
            r["names"] = extract_names(r.get("answer", ""), r.get("sources"))
            doms = []
            for s in r.get("sources") or []:
                if s.get("url"):
                    d = norm_domain(s["url"])
                    if d and d not in doms:
                        doms.append(d)
            r["domains"] = doms
            r["kinds"] = {d: kind_of(d) for d in doms}
            if doms:
                with_sources += 1
            if r["names"]:
                named_any += 1
            named_total += len(r["names"])
            for d in doms:
                kinds[d] = r["kinds"][d]
                cited[d] += 1
                counts[r["kinds"][d]] += 1
        total = sum(counts.values())
        dates = [day(r.get("datetime")) for r in recs if day(r.get("datetime"))]
        stats[eng] = {
            "answers": len(recs),
            "expected": panel_size,
            "failed": failed.get(eng, 0),
            "with_sources": with_sources,
            "named_any": named_any,
            "avg_named": (named_total / len(recs)) if recs else 0,
            "own": counts["own-site"],
            "dirs": counts["directory"],
            "multi": counts["multi-city"],
            "own_share": (counts["own-site"] / total) if total else None,
            "unique_domains": len(cited),
            "top": cited.most_common(25),
            "kinds": kinds,
            "models": sorted({r.get("model_name") or r.get("model_requested") or "?" for r in recs}),
            "cost": sum(row_cost(r) for r in recs),
            "first": min(dates) if dates else "",
            "last": max(dates) if dates else "",
        }
    return stats




# ----------------------------------------------------------------------------
# cross-engine grouping and the noise floor
# ----------------------------------------------------------------------------

ENTITY_WORDS = {"inc", "llc", "co", "corp", "pa", "pl", "pllc", "ltd", "the", "company"}


def business_key(name):
    """Two spellings of one business share a key: case, punctuation, a parenthesised tail and entity suffixes
    (Inc, LLC, P.A.) are ignored. 'Hartsock & Mann, CPA' and 'Hartsock & Mann CPA' merge; 'Dr. John Cervenka'
    and 'John Cervenka' do not (conservative on purpose)."""
    k = re.sub(r"\([^)]*\)", "", name.lower())
    toks = [t for t in re.sub(r"[^a-z0-9]+", " ", k).split() if t not in ENTITY_WORDS]
    return "".join(toks)


def group_businesses(per_engine, engine_order):
    """per_engine: {engine: row} for one question in one month (rows carry 'names').
    Returns [{'name', 'engines': [engine...]}] sorted by engines naming it (most first), then name.
    The displayed spelling is the most frequent one; ties go to the first engine in engine_order."""
    seen = {}
    for e in engine_order:
        r = per_engine.get(e)
        if not r:
            continue
        for n in r.get("names") or []:
            k = business_key(n)
            if not k:
                continue
            b = seen.setdefault(k, {"spellings": Counter(), "engines": [], "first": n})
            b["spellings"][n] += 1
            if e not in b["engines"]:
                b["engines"].append(e)
    out = []
    for b in seen.values():
        top = b["spellings"].most_common()
        best = max(top, key=lambda kv: kv[1])[1]
        name = next(n for n in [b["first"]] + [s for s, _ in top] if b["spellings"][n] == best)
        out.append({"name": name, "engines": b["engines"]})
    out.sort(key=lambda b: (-len(b["engines"]), b["name"].lower()))
    return out


def variance_stats(rows):
    """Agreement across same-day samples per engine: question groups, same first-named business in every
    sample, at least one shared name, at least one shared cited domain. Mutates rows (names, domains)."""
    groups = defaultdict(list)
    for r in rows:
        r["names"] = extract_names(r.get("answer", ""), r.get("sources"))
        r["domains"] = sorted({norm_domain(s["url"]) for s in (r.get("sources") or []) if s.get("url")})
        groups[(r["query_id"], r["engine"])].append(r)
    per_engine = defaultdict(lambda: {"groups": 0, "names_agree": 0, "domains_agree": 0, "top_name_agree": 0})
    for (qid, e), g in groups.items():
        if len(g) < 2:
            continue
        pe = per_engine[e]
        pe["groups"] += 1
        name_sets = [set(n.lower() for n in r["names"]) for r in g]
        dom_sets = [set(r["domains"]) for r in g]
        if all(name_sets) and set.intersection(*name_sets):
            pe["names_agree"] += 1
        if all(dom_sets) and set.intersection(*dom_sets):
            pe["domains_agree"] += 1
        firsts = [r["names"][0].lower() for r in g if r["names"]]
        if len(firsts) == len(g) and len(set(firsts)) == 1:
            pe["top_name_agree"] += 1
    return per_engine
