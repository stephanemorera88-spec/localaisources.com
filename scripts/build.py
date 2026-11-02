#!/usr/bin/env python3
"""Render localaisources.com from data/. Standard library only.

Inputs
  data/panel-v1.json          the frozen prompts
  data/runs/YYYY-MM.jsonl     one row per prompt per engine per month
  data/runs/YYYY-MM-variance.jsonl   optional same-day N=3 subsample

Outputs (repository root, served by GitHub Pages)
  index.html, {city}/{vertical}/, domains/{domain}/, engines/{engine}/,
  runs/{run}/, method/, data/ (+ json, csv), sitemap.xml, llms.txt, 404.html

Every number on every page is computed here from the rows. Nothing is typed in.
"""

import csv
import glob
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

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
TODAY = date.today().isoformat()
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


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def esc(s):
    return html.escape(str(s), quote=True)


def month_label(run_id):
    y, m = run_id.split("-")[:2]
    return f"{MONTHS[int(m) - 1]} {y}"


def article(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def cap(s):
    return s[:1].upper() + s[1:]


def day(s):
    return (s or "")[:10]


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if path.endswith(".html"):
        # every table scrolls sideways on narrow screens instead of widening the page
        content = content.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


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
RATING_RE = re.compile(r"/\s?5\b|\b\d[\d,]*\+?\s+(google\s+|yelp\s+)?reviews?\b|\bstars?\b|\b\d(\.\d)?\s*(star|rating)")
ADDRESS_RE = re.compile(r"^\d{2,6}\s+\S|\bfl\s+\d{5}\b|\b\d+\s+[a-z0-9 .]+\b(rd|st|ave|blvd|dr|hwy|ln|way|suite|ste|unit|pkwy)\b\.?", re.I)
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")


def compact(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


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
    if RATING_RE.search(low):
        return None
    if ADVICE_START_RE.match(low) and not has_suffix:
        return None
    toks = re.findall(r"[A-Za-z][A-Za-z'-]+", n)
    if GENERIC_WORDS and toks and not has_suffix and all(t.lower() in GENERIC_WORDS for t in toks) \
            and compact(n) not in (domains_compact or ""):
        return None
    if re.search(r"\b(near|options|option|companies|providers|picks|choices|list|guide|rated|reviewed|top|best)\b", low) \
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
    for m in re.finditer(r"\*\*([^*\n]{3,80})\*\*", answer or ""):
        raw = re.sub(r"^\d+[.)]\s*", "", m.group(1))
        raw = re.sub(r"\[\d+\]", "", raw)
        for part in split_list(raw):
            n = valid_name(part, domains_compact)
            if n:
                found.append(n)
    lines = [l.strip() for l in (answer or "").splitlines()]
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
        ok_keys = {(r["query_id"], r["engine"]) for r in rows}
        failed = Counter()
        failed_seen = set()
        for r in raw:
            k = (r.get("query_id"), r.get("engine"))
            if (r.get("error") or not r.get("answer")) and k not in ok_keys and k not in failed_seen:
                failed_seen.add(k)
                failed[r.get("engine")] += 1
        if rows:
            runs[name] = {"rows": rows, "failed": failed}
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
    for eng, recs in by_engine.items():
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
# page shell
# ----------------------------------------------------------------------------

CSS = """
:root{--bg:#fbfaf7;--ink:#1c1a19;--muted:#5d5853;--line:#e6e1d8;--accent:#1f4d3a;--own:#1f4d3a;--dir:#8a4b1f;--multi:#4a4f8a;--chip:#efeae0}
*{box-sizing:border-box}html{font-size:17px}
body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-serif,Georgia,"Times New Roman",serif;line-height:1.5}
a{color:var(--accent)}
header.site{border-bottom:1px solid var(--line);padding:14px 16px}
header.site .in{max-width:76rem;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px 22px;align-items:baseline;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.95rem}
header.site .brand{font-weight:700;text-decoration:none;color:var(--ink);font-size:1.05rem}
header.site nav a{text-decoration:none;color:var(--muted)}
main{max-width:76rem;margin:0 auto;padding:28px 16px 60px}
h1{font-size:1.9rem;line-height:1.15;letter-spacing:-.01em;margin:.2em 0 .5em;font-weight:600}
h2{font-size:1.3rem;margin:2em 0 .5em;font-weight:600}
h3{font-size:1.05rem;margin:1.5em 0 .4em;font-weight:600}
p.lede{font-size:1.1rem}
.meta{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.85rem;color:var(--muted)}
table{border-collapse:collapse;width:100%;margin:.6em 0 1.2em;font-size:.95rem}
th,td{text-align:left;padding:.45em .6em;border-bottom:1px solid var(--line);vertical-align:top}
th{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.72rem;padding:.1em .5em;border-radius:3px;background:var(--chip);color:var(--muted);margin-left:.4em;vertical-align:middle;white-space:nowrap}
.chip.own{color:#fff;background:var(--own)}.chip.dir{color:#fff;background:var(--dir)}.chip.multi{color:#fff;background:var(--multi)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:.6em 0 1.2em}.tw table{margin:0;min-width:36rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:6px 18px;font-size:.95rem}
.grid a{text-decoration:none}
.note{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.85rem;color:var(--muted);border-left:3px solid var(--line);padding-left:12px;margin:1em 0}
footer.site{border-top:1px solid var(--line);margin-top:40px;padding:22px 16px;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.85rem;color:var(--muted)}
footer.site .in{max-width:76rem;margin:0 auto}
ul.names{columns:2;column-gap:2rem;padding-left:1.2em;margin:.3em 0 .8em}
@media (max-width:640px){html{font-size:16px}h1{font-size:1.5rem}ul.names{columns:1}table{font-size:.88rem}}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;background:var(--chip);padding:.05em .3em;border-radius:3px}
"""

ENTITY_NODES = [
    {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": SITE_NAME,
     "publisher": {"@id": PUBLISHER_URL + "#organization"}},
    {"@type": "Organization", "@id": PUBLISHER_URL + "#organization", "name": PUBLISHER, "url": PUBLISHER_URL,
     "founder": {"@id": AUTHOR_ID},
     "address": {"@type": "PostalAddress", "addressLocality": "DeLand", "addressRegion": "FL", "addressCountry": "US"}},
    {"@type": "Person", "@id": AUTHOR_ID, "name": "Stephane Morera", "url": "https://stephanemorera.com/",
     "worksFor": {"@id": PUBLISHER_URL + "#organization"},
     "sameAs": ["https://www.linkedin.com/in/stephanemorera", "https://lounge.ai/@stephanemorera", "https://kingofaeo.io/"]},
]


def shell(title, desc, path, body, lastmod, ld=None, og_type="website"):
    url = SITE + path
    graph = [{
        "@type": "WebPage", "@id": url + "#webpage", "url": url, "name": title, "description": desc,
        "inLanguage": "en", "dateModified": lastmod,
        "isPartOf": {"@id": SITE + "/#website"},
        "author": {"@id": AUTHOR_ID}, "publisher": {"@id": PUBLISHER_URL + "#organization"},
    }] + ENTITY_NODES
    if ld:
        graph.extend(ld)
    ld_block = '<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False) + "</script>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#fbfaf7">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:site" content="@Stephane_Morera">
<link rel="stylesheet" href="/assets/style.css">
{ld_block}
</head>
<body>
<header class="site"><div class="in">
<a class="brand" href="/">{SITE_NAME}</a>
<nav><a href="/engines/">Engines</a> &nbsp; <a href="/domains/">Sources</a> &nbsp; <a href="/runs/">Months</a> &nbsp; <a href="/method/">Method</a> &nbsp; <a href="/data/">Data</a></nav>
</div></header>
<main>
{body}
</main>
<footer class="site"><div class="in">
<p>{SITE_NAME} is published by <a href="{PUBLISHER_URL}">{PUBLISHER}</a> in DeLand, Florida. It is written by <a href="https://stephanemorera.com/">Stephane Morera</a>. Data under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, code under MIT, both on <a href="https://github.com/stephanemorera88-spec/localaisources.com">GitHub</a>. Engine answers are recorded as returned and are not EVOIX recommendations. Extraction errors can be reported through the <a href="{CONTACT_URL}">EVOIX contact page</a>.</p>
<p>Page data as of {esc(lastmod)}. Analysis version {ANALYSIS_VERSION}.</p>
</div></footer>
</body>
</html>
"""


def kind_chip(k):
    cls = {"own-site": "own", "directory": "dir", "multi-city": "multi"}.get(k, "")
    return f'<span class="chip {cls}">{KIND_LABEL.get(k, "unclassified")}</span>'


def pct(x):
    return "n/a" if x is None else f"{round(x * 100)}%"


def answers_cell(s):
    if s["failed"]:
        return f"{s['answers']} of {s['expected']} ({s['failed']} calls failed)"
    return f"{s['answers']} of {s['expected']}"


def top_cell(s):
    if not s["top"]:
        return "none cited"
    d, n = s["top"][0]
    return f"<a href=\"/domains/{slug(d)}/\">{esc(d)}</a> {kind_chip(s['kinds'].get(d))}<div class=\"meta\">cited in {n} of {s['answers']} answers</div>"


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------

def build(panel, runs, variance):
    run_ids = sorted(runs)
    latest = run_ids[-1]
    panel_size = len(panel["prompts"])
    analysed = {rid: analyse_run(runs[rid]["rows"], runs[rid]["failed"], panel_size) for rid in run_ids}
    run_date = {rid: min((analysed[rid][e]["first"] or TODAY) for e in analysed[rid]) for rid in run_ids}
    by_q = defaultdict(lambda: defaultdict(dict))   # query_id -> run -> engine -> row
    for rid in run_ids:
        for r in runs[rid]["rows"]:
            by_q[r["query_id"]][rid][r["engine"]] = r
    all_engines = [e for e in ENGINE_ORDER if any(e in analysed[rid] for rid in run_ids)]
    pages = []   # (path, lastmod)

    def engines_in(rid):
        return [e for e in ENGINE_ORDER if e in analysed[rid]]

    engines_latest = engines_in(latest)
    latest_date = run_date[latest]

    # ---- home
    st = analysed[latest]
    rows_html = "".join(
        f"<tr><td><a href=\"/engines/{e}/\">{ENGINE_NAMES[e]}</a><div class=\"meta\">{esc(', '.join(st[e]['models']))}</div></td>"
        f"<td class=\"num\">{st[e]['named_any']} of {st[e]['answers']}</td>"
        f"<td class=\"num\">{pct(st[e]['own_share'])}</td>"
        f"<td>{top_cell(st[e])}</td></tr>" for e in engines_latest)
    failed_total = sum(st[e]["failed"] for e in engines_latest)
    failed_note = (f" {failed_total} of {panel_size * len(engines_latest)} calls returned no answer this month and are counted as missing, not as answers; the per-engine detail is on the <a href=\"/runs/{latest}/\">run page</a>."
                   if failed_total else "")
    grid = ""
    for v in panel["verticals"]:
        grid += f"<h3>{esc(cap(v))}</h3><div class=\"grid\">"
        for c in panel["cities"]:
            grid += f"<a href=\"/{slug(c)}/{slug(v)}/\">{esc(c)}</a>"
        grid += "</div>"
    n_eng = len(engines_latest)
    home_desc = (f"A public monthly record of which businesses and which sources {n_eng} AI engines cite when asked who the best "
                 f"roofer, plumber, dentist and seven other local providers are in 10 Central Florida cities. {month_label(latest)} edition.")
    body = f"""
<p class="meta">Panel v1 · {panel_size} fixed questions · {n_eng} engines · updated monthly · latest run {month_label(latest)}, collected {esc(latest_date)}</p>
<h1>Which businesses do AI engines recommend in Central Florida, and which sources do they cite?</h1>
<p class="lede">Every month we ask {n_eng} AI engines the same {panel_size} questions, "Who is the best {{vertical}} in {{city}}, Florida?", for {len(panel['verticals'])} service verticals across {len(panel['cities'])} Central Florida cities, with live web search on. We record every business named and every source cited, and publish all of it here, right or wrong. This is the {month_label(latest)} edition.</p>
<h2>{month_label(latest)} at a glance</h2>
<table>
<tr><th>Engine</th><th class="num">Answers naming at least one business</th><th class="num">Own-site share of citations</th><th>Most cited source</th></tr>
{rows_html}
</table>
<p class="note">Each cell is one answer per question per engine in this month's run (N=1 per question), so a single question's result is provisional. The aggregate rows above are the index figures. The same-day repeat subsample on the <a href="/method/">method page</a> is the measured noise floor. "Own-site share" counts each cited domain once per answer and sums across the 100 answers; it is the share of those domain citations that read as a local business's own website, as opposed to a directory, aggregator, review or social site, or a multi-city business site (analysis {ANALYSIS_VERSION}).{failed_note}</p>
<h2>Browse by vertical and city</h2>
{grid}
<h2>Why this exists</h2>
<p>Business owners ask whether AI recommends them. Agencies guess at how AI picks sources. The global indexes that exist, Promvia's AI Source Index, BrandInsightAI's GEO Index and HeyAmos's AI Sources Index among them, answer at the level of "best CRM" and report domains worldwide. None of them asks about a roofer in DeLand or names the businesses. This one does, every month, on a fixed panel, so the record can be compared over time and reproduced by anyone with the prompt list and the method.</p>
<p>It began as EVOIX's <a href="{STUDY_URL}">Central Florida AI Citation Study</a>, collected 2 July 2026. That run is month zero here and the panel has not changed since.</p>
<h2>Read next</h2>
<ul>
<li><a href="/runs/{latest}/">The full {month_label(latest)} run</a>, every engine, every top source</li>
<li><a href="/domains/">Every source domain cited</a>, with how often and where</li>
<li><a href="/method/">Method, instrument and changelog</a></li>
<li><a href="/data/">Download the rows</a> (CC BY 4.0)</li>
</ul>
"""
    write("index.html", shell(f"{SITE_NAME}: which businesses AI engines recommend in Central Florida, {month_label(latest)}",
                              home_desc, "/", body, latest_date))
    pages.append(("/", latest_date))

    # ---- panel pages
    for p in panel["prompts"]:
        qid, v, c = p["query_id"], p["vertical"], p["city"]
        path = f"/{slug(c)}/{slug(v)}/"
        sections = ""
        page_date = ""
        for rid in reversed(run_ids):
            per = by_q[qid].get(rid, {})
            if not per:
                continue
            engs = [e for e in ENGINE_ORDER if e in per]
            collected = max(day(per[e].get("datetime")) for e in engs) or run_date[rid]
            page_date = page_date or collected
            named_engines = sum(1 for e in engs if per[e].get("names"))
            missing = [e for e in engines_in(rid) if e not in per]
            sections += f"<h2>{month_label(rid)}</h2><p class=\"meta\">Collected {esc(collected)} · N=1 per engine · provisional at the question level</p>"
            sections += f"<p>{named_engines} of {len(engs)} engines named at least one specific business."
            if missing:
                sections += f" No answer was returned by {', '.join(ENGINE_NAMES[e] for e in missing)} this month."
            sections += "</p>"
            for e in engs:
                r = per[e]
                names = r.get("names") or []
                doms = r.get("domains") or []
                sections += f"<h3>{ENGINE_NAMES[e]} <span class=\"chip\">{esc(r.get('model_name') or r.get('model_requested') or '')}</span></h3>"
                if names:
                    sections += "<p class=\"meta\">Businesses named in the answer, as written by the engine</p><ul class=\"names\">" + "".join(f"<li>{esc(n)}</li>" for n in names) + "</ul>"
                else:
                    sections += "<p class=\"meta\">No business name was extracted from this answer.</p>"
                if doms:
                    sections += "<p class=\"meta\">Sources cited</p><p>" + " · ".join(
                        f"<a href=\"/domains/{slug(d)}/\">{esc(d)}</a>{kind_chip(r['kinds'].get(d))}" for d in doms) + "</p>"
                else:
                    sections += "<p class=\"meta\">No sources were returned with this answer.</p>"
        latest_per = by_q[qid].get(latest, {})
        engs_l = [e for e in ENGINE_ORDER if e in latest_per]
        k = sum(1 for e in engs_l if latest_per[e].get("names"))
        own_cnt = sum(1 for e in engs_l for d in latest_per[e].get("domains", []) if latest_per[e]["kinds"].get(d) == "own-site")
        dir_cnt = sum(1 for e in engs_l for d in latest_per[e].get("domains", []) if latest_per[e]["kinds"].get(d) == "directory")
        title = f"Who do AI engines recommend for {article(v)} {v} in {c}, Florida? ({month_label(latest)})"
        desc = (f"In {month_label(latest)}, {k} of {len(engs_l)} AI engines named at least one specific {v} for {c}, Florida, "
                f"and together they cited {own_cnt} business websites and {dir_cnt} directories. Names and sources, recorded as returned.")
        first = (f"<p class=\"lede\">In {month_label(latest)}, {k} of {len(engs_l)} AI engines named at least one specific {esc(v)} for {esc(c)}, Florida, "
                 f"when asked \"{esc(p['prompt'])}\". Together they cited {own_cnt} business websites and {dir_cnt} directory or aggregator pages. "
                 f"The names and the sources each engine returned are below, by month.</p>")
        body = f"<p class=\"meta\"><a href=\"/\">{SITE_NAME}</a> · {esc(c)} · {esc(v)}</p><h1>{esc(title)}</h1>{first}{sections}"
        body += ("<p class=\"note\">Names are extracted automatically from each answer's bold text and tables, so a name can be missed or cut oddly; "
                 "the full answer text is in the <a href=\"/data/\">downloadable rows</a>. A business listed here was named by that engine on that date. "
                 "It is not an EVOIX recommendation, and absence from this page is not a judgement of any business.</p>")
        write(path.strip("/") + "/index.html", shell(title, desc, path, body, page_date or latest_date, og_type="article"))
        pages.append((path, page_date or latest_date))

    # ---- domain pages + index
    dom_rows = defaultdict(list)   # domain -> list of (rid, engine, qid, vertical, city, kind)
    for rid in run_ids:
        for r in runs[rid]["rows"]:
            for d in r.get("domains", []):
                dom_rows[d].append((rid, r["engine"], r["query_id"], r["vertical"], r["city"], r["kinds"].get(d)))
    dom_index = ""
    for d, lst in sorted(dom_rows.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        kind_by_run = {}
        for rid, e, qid, v, c, k in lst:
            kind_by_run[rid] = k
        latest_kind = kind_by_run[max(kind_by_run)]
        path = f"/domains/{slug(d)}/"
        by_run = defaultdict(Counter)
        for rid, e, *_ in lst:
            by_run[rid][e] += 1
        tbl = "<table><tr><th>Month</th><th>Classified as</th>" + "".join(f"<th class=\"num\">{ENGINE_NAMES[e]}</th>" for e in all_engines) + "</tr>"
        for rid in reversed(run_ids):
            if rid not in by_run:
                continue
            tbl += (f"<tr><td><a href=\"/runs/{rid}/\">{month_label(rid)}</a></td><td>{kind_chip(kind_by_run[rid])}</td>"
                    + "".join(f"<td class=\"num\">{by_run[rid].get(e, 0) if e in analysed[rid] else 'not run'}</td>" for e in all_engines) + "</tr>")
        tbl += "</table>"
        qlist = defaultdict(list)
        for rid, e, qid, v, c, _k in lst:
            qlist[(v, c)].append((rid, e))
        ql = "<ul>" + "".join(
            f"<li><a href=\"/{slug(c)}/{slug(v)}/\">{esc(v)} in {esc(c)}</a> <span class=\"meta\">({', '.join(sorted({ENGINE_NAMES[e] for _, e in ents}))})</span></li>"
            for (v, c), ents in sorted(qlist.items())) + "</ul>"
        dom_date = max(run_date[rid] for rid in kind_by_run)
        title = f"{d}: how often AI engines cite it for Central Florida local-service questions"
        desc = f"{d} was cited in {len(lst)} answers across {len(kind_by_run)} monthly run(s) of the Local AI Sources panel. Classified as {KIND_LABEL[latest_kind]} in the latest month."
        body = (f"<p class=\"meta\"><a href=\"/\">{SITE_NAME}</a> · <a href=\"/domains/\">Sources</a></p><h1>{esc(d)} {kind_chip(latest_kind)}</h1>"
                f"<p class=\"lede\">{esc(d)} was cited in {len(lst)} answers across {len(kind_by_run)} monthly run(s). Classification is decided per month from that month's rows (analysis {ANALYSIS_VERSION}); the latest month reads {KIND_LABEL[latest_kind]}.</p>"
                f"<h2>Answers citing it, by month and engine</h2>{tbl}<h2>Questions it was cited on</h2>{ql}")
        write(path.strip("/") + "/index.html", shell(title, desc, path, body, dom_date))
        pages.append((path, dom_date))
        dom_index += f"<tr><td><a href=\"{path}\">{esc(d)}</a> {kind_chip(latest_kind)}</td><td class=\"num\">{len(lst)}</td></tr>"
    body = (f"<h1>Every source domain cited on the panel</h1><p class=\"lede\">{len(dom_rows)} distinct domains across {len(run_ids)} monthly run(s). "
            f"Count is the number of answers citing the domain, all engines and months combined. The chip is the latest month's classification.</p><table><tr><th>Domain</th><th class=\"num\">Answers</th></tr>{dom_index}</table>")
    write("domains/index.html", shell("Sources cited by AI engines for Central Florida local-service questions",
                                      f"{len(dom_rows)} distinct domains cited across the Local AI Sources panel, with counts.", "/domains/", body, latest_date))
    pages.append(("/domains/", latest_date))

    # ---- engine pages + index
    eng_index = ""
    for e in all_engines:
        path = f"/engines/{e}/"
        sec = ""
        for rid in reversed(run_ids):
            if e not in analysed[rid]:
                continue
            s = analysed[rid][e]
            top = "".join(f"<tr><td><a href=\"/domains/{slug(d)}/\">{esc(d)}</a> {kind_chip(s['kinds'].get(d))}</td><td class=\"num\">{n}</td></tr>" for d, n in s["top"][:20]) or "<tr><td colspan=\"2\">none cited</td></tr>"
            sec += (f"<h2>{month_label(rid)} <span class=\"chip\">{esc(', '.join(s['models']))}</span></h2>"
                    f"<table><tr><th>Answers returned</th><th class=\"num\">Naming a business</th><th class=\"num\">With sources</th><th class=\"num\">Own-site share</th><th class=\"num\">Unique domains</th><th class=\"num\">Names per answer</th></tr>"
                    f"<tr><td>{answers_cell(s)}</td><td class=\"num\">{s['named_any']}</td><td class=\"num\">{s['with_sources']}</td><td class=\"num\">{pct(s['own_share'])}</td><td class=\"num\">{s['unique_domains']}</td><td class=\"num\">{s['avg_named']:.1f}</td></tr></table>"
                    f"<h3>Most cited domains</h3><table><tr><th>Domain</th><th class=\"num\">Answers citing it</th></tr>{top}</table>")
        s = analysed[latest].get(e)
        eng_date = max(run_date[rid] for rid in run_ids if e in analysed[rid])
        title = f"What {ENGINE_NAMES[e]} cites for Central Florida local-service questions"
        desc = (f"{ENGINE_NAMES[e]} on the Local AI Sources panel: how often it names a business, its own-site share and its most cited domains, by month."
                if not s else f"In {month_label(latest)}, {ENGINE_NAMES[e]} named a business in {s['named_any']} of {s['answers']} answers with an own-site citation share of {pct(s['own_share'])}. Most cited domains by month.")
        body = f"<p class=\"meta\"><a href=\"/\">{SITE_NAME}</a> · <a href=\"/engines/\">Engines</a></p><h1>{esc(title)}</h1>{sec}"
        write(path.strip("/") + "/index.html", shell(title, desc, path, body, eng_date))
        pages.append((path, eng_date))
        eng_index += f"<li><a href=\"{path}\">{ENGINE_NAMES[e]}</a></li>"
    write("engines/index.html", shell("Engines on the Local AI Sources panel", "Per-engine pages: ChatGPT, Perplexity, Claude and Gemini on 100 Central Florida local-service questions.", "/engines/",
                                      f"<h1>Engines</h1><ul>{eng_index}</ul>", latest_date))
    pages.append(("/engines/", latest_date))

    # ---- run pages + index
    run_index = ""
    for rid in reversed(run_ids):
        path = f"/runs/{rid}/"
        st = analysed[rid]
        engs = engines_in(rid)
        cost = sum(st[e]["cost"] for e in engs)
        n_answers = sum(st[e]["answers"] for e in engs)
        n_failed = sum(st[e]["failed"] for e in engs)
        tbl = "<table><tr><th>Engine</th><th>Model</th><th>Answers returned</th><th class=\"num\">Naming a business</th><th class=\"num\">Own-site share</th><th class=\"num\">Multi-city sites</th><th class=\"num\">Unique domains</th><th>Top domain</th></tr>"
        for e in engs:
            s = st[e]
            tbl += (f"<tr><td><a href=\"/engines/{e}/\">{ENGINE_NAMES[e]}</a></td><td>{esc(', '.join(s['models']))}</td><td>{answers_cell(s)}</td>"
                    f"<td class=\"num\">{s['named_any']}</td><td class=\"num\">{pct(s['own_share'])}</td><td class=\"num\">{s['multi']}</td><td class=\"num\">{s['unique_domains']}</td>"
                    f"<td>{top_cell(s)}</td></tr>")
        tbl += "</table>"
        tops = ""
        for e in engs:
            s = st[e]
            tops += f"<h3>{ENGINE_NAMES[e]}</h3><table><tr><th>Domain</th><th class=\"num\">Answers citing it</th></tr>" + ("".join(
                f"<tr><td><a href=\"/domains/{slug(d)}/\">{esc(d)}</a> {kind_chip(s['kinds'].get(d))}</td><td class=\"num\">{n}</td></tr>" for d, n in s["top"][:15]) or "<tr><td colspan=\"2\">none cited</td></tr>") + "</table>"
        var = variance.get(rid)
        var_html = ("<h2>Same-day repeat subsample</h2>" + variance_agreement(var)) if var else ""
        collected = run_date[rid]
        failed_txt = f" {n_failed} call(s) returned no answer and are excluded from every figure on this page." if n_failed else ""
        title = f"{month_label(rid)} run: what {len(engs)} AI engines cited for 100 Central Florida local-service questions"
        desc = f"Local AI Sources {month_label(rid)}: {len(engs)} engines, {n_answers} answers, collected {collected}. Per-engine naming rate, own-site share and most cited domains."
        body = (f"<p class=\"meta\"><a href=\"/\">{SITE_NAME}</a> · <a href=\"/runs/\">Months</a></p><h1>{esc(title)}</h1>"
                f"<p class=\"lede\">Collected {esc(collected)}. {n_answers} answers returned of {panel_size * len(engs)} calls, one per question per engine.{failed_txt} Recorded API charge ${cost:.2f}.</p>"
                f"{tbl}<h2>Most cited domains by engine</h2>{tops}{var_html}"
                f"<p><a href=\"/data/{rid}.csv\">Download this month as CSV</a> · <a href=\"/data/{rid}.json\">JSON with full answers</a></p>")
        write(path.strip("/") + "/index.html", shell(title, desc, path, body, collected, og_type="article"))
        pages.append((path, collected))
        run_index += f"<li><a href=\"{path}\">{month_label(rid)}</a> <span class=\"meta\">{len(engs)} engines, collected {esc(collected)}</span></li>"
    write("runs/index.html", shell("Monthly runs of the Local AI Sources panel", "Every monthly run, newest first.", "/runs/", f"<h1>Months</h1><ul>{run_index}</ul>", latest_date))
    pages.append(("/runs/", latest_date))

    # ---- data files
    for rid in run_ids:
        rows = runs[rid]["rows"]
        json.dump([{k: r.get(k) for k in ("run_id", "panel_version", "query_id", "vertical", "city", "prompt", "engine",
                                            "model_requested", "model_name", "datetime", "answer", "sources", "names", "domains", "kinds", "cost", "money_spent")} for r in rows],
                  open(os.path.join(ROOT, "data", f"{rid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        with open(os.path.join(ROOT, "data", f"{rid}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["run_id", "panel_version", "query_id", "vertical", "city", "engine", "model_name", "datetime",
                        "names_extracted", "domains_cited", "own_site_count", "directory_count", "multi_city_count"])
            for r in rows:
                kc = Counter(r["kinds"].get(d) for d in r.get("domains", []))
                w.writerow([r.get("run_id"), r.get("panel_version"), r["query_id"], r["vertical"], r["city"], r["engine"],
                            r.get("model_name") or r.get("model_requested"), r.get("datetime"),
                            "|".join(r.get("names", [])), "|".join(r.get("domains", [])), kc["own-site"], kc["directory"], kc["multi-city"]])
    ds = [{
        "@type": "Dataset", "@id": SITE + "/data/#dataset", "name": "Local AI Sources panel v1",
        "description": "Monthly record of the businesses named and the source URLs cited by AI engines when asked who the best local provider is, for 10 service verticals in 10 Central Florida cities. One row per question per engine per month, with the full answer text.",
        "url": SITE + "/data/", "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@id": PUBLISHER_URL + "#organization"}, "author": {"@id": AUTHOR_ID},
        "temporalCoverage": f"{run_ids[0]}/{run_ids[-1]}", "spatialCoverage": "Central Florida, United States",
        "keywords": ["AI visibility", "AI citations", "answer engine optimization", "local SEO", "ChatGPT", "Perplexity", "Claude", "Gemini"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE}/data/{rid}.json"} for rid in run_ids]
                        + [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{SITE}/data/{rid}.csv"} for rid in run_ids],
    }]
    dl = "".join(f"<li>{month_label(rid)}: <a href=\"/data/{rid}.json\">JSON (full answers)</a> · <a href=\"/data/{rid}.csv\">CSV (names and domains)</a></li>" for rid in reversed(run_ids))
    body = (f"<h1>Download the rows</h1><p class=\"lede\">One row per question per engine per month. The JSON carries the full answer text and every cited URL with its title; the CSV carries the extracted names, the cited domains and the own-site, directory and multi-city counts.</p>"
            f"<ul>{dl}<li><a href=\"/data/panel-v1.json\">Panel v1</a>, the 100 prompts</li></ul>"
            f"<p>License <a href=\"https://creativecommons.org/licenses/by/4.0/\">CC BY 4.0</a>. Attribution: \"Local AI Sources by EVOIX LLC, localaisources.com\". The answer text is engine output reproduced for research and comparison; it is not written by EVOIX and may contain errors about the businesses it names.</p>")
    write("data/index.html", shell("Local AI Sources data downloads", "Monthly rows of AI engine answers and citations for Central Florida local-service questions, CC BY 4.0.", "/data/", body, latest_date, ld=ds))
    pages.append(("/data/", latest_date))

    # ---- method
    instr = "<table><tr><th>Month</th>" + "".join(f"<th>{ENGINE_NAMES[e]}</th>" for e in all_engines) + "<th class=\"num\">Calls failed</th><th class=\"num\">Charge</th></tr>"
    for rid in reversed(run_ids):
        instr += (f"<tr><td>{month_label(rid)}</td>" + "".join(
            f"<td>{esc(', '.join(analysed[rid][e]['models'])) if e in analysed[rid] else 'not run'}</td>" for e in all_engines)
            + f"<td class=\"num\">{sum(analysed[rid][e]['failed'] for e in engines_in(rid))}</td>"
            + f"<td class=\"num\">${sum(analysed[rid][e]['cost'] for e in engines_in(rid)):.2f}</td></tr>")
    instr += "</table>"
    var_sections = "".join(f"<h3>{month_label(rid)}</h3>{variance_agreement(v)}" for rid, v in sorted(variance.items(), reverse=True)) or "<p>No repeat subsample has been run yet. The first one is scheduled with the first monthly run after July 2026.</p>"
    prompts_html = "<ol>" + "".join(f"<li>{esc(p['prompt'])}</li>" for p in panel["prompts"]) + "</ol>"
    body = f"""
<h1>Method, instrument and changelog</h1>
<p class="lede">The index is a fixed panel of {panel_size} questions put to the same AI engines once a month through their search-grounded APIs. Every answer and every cited URL is stored and published. Nothing on the site is typed in; every page is generated from the rows.</p>
<h2>Panel v1</h2>
<p>Template <code>{esc(panel['template'])}</code>, frozen {esc(panel['frozen'])}. {len(panel['verticals'])} verticals ({esc(', '.join(panel['verticals']))}) by {len(panel['cities'])} cities ({esc(', '.join(panel['cities']))}). A prompt is never edited. If the panel changes it gets a new version number and the old one stays comparable with itself.</p>
<h2>Instrument</h2>
<p>DataForSEO <code>ai_optimization/{{engine}}/llm_responses/live</code> with <code>web_search: true</code>, United States, English, no location override, no logged-in state. The model is part of the instrument: a month asked with a different model is a different instrument and is compared to earlier months as directional only. Movers are reported only between months with the same instrument. "Charge" is the DataForSEO task charge recorded per call, the figure the collector caps on.</p>
{instr}
<p>July 2026 was collected for EVOIX's <a href="{STUDY_URL}">Central Florida AI Citation Study</a> on ChatGPT <code>gpt-5.3-chat-latest</code> and Perplexity <code>sonar</code>. From November 2026 the panel runs on four engines with pinned models (ChatGPT <code>gpt-5.4-2026-03-05</code>, Perplexity <code>sonar-pro</code>, Claude <code>claude-sonnet-5</code>, Gemini <code>gemini-3.6-flash</code>), so the ChatGPT and Perplexity lanes changed instrument between month zero and month one. The model shown on every page is the one the API reported serving, not the one requested: in November 2026 the collector asked for <code>gemini-3.5-flash</code> and DataForSEO served <code>gemini-3.6-flash</code> on all 100 rows, so the Gemini lane is pinned to the served name from December.</p>
<p>Gemini returns every citation as a <code>vertexaisearch.cloud.google.com</code> redirect link. The collector follows each link once and stores the real URL; the redirect link is kept in the row as <code>redirect_url</code>. The handful that fail to resolve fall back to the domain in the citation title and are flagged in the row.</p>
<h2>What is counted</h2>
<ul>
<li><strong>Answers returned.</strong> A call that errors or returns no text is a failed call. It is counted and shown, and excluded from every rate, so "80 of 88" means 88 answers came back out of 100 calls.</li>
<li><strong>Naming a business.</strong> An answer counts if at least one business name is extracted from its bold text or its table body rows (table headers are skipped). Since analysis a5 the extractor drops advice headings ("Get Multiple Estimates"), the model's own working headings ("Searching for recommendations"), ratings, addresses and phone lines, splits a bold run of three or more names into separate names, and treats a phrase made only of ordinary English words as a heading unless it carries a trade word (Roofing, Dental, Law, CPA and the like) or matches one of the answer's cited domains. The extraction is automatic and conservative; it can miss a name written in plain prose. It never invents one.</li>
<li><strong>Source classes.</strong> Each cited domain is one of three things in a given month. <em>Directory</em>: on the published list in <code>scripts/classify.py</code> (directories, aggregators, review, social, reference and lead-gen sites). <em>Multi-city site</em>: not on the list, but cited for the same template across {MULTI_CITY_THRESHOLD} or more of the 10 cities that month, which catches regional businesses, franchises and business sites that publish "best in {{city}}" listicles. <em>Own site</em>: everything else, read as a local business's own website. The class is decided per month across all engines, so a domain has one class per month and can change class between months; the domain pages show the class for every month. Disclosure: <code>delandlocal.com</code> is a DeLand business directory published by EVOIX, the publisher of this index. It is on the directory list, so a citation of it never counts as a business's own site, and it appears in the tables like any other directory.</li>
<li><strong>Own-site share.</strong> Each answer contributes its distinct cited domains once. The share is own-site citations divided by all domain citations (own site, directory and multi-city together), summed over the engine's answers that month. It is not the share of the engine's distinct domains across the whole month, which runs higher because directories repeat across answers and business sites mostly do not.</li>
<li><strong>Most cited source.</strong> The number of answers citing a domain at least once; a domain counts once per answer.</li>
<li><strong>Samples.</strong> One answer per question per engine per month. AI engines are not deterministic, so any single question's monthly result is provisional. The aggregate figures across 100 questions are the index. The noise floor is measured, not assumed, with the subsample below.</li>
</ul>
<h2>Same-day repeat subsample</h2>
<p>With each monthly run, 10 of the 100 questions (one per vertical, city rotating) are asked three times on the same day on every engine. The agreement rate on the named businesses and on the cited domains is published here and is the floor under which a month-over-month move is noise. "Same first-named business" is an exact match on the first extracted name, so a spelling or suffix difference counts as a miss, and a group in which any sample extracted no name counts as disagreement. The name rates are therefore conservative, and a low figure on an engine that often names nobody (Claude in November 2026) mixes real instability with answers that declined to name a business.</p>
{var_sections}
<h2>Changelog</h2>
<ul>
<li>2026-07-02: month zero collected (two engines) for the Central Florida AI Citation Study. Its published analysis (a1) split domains into two classes, aggregator and own site, with a 4-city rule; the figures on this site are recomputed under the current analysis and can differ from the study page.</li>
<li>2026-11-02: Local AI Sources filed as EVOIX aeo-lab experiment EXP-015 with predictions written before the first monthly run. Domain registered. Analysis a3: nine domains appended to the July directory list (experience.com, lawnstarter.com, homeguide.com, trustanalytica.com, bing.com, apple.com, tiktok.com, x.com, twitter.com); the city rule became its own class, multi-city site, at {MULTI_CITY_THRESHOLD} cities, decided per month across all engines, after a code review found the 4-city rule labelling regional businesses as directories; table header rows excluded from name extraction; failed calls counted and shown.</li>
<li>2026-11-02: month one collected, four engines, 400 answers, 04:52 to 05:30 EST, charge $13.36. Analysis a4: 46 domains appended to the directory list after reading the November top sources on the two new lanes and the long tail (directories, aggregators, ranking and listicle sites, media, reference, government, professional associations, manufacturer and insurer finders; the full list is in <code>scripts/classify.py</code>, including <code>delandlocal.com</code>, disclosed above). Nine domains cited in three or more answers could not be verified today and are left to the multi-city rule for now: smarfle.com, theroofingbrief.com, legaldirectorate.com, toptaxhq.com, prosgrade.com, cityvetted.com, myheronhome.com, roof.info, hvacservice.io. Gemini redirect links resolved to real URLs (above). The collector stops on a confirmed empty account balance and treats a one-off 40200 as a retryable row.</li>
<li>2026-11-02, later the same day: analysis a5. A review of the first November build found about one extracted name in ten was not a business (an address, a star rating, a line of advice such as "Verify Licensing &amp; Insurance", or three names bundled in one bold run; about one in five on the Gemini lane). The extractor now filters those as described under "Naming a business"; the word list it uses is published as <code>data/generic-words.txt</code>. Naming rates moved with it (Claude 76 to 72 of 100, Gemini 100 to 99). July is recomputed under the same rule.</li>
</ul>
<h2>Related work</h2>
<p>Three public indexes measure AI citations at the global, category level and are worth reading alongside this one: <a href="https://promvia.app/ai-source-index">Promvia's AI Source Index</a> (weekly, 40 buyer questions, every row published), <a href="https://brandinsightai.com/sources">BrandInsightAI's AI Source Bias Index</a> and <a href="https://www.heyamos.com/ai-citation-index">HeyAmos's AI Sources Index</a>. This index is the local complement: fixed cities, fixed verticals, named businesses, monthly, from July 2026.</p>
<h2>Corrections</h2>
<p>If a name was extracted wrongly, a domain is misclassified, or a business believes an engine's answer about it is inaccurate, write through the <a href="{CONTACT_URL}">EVOIX contact page</a>. Extraction and classification errors are fixed in the next build and logged above. Engine answers themselves are reproduced as returned and are not edited.</p>
<h2>The 100 prompts</h2>
{prompts_html}
"""
    write("method/index.html", shell("Local AI Sources method, instrument and changelog",
                                     "How the Local AI Sources panel is collected and counted: 100 fixed prompts, four AI engines, pinned models, published rows, measured noise floor.", "/method/", body, latest_date))
    pages.append(("/method/", latest_date))

    # ---- sitemap, llms.txt, 404, css
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"<url><loc>{SITE}{p}</loc><lastmod>{lm}</lastmod></url>\n" for p, lm in pages) + "</urlset>\n"
    write("sitemap.xml", sm)
    llms = f"""# {SITE_NAME}

> A public monthly record of which businesses and which source domains AI engines (ChatGPT, Perplexity, Claude, Gemini) cite when asked "Who is the best {{vertical}} in {{city}}, Florida?" for 10 service verticals in 10 Central Florida cities. Published by EVOIX LLC, DeLand, Florida. Author Stephane Morera. Data CC BY 4.0.

Latest run: {month_label(latest)}, collected {latest_date}. Panel v1, 100 fixed prompts, one answer per prompt per engine per month, every row published.

## Pages
- [Home]({SITE}/): this month's headline figures per engine
- [Method]({SITE}/method/): panel, instrument, what is counted, changelog, noise floor
- [Data]({SITE}/data/): JSON and CSV downloads per month
- [Engines]({SITE}/engines/): per-engine pages
- [Sources]({SITE}/domains/): every cited domain with counts
- [Months]({SITE}/runs/): every monthly run

## Origin
- [Central Florida AI Citation Study]({STUDY_URL}): the July 2026 study that became month zero
"""
    write("llms.txt", llms)
    write("404.html", shell("Page not found", "This page does not exist on Local AI Sources.", "/404.html",
                            "<h1>Not here</h1><p>Try the <a href=\"/\">home page</a>, the <a href=\"/runs/\">monthly runs</a> or the <a href=\"/domains/\">source list</a>.</p>", latest_date))
    write("assets/style.css", CSS)
    return pages


def variance_agreement(rows):
    """Agreement across same-day samples: share of (prompt, engine) groups where all samples
    share at least one named business, and where all samples share at least one cited domain."""
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
    out = "<table><tr><th>Engine</th><th class=\"num\">Question groups</th><th class=\"num\">Same first-named business in all samples</th><th class=\"num\">At least one shared name</th><th class=\"num\">At least one shared domain</th></tr>"
    for e in ENGINE_ORDER:
        if e not in per_engine:
            continue
        pe = per_engine[e]
        g = pe["groups"] or 1
        out += (f"<tr><td>{ENGINE_NAMES[e]}</td><td class=\"num\">{pe['groups']}</td><td class=\"num\">{pe['top_name_agree']} ({round(pe['top_name_agree'] / g * 100)}%)</td>"
                f"<td class=\"num\">{pe['names_agree']} ({round(pe['names_agree'] / g * 100)}%)</td><td class=\"num\">{pe['domains_agree']} ({round(pe['domains_agree'] / g * 100)}%)</td></tr>")
    out += "</table>"
    return out


def main():
    panel = load_panel()
    runs = load_runs()
    if not runs:
        sys.exit("no runs found under data/runs/")
    variance = load_variance()
    pages = build(panel, runs, variance)
    print(f"built {len(pages)} pages from runs {', '.join(sorted(runs))}")


if __name__ == "__main__":
    main()
