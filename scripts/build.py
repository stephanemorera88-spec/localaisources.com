#!/usr/bin/env python3
"""Render localaisources.com from data/. Standard library only.

Inputs
  data/panel-v1.json          the frozen prompts
  data/runs/YYYY-MM.jsonl     one row per prompt per engine per month
  data/runs/YYYY-MM-variance.jsonl   optional same-day N=3 subsample
  assets/plates/paper.png     the paper ground, a clean crop of the approved comp; tiled by assets/plates/paper.svg

Outputs (repository root, served by GitHub Pages)
  index.html, {city}/{vertical}/, domains/{domain}/, engines/{engine}/,
  runs/{run}/, method/, data/ (+ json, csv), sitemap.xml, llms.txt, 404.html,
  assets/site.css, assets/plates/paper.svg

Layers
  analysis.py   reads the rows and computes every figure
  view models   (this file, "views") shape the figures per page type; no HTML
  templates     (this file, "templates") turn a view into HTML; no arithmetic
Nothing numeric is typed in. A number that appears on a page was computed from the rows.
"""

import base64
import csv
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import (ANALYSIS_VERSION, AUTHOR_ID, CONTACT_URL, ENGINE_NAMES, ENGINE_ORDER, KIND_LABEL,  # noqa: E402
                      MONTHS, MULTI_CITY_THRESHOLD, PUBLISHER, PUBLISHER_URL, ROOT, SITE, SITE_NAME, STUDY_URL,
                      analyse_run, day, extract_names, group_businesses, load_panel, load_runs, load_variance,
                      row_cost, variance_stats)

TODAY = date.today().isoformat()
MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# vertical -> (thumb tab, section head on the home page, head on the owner page)
TRADES = {
    "roofer": ("Roofer", "Roofers", "Roofers"),
    "AC repair company": ("AC repair", "AC repair", "AC repair"),
    "plumber": ("Plumber", "Plumbers", "Plumbers"),
    "personal injury lawyer": ("Lawyer", "Personal injury lawyers", "Injury lawyers"),
    "dentist": ("Dentist", "Dentists", "Dentists"),
    "chiropractor": ("Chiropractor", "Chiropractors", "Chiropractors"),
    "real estate agent": ("Real estate", "Real estate agents", "Real estate agents"),
    "landscaping company": ("Landscaper", "Landscapers", "Landscapers"),
    "pest control company": ("Pest control", "Pest control", "Pest control"),
    "CPA": ("CPA", "CPAs", "CPAs"),
}
TAGLINE = "Who the AI engines name in Central Florida, reprinted every first Monday"


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


def short_date(iso):
    """'2026-11-02' -> 'Nov 2'. Empty in, empty out."""
    d = day(iso)
    if not d:
        return ""
    y, m, dd = d.split("-")
    return f"{MONTHS_SHORT[int(m) - 1]} {int(dd)}"


def article(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def cap(s):
    return s[:1].upper() + s[1:]


def plural(n, word, words=None):
    return f"{n} {word if n == 1 else (words or word + 's')}"


def pct(x):
    return "n/a" if x is None else f"{round(x * 100)}%"


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def trade(vertical):
    return TRADES.get(vertical, (cap(vertical), cap(vertical) + "s", cap(vertical) + "s"))


def trade_anchor(vertical):
    return slug(trade(vertical)[1])


# ----------------------------------------------------------------------------
# views: the shapes each page type renders. Figures only, no HTML.
# ----------------------------------------------------------------------------

class Index:
    """Everything the templates need, computed once."""

    def __init__(self, panel, runs, variance):
        self.panel = panel
        self.panel_size = len(panel["prompts"])
        self.run_ids = sorted(runs)
        self.latest = self.run_ids[-1]
        self.rows = {rid: runs[rid]["rows"] for rid in self.run_ids}
        self.stats = {rid: analyse_run(runs[rid]["rows"], runs[rid]["failed"], self.panel_size) for rid in self.run_ids}
        self.run_date = {rid: min((self.stats[rid][e]["first"] or rid + "-01") for e in self.stats[rid]) for rid in self.run_ids}
        self.retried = {rid: runs[rid].get("retried", Counter()) for rid in self.run_ids}
        self.variance_cost = {rid: sum(row_cost(r) for r in rows) for rid, rows in variance.items()}
        self.variance = {rid: variance_stats(rows) for rid, rows in variance.items()}
        # One row per question per engine per month is what every N=1 sentence on the site asserts. A month with
        # several samples per question (December 2026 onwards) needs the aggregation rule (analysis a6+) first.
        for rid in self.run_ids:
            dup = [(q, e) for (q, e), n in Counter((r["query_id"], r["engine"]) for r in runs[rid]["rows"]).items() if n > 1]
            if dup:
                sys.exit(f"{rid}: {len(dup)} question/engine pairs have more than one sample (first: {dup[0]}); "
                         "the N=3 aggregation rule is not implemented, so this month cannot be built under N=1 wording.")
        # query_id -> run -> engine -> row. One row per engine per month today (N=1); the N=3 aggregation
        # rule (analysis a6, before the December 2026 run) will turn the row into a list of samples here.
        self.by_q = defaultdict(lambda: defaultdict(dict))
        for rid in self.run_ids:
            for r in runs[rid]["rows"]:
                self.by_q[r["query_id"]][rid][r["engine"]] = r
        self.all_engines = [e for e in ENGINE_ORDER if any(e in self.stats[rid] for rid in self.run_ids)]
        self.pages = []   # (path, lastmod) for the sitemap

    def engines_in(self, rid):
        return [e for e in ENGINE_ORDER if e in self.stats[rid]]

    @property
    def latest_date(self):
        return self.run_date[self.latest]

    def question_month(self, qid, rid):
        """One question in one month: engines asked, who named a business, businesses grouped across engines,
        and what each engine cited. None when the month has no row for the question."""
        per = self.by_q[qid].get(rid, {})
        if not per:
            return None
        asked = self.engines_in(rid)
        answered = [e for e in asked if e in per]
        named = [e for e in answered if per[e].get("names")]
        collected = max(day(per[e].get("datetime")) for e in answered) or self.run_date[rid]
        businesses = group_businesses(per, ENGINE_ORDER)
        groups = defaultdict(list)
        for b in businesses:
            groups[len(b["engines"])].append(b)
        engines = []
        for e in answered:
            r = per[e]
            engines.append({
                "engine": e, "model": r.get("model_name") or r.get("model_requested") or "",
                "date": day(r.get("datetime")), "names": r.get("names") or [],
                "sources": [{"domain": d, "kind": r["kinds"].get(d)} for d in r.get("domains") or []],
            })
        own = sum(1 for en in engines for s in en["sources"] if s["kind"] == "own-site")
        dirs = sum(1 for en in engines for s in en["sources"] if s["kind"] == "directory")
        return {
            "rid": rid, "asked": asked, "answered": answered, "named": named,
            "silent": [e for e in answered if e not in named], "missing": [e for e in asked if e not in per],
            "collected": collected, "groups": dict(sorted(groups.items(), reverse=True)),
            "engines": engines, "own": own, "dirs": dirs,
        }

    def home_lines(self):
        """Per trade, per city: how many of the month's engines named at least one business."""
        rid = self.latest
        out = []
        for v in self.panel["verticals"]:
            lines = []
            for c in self.panel["cities"]:
                qid = next(p["query_id"] for p in self.panel["prompts"] if p["vertical"] == v and p["city"] == c)
                qm = self.question_month(qid, rid)
                # k of n: engines whose answer to this question carried an extracted name, over engines that answered it.
                # The same denominator the question page uses. None when the question was not asked this month.
                k = len(qm["named"]) if qm else None
                n = len(qm["answered"]) if qm else None
                lines.append({"city": c, "vertical": v, "path": f"/{slug(c)}/{slug(v)}/", "k": k, "n": n})
            out.append({"vertical": v, "anchor": trade_anchor(v), "head": trade(v)[1], "lines": lines})
        return out

    def domain_rows(self):
        """domain -> list of (rid, engine, qid, vertical, city, kind)."""
        dom = defaultdict(list)
        for rid in self.run_ids:
            for r in self.rows[rid]:
                for d in r.get("domains", []):
                    dom[d].append((rid, r["engine"], r["query_id"], r["vertical"], r["city"], r["kinds"].get(d)))
        return dom


# ----------------------------------------------------------------------------
# templates: the book
# ----------------------------------------------------------------------------

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

SECTIONS_NAV = [("/engines/", "Engines"), ("/domains/", "Sources"), ("/runs/", "Months"), ("/method/", "Method"), ("/data/", "Data")]


def tabs_html(panel, current_vertical=None, on_home=False):
    items = []
    for v in panel["verticals"]:
        href = ("#" if on_home else "/#") + trade_anchor(v)
        cur = ' aria-current="page"' if v == current_vertical else ""
        items.append(f'<li><a href="{href}"{cur}>{esc(trade(v)[0])}</a></li>')
    return f'<nav class="tabs" aria-label="Trades"><ul>{"".join(items)}</ul></nav>'


def shell(ix, title, desc, path, body, lastmod, ld=None, og_type="website", months=None, current_vertical=None,
          script=""):
    """months: [(anchor, label)] shown in the running head, first one current."""
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
        {"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    nav = "".join(f'<a href="{h}"{" aria-current=page" if path.startswith(h) else ""}>{t}</a>' for h, t in SECTIONS_NAV)
    months_nav = ""
    if months:
        months_nav = '<nav class="months" aria-label="Months">' + "".join(
            f'<a href="#{a}"{" aria-current=true" if i == 0 else ""}>{esc(l)}</a>' for i, (a, l) in enumerate(months)) + "</nav>"
    line1 = "" if path == "/" else f'<div class="line1"><a class="home" href="/">{SITE_NAME}</a>{months_nav}</div>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#f3cf4a">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:site" content="@Stephane_Morera">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/assets/fonts/BebasNeue-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
{ld_block}
</head>
<body>
<a class="skip" href="#main">Skip to the listings</a>
<div class="book">
<header class="runhead">{line1}<nav class="sections" aria-label="Sections">{nav}</nav></header>
{tabs_html(ix.panel, current_vertical, on_home=(path == "/"))}
<main id="main">
{body}
</main>
<footer class="colophon">
<p class="pub">Published by EVOIX, DeLand, Florida</p>
<div class="prose small"><p>{SITE_NAME} is published by <a href="{PUBLISHER_URL}">{PUBLISHER}</a> and written by <a href="https://stephanemorera.com/">Stephane Morera</a>. Data under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, code under MIT, both on <a href="https://github.com/stephanemorera88-spec/localaisources.com">GitHub</a>. Engine answers are recorded as returned and are not EVOIX recommendations. Extraction errors can be reported through the <a href="{CONTACT_URL}">EVOIX contact page</a>. Page data as of {esc(lastmod)}, analysis {ANALYSIS_VERSION}.</p></div>
</footer>
</div>
{script}</body>
</html>
"""


def lead(h1, ask="", q="", tag=""):
    """The page's display ad: double red rule, the heading, an optional red line and a quoted or plain line."""
    out = [f'<section class="ad lead"><h1>{h1}</h1>']
    if tag:
        out.append(f'<p class="tag">{tag}</p>')
    if ask:
        out.append(f'<p class="ask">{ask}</p>')
    if q:
        out.append(f'<p class="q">{q}</p>')
    out.append("</section>")
    return "".join(out)


def notice(text):
    return f'<section class="ad notice"><p>{text}</p></section>'


def rule_head(text, level=2, anchor=None):
    a = f' id="{anchor}"' if anchor else ""
    return f"<h{level}{a}>{text}</h{level}>"


def lines(items, cls=""):
    """Ledger lines. items: (label_html, value_html, href or None)."""
    out = [f'<ol class="lines {cls}">']
    for label, value, href in items:
        inner = f'<span class="k">{label}</span><span class="v">{value}</span>'
        out.append(f'<li><a class="row" href="{href}">{inner}</a></li>' if href else f'<li><span class="row">{inner}</span></li>')
    out.append("</ol>")
    return "".join(out)


def facts(items):
    """Definition ledger for a block of figures. items: (term_html, value_html)."""
    return '<dl class="lines">' + "".join(
        f'<div class="row"><dt class="k">{t}</dt><dd class="v">{v}</dd></div>' for t, v in items) + "</dl>"


def two_line(items):
    """Two-line listings: the name, then who named it. items: (name_html, who_html, href or None)."""
    out = ['<ol class="lines listing">']
    for name, who, href in items:
        inner = f'<span class="nm">{name}</span><span class="who">{who}</span>'
        out.append(f'<li><a class="row" href="{href}">{inner}</a></li>' if href else f'<li><span class="row">{inner}</span></li>')
    out.append("</ol>")
    return "".join(out)


def domain_link(d, kind=None):
    if kind == "own-site":
        return f'<a class="own" href="/domains/{slug(d)}/">{esc(d)}<span class="vh"> (own site)</span></a>'
    return f'<a href="/domains/{slug(d)}/">{esc(d)}</a>'


def engine_link(e):
    return f'<a href="/engines/{e}/">{ENGINE_NAMES[e]}</a>'


def names_list(engines):
    return ", ".join(ENGINE_NAMES[e] for e in engines)


# ----------------------------------------------------------------------------
# pages
# ----------------------------------------------------------------------------

def build_home(ix):
    rid = ix.latest
    engs = ix.engines_in(rid)
    n_eng = len(engs)
    panel = ix.panel
    cities = "".join(f'<option value="{slug(c)}">{esc(c)}</option>' for c in panel["cities"])
    trades = "".join(f'<option value="{slug(v)}">{esc(trade(v)[1])}</option>' for v in panel["verticals"])
    finder = f"""<form class="finder" action="/" method="get">
<label><span class="vh">Your city</span><select name="city" required><option value="" selected disabled>Your city</option>{cities}</select></label>
<label><span class="vh">Your trade</span><select name="trade" required><option value="" selected disabled>Your trade</option>{trades}</select></label>
<button type="submit">See who AI names</button>
</form>"""
    head = (f'<section class="ad lead"><h1>{SITE_NAME}</h1><p class="tag">{TAGLINE}</p>{finder}</section>')
    failed_total = sum(ix.stats[rid][e]["failed"] for e in engs)
    failed_note = f" {failed_total} calls returned no answer and count as missing." if failed_total else ""
    note = notice(f'The <a href="/runs/{rid}/">{month_label(rid)}</a> record. {n_eng} engines, {ix.panel_size} questions. '
                  f'Collected {short_date(ix.latest_date)}. N=1 per question, provisional. '
                  f'Each line counts the engines whose answer carried a name we could extract. Extraction is automatic and imperfect; the <a href="/method/">method page</a> says how.{failed_note}')
    listing = ['<section class="listings">']
    for block in ix.home_lines():
        listing.append(rule_head(esc(block["head"]), 2, block["anchor"]))
        listing.append(lines([(esc(l["city"]), f'{l["k"]} of {l["n"]}' if l["n"] else "not asked", l["path"]) for l in block["lines"]], "two"))
    listing.append("</section>")
    about = f"""<section class="prose about">
<h2>About this book</h2>
<p>Every month, on the first Monday, we ask {n_eng} AI engines the same {ix.panel_size} questions, "Who is the best {{trade}} in {{city}}, Florida?", for {len(panel['verticals'])} trades across {len(panel['cities'])} Central Florida cities, with live web search on. We record every business named and every source cited, and print all of it here, right or wrong. A business listed on a page was named by that engine on that date. It is not an EVOIX recommendation, and absence is not a judgement of any business.</p>
<p>The global indexes that exist, Promvia's AI Source Index, BrandInsightAI's GEO Index and HeyAmos's AI Sources Index among them, answer at the level of "best CRM" and report domains worldwide. None of them asks about a roofer in DeLand or names the businesses. This one does, on a fixed panel, so the record can be compared over time and reproduced by anyone with the prompt list and the <a href="/method/">method</a>. It began as EVOIX's <a href="{STUDY_URL}">Central Florida AI Citation Study</a>, collected 2 July 2026; that run is month zero here and the panel has not changed since. The full {month_label(rid)} run, with every engine's figures and most cited sources, is on the <a href="/runs/{rid}/">month page</a>; the rows are <a href="/data/">free to download</a>.</p>
</section>"""
    body = head + note + "".join(listing) + about
    desc = (f"A public monthly record of which businesses and which sources {n_eng} AI engines cite when asked who the best "
            f"roofer, plumber, dentist and seven other local providers are in 10 Central Florida cities. {month_label(rid)} edition.")
    script = ("<script>document.querySelector('.finder').addEventListener('submit',function(e){e.preventDefault();"
              "var c=this.city.value,t=this.trade.value;if(c&&t){location.href='/'+c+'/'+t+'/'}});</script>")
    write("index.html", shell(ix, f"{SITE_NAME}: which businesses AI engines recommend in Central Florida, {month_label(rid)}",
                              desc, "/", body, ix.latest_date, script=script))
    ix.pages.append(("/", ix.latest_date))


def question_month_html(qm):
    rid = qm["rid"]
    n = len(qm["answered"])
    named_txt = f"a name was extracted from {len(qm['named'])} of {n}" if n else "no answers"
    note = notice(f'The <a href="/runs/{rid}/">{month_label(rid)}</a> record. {n} engines, one answer each, {named_txt}. '
                  f'Collected {short_date(qm["collected"])}. N=1, provisional. Names printed as returned. A record, not a recommendation.')
    out = [f'<section class="month" id="{rid}">', note]
    if qm["missing"]:
        out.append(f'<p class="aside">No answer was returned by {names_list(qm["missing"])} this month.</p>')
    if not qm["groups"]:
        out.append(rule_head("No business named"))
        out.append('<p class="aside">None of the answers named a specific business.</p>')
    for k, group in qm["groups"].items():
        label = f"Named by {k} of {n} engines" if k > 1 else "Named by 1 engine"
        out.append(rule_head(label))
        out.append(two_line([(esc(b["name"]), names_list(b["engines"]), None) for b in group]))
    if qm["silent"] and qm["groups"]:
        who = names_list(qm["silent"])
        out.append(f'<p class="aside">No name could be extracted from the answer by {who}.</p>')
    out.append(rule_head("Where the engines looked"))
    out.append('<div class="srcs">')
    for en in qm["engines"]:
        srcs = " &middot; ".join(domain_link(s["domain"], s["kind"]) for s in en["sources"]) or "no sources cited"
        out.append(f'<p><b>{engine_link(en["engine"])}</b> <small>{esc(en["model"])}, {short_date(en["date"])}</small><br>{srcs}</p>')
    out.append('<p class="legend"><span class="own legend-sample">Red and underlined</span> = not a directory and not a multi-city site, so it reads as a business&rsquo;s own site. Everything else is a directory, an aggregator or a multi-city site.</p></div>')
    out.append("</section>")
    return "".join(out)


def build_questions(ix):
    for p in ix.panel["prompts"]:
        qid, v, c = p["query_id"], p["vertical"], p["city"]
        path = f"/{slug(c)}/{slug(v)}/"
        months = []
        sections = []
        for rid in reversed(ix.run_ids):
            qm = ix.question_month(qid, rid)
            if not qm:
                continue
            months.append((rid, month_label(rid), qm))
            sections.append(question_month_html(qm))
        if not months:
            continue
        latest_qm = months[0][2]
        page_date = latest_qm["collected"]
        n = len(latest_qm["answered"])
        k = len(latest_qm["named"])
        title = f"Who do AI engines recommend for {article(v)} {v} in {c}, Florida? ({month_label(ix.latest)})"
        desc = (f"In {month_label(ix.latest)}, a name could be extracted from {k} of {n} AI engine answers about the best {v} in {c}, Florida; "
                f"together the answers cited {latest_qm['own']} business websites and {latest_qm['dirs']} directories. Names and sources, recorded as returned.")
        head = lead(f'{esc(trade(v)[2])} <span class="dot">&middot;</span> {esc(c)}',
                    ask=f"Asked of {len(latest_qm['asked'])} AI engines",
                    q=f"&ldquo;{esc(p['prompt'])}&rdquo;")
        note = ('<div class="prose note"><p>Names are extracted automatically from each answer&rsquo;s bold text, numbered headings and tables, so a name can be missed, cut oddly, or turn out to be a directory or an agency rather than a business; '
                'the full answer text is in the <a href="/data/">downloadable rows</a>. A business listed here was named by that engine on that date. '
                'It is not an EVOIX recommendation, and absence from this page is not a judgement of any business.</p></div>')
        body = head + "".join(sections) + note
        write(path.strip("/") + "/index.html",
              shell(ix, title, desc, path, body, page_date, og_type="article",
                    months=[(a, l) for a, l, _ in months], current_vertical=v))
        ix.pages.append((path, page_date))


def build_domains(ix):
    dom_rows = ix.domain_rows()
    index_items = []
    for d, lst in sorted(dom_rows.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        kind_by_run = {}
        for rid, e, qid, v, c, k in lst:
            kind_by_run[rid] = k
        latest_kind = kind_by_run[max(kind_by_run)]
        path = f"/domains/{slug(d)}/"
        by_run = defaultdict(Counter)
        for rid, e, *_ in lst:
            by_run[rid][e] += 1
        per_month = []
        for rid in reversed(ix.run_ids):
            if rid not in by_run:
                continue
            per_month.append(rule_head(f'<a href="/runs/{rid}/">{month_label(rid)}</a> <span class="kind">{esc(KIND_LABEL[kind_by_run[rid]])}</span>'))
            per_month.append(facts([(engine_link(e), str(by_run[rid].get(e, 0)) if e in ix.stats[rid] else "not run") for e in ix.all_engines]))
        qlist = defaultdict(set)
        for rid, e, qid, v, c, _k in lst:
            qlist[(v, c)].add(e)
        questions = two_line([(f"{esc(trade(v)[2])} <span class=\"dot\">&middot;</span> {esc(c)}",
                               names_list([e for e in ENGINE_ORDER if e in ents]), f"/{slug(c)}/{slug(v)}/")
                              for (v, c), ents in sorted(qlist.items(), key=lambda kv: (kv[0][1], kv[0][0]))])
        dom_date = max(ix.run_date[rid] for rid in kind_by_run)
        runs_txt = plural(len(kind_by_run), "monthly run")
        title = f"{d}: how often AI engines cite it for Central Florida local-service questions"
        desc = f"{d} was cited in {len(lst)} answers across {runs_txt} of the Local AI Sources panel. Classified as {KIND_LABEL[latest_kind]} in the latest month."
        head = lead(esc(d), ask=esc(KIND_LABEL[latest_kind]),
                    q=f"Cited in {plural(len(lst), 'answer')} across {runs_txt}")
        body = (head + f'<div class="prose note"><p>Classification is decided per month from that month&rsquo;s rows (analysis {ANALYSIS_VERSION}), so a domain can change class between months.</p></div>'
                + rule_head("Answers citing it, by month and engine") + "".join(per_month)
                + rule_head("Questions it was cited on") + questions)
        write(path.strip("/") + "/index.html", shell(ix, title, desc, path, body, dom_date))
        ix.pages.append((path, dom_date))
        index_items.append((esc(d), f"{len(lst)} <small>{esc(KIND_LABEL[latest_kind])}</small>", path))
    head = lead("Sources", ask=f"{len(dom_rows)} domains across {plural(len(ix.run_ids), 'monthly run')}",
                q="Every domain an engine cited, most cited first")
    body = (head + '<div class="prose note"><p>The count is the number of answers citing the domain, all engines and months combined. The class beside it is the latest month&rsquo;s.</p></div>'
            + lines(index_items, "ledger"))
    write("domains/index.html", shell(ix, "Sources cited by AI engines for Central Florida local-service questions",
                                      f"{len(dom_rows)} distinct domains cited across the Local AI Sources panel, with counts.", "/domains/", body, ix.latest_date))
    ix.pages.append(("/domains/", ix.latest_date))


def engine_month_facts(s, rid):
    top = s["top"][0] if s["top"] else None
    answers = f"{s['answers']} of {s['expected']}" + (f" ({s['failed']} calls failed)" if s["failed"] else "")
    return facts([
        ("Answers returned", answers),
        ("Answers with an extracted name", str(s["named_any"])),
        ("With sources", str(s["with_sources"])),
        ("Own-site share of citations", pct(s["own_share"])),
        ("Multi-city site citations", str(s["multi"])),
        ("Unique domains", str(s["unique_domains"])),
        ("Names per answer, all answers", f"{s['avg_named']:.1f}"),
        ("Most cited source", (domain_link(top[0], s["kinds"].get(top[0])) + f" <small>{top[1]} of {s['answers']}</small>") if top else "none cited"),
    ])


def top_domains(s, limit):
    """The most cited domains, at least `limit` of them; every domain tied with the last one shown is shown too."""
    if not s["top"]:
        return '<p class="aside">None cited.</p>'
    cut = s["top"][min(limit, len(s["top"])) - 1][1]
    shown = [(d, n) for d, n in s["top"] if n >= cut]
    return lines([(domain_link(d, s["kinds"].get(d)), str(n), None) for d, n in shown], "ledger")


def build_engines(ix):
    index_items = []
    for e in ix.all_engines:
        path = f"/engines/{e}/"
        sec = []
        for rid in reversed(ix.run_ids):
            if e not in ix.stats[rid]:
                continue
            s = ix.stats[rid][e]
            sec.append(rule_head(f'<a href="/runs/{rid}/">{month_label(rid)}</a> <span class="kind">{esc(", ".join(s["models"]))}</span>'))
            sec.append(engine_month_facts(s, rid))
            sec.append(rule_head("Most cited domains", 3))
            sec.append(top_domains(s, 20))
        s = ix.stats[ix.latest].get(e)
        eng_date = max(ix.run_date[rid] for rid in ix.run_ids if e in ix.stats[rid])
        title = f"What {ENGINE_NAMES[e]} cites for Central Florida local-service questions"
        desc = (f"{ENGINE_NAMES[e]} on the Local AI Sources panel: how often it names a business, its own-site share and its most cited domains, by month."
                if not s else f"In {month_label(ix.latest)}, a name was extracted from {s['named_any']} of {s['answers']} {ENGINE_NAMES[e]} answers, with an own-site citation share of {pct(s['own_share'])}. Most cited domains by month.")
        head = lead(ENGINE_NAMES[e], ask=f"On the panel since {month_label(min(rid for rid in ix.run_ids if e in ix.stats[rid]))}",
                    q=(f"A name was extracted from {s['named_any']} of {s['answers']} answers in {month_label(ix.latest)}" if s else ""))
        write(path.strip("/") + "/index.html", shell(ix, title, desc, path, head + "".join(sec), eng_date))
        ix.pages.append((path, eng_date))
        index_items.append((ENGINE_NAMES[e], f"{s['named_any']} of {s['answers']}" if s else "not run", path))
    head = lead("Engines", ask=f"{len(ix.all_engines)} engines on the panel", q=f"Answers with an extracted name, {month_label(ix.latest)}")
    write("engines/index.html", shell(ix, "Engines on the Local AI Sources panel", "Per-engine pages: ChatGPT, Perplexity, Claude and Gemini on 100 Central Florida local-service questions.", "/engines/",
                                      head + lines(index_items, "ledger"), ix.latest_date))
    ix.pages.append(("/engines/", ix.latest_date))


def variance_html(per_engine):
    out = []
    for e in ENGINE_ORDER:
        if e not in per_engine:
            continue
        pe = per_engine[e]
        g = pe["groups"] or 1
        out.append(rule_head(ENGINE_NAMES[e], 3))
        out.append(facts([
            ("Question groups", str(pe["groups"])),
            ("Same first-named business in all samples", f"{pe['top_name_agree']} ({round(pe['top_name_agree'] / g * 100)}%)"),
            ("At least one shared name", f"{pe['names_agree']} ({round(pe['names_agree'] / g * 100)}%)"),
            ("At least one shared domain", f"{pe['domains_agree']} ({round(pe['domains_agree'] / g * 100)}%)"),
        ]))
    return "".join(out)


def build_runs(ix):
    index_items = []
    for rid in reversed(ix.run_ids):
        path = f"/runs/{rid}/"
        st = ix.stats[rid]
        engs = ix.engines_in(rid)
        cost = sum(st[e]["cost"] for e in engs)
        n_answers = sum(st[e]["answers"] for e in engs)
        n_failed = sum(st[e]["failed"] for e in engs)
        sec = []
        for e in engs:
            s = st[e]
            sec.append(rule_head(f'{engine_link(e)} <span class="kind">{esc(", ".join(s["models"]))}</span>'))
            sec.append(engine_month_facts(s, rid))
            sec.append(rule_head("Most cited domains", 3))
            sec.append(top_domains(s, 15))
        var = ix.variance.get(rid)
        if var:
            sec.append(rule_head("Same-day repeat subsample"))
            sec.append('<div class="prose note"><p>Ten of the 100 questions were asked three times on the same day on every engine. The agreement between the three answers is the noise floor under which a month-over-month move is noise. Definitions on the <a href="/method/">method page</a>.</p></div>')
            sec.append(variance_html(var))
        collected = ix.run_date[rid]
        failed_txt = f" {n_failed} call(s) returned no answer and are excluded from every figure on this page." if n_failed else ""
        title = f"{month_label(rid)} run: what {len(engs)} AI engines cited for 100 Central Florida local-service questions"
        desc = f"Local AI Sources {month_label(rid)}: {len(engs)} engines, {n_answers} answers, collected {collected}. Per-engine naming rate, own-site share and most cited domains."
        head = lead(month_label(rid), ask=f"{plural(len(engs), 'engine')}, {plural(n_answers, 'answer')}",
                    q=f"Collected {esc(collected)}. One answer per question per engine.{failed_txt} Recorded API charge ${cost:.2f}.")
        dl = f'<p class="aside"><a href="/data/{rid}.csv">Download this month as CSV</a> &middot; <a href="/data/{rid}.json">JSON with full answers</a></p>'
        write(path.strip("/") + "/index.html", shell(ix, title, desc, path, head + "".join(sec) + dl, collected, og_type="article"))
        ix.pages.append((path, collected))
        index_items.append((month_label(rid), f"{plural(len(engs), 'engine')}, collected {short_date(collected)}", path))
    head = lead("Months", ask=plural(len(ix.run_ids), "monthly run"), q="Newest first. Reprinted every first Monday.")
    write("runs/index.html", shell(ix, "Monthly runs of the Local AI Sources panel", "Every monthly run, newest first.", "/runs/", head + lines(index_items, "ledger"), ix.latest_date))
    ix.pages.append(("/runs/", ix.latest_date))


def build_data(ix):
    for rid in ix.run_ids:
        rows = ix.rows[rid]
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
        "temporalCoverage": f"{ix.run_ids[0]}/{ix.run_ids[-1]}", "spatialCoverage": "Central Florida, United States",
        "keywords": ["AI visibility", "AI citations", "answer engine optimization", "local SEO", "ChatGPT", "Perplexity", "Claude", "Gemini"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE}/data/{rid}.json"} for rid in ix.run_ids]
                        + [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{SITE}/data/{rid}.csv"} for rid in ix.run_ids],
    }]
    items = []
    for rid in reversed(ix.run_ids):
        items.append((f"{month_label(rid)} JSON", "full answers", f"/data/{rid}.json"))
        items.append((f"{month_label(rid)} CSV", "names and domains", f"/data/{rid}.csv"))
    items.append(("Panel v1", "the 100 prompts", "/data/panel-v1.json"))
    head = lead("Data", ask="One row per question per engine per month", q="CC BY 4.0")
    body = (head + lines(items, "ledger")
            + '<div class="prose"><p>The JSON carries the full answer text and every cited URL with its title; the CSV carries the extracted names, the cited domains and the own-site, directory and multi-city counts.</p>'
            + '<p>License <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Attribution: "Local AI Sources by EVOIX LLC, localaisources.com". The answer text is engine output reproduced for research and comparison; it is not written by EVOIX and may contain errors about the businesses it names.</p></div>')
    write("data/index.html", shell(ix, "Local AI Sources data downloads", "Monthly rows of AI engine answers and citations for Central Florida local-service questions, CC BY 4.0.", "/data/", body, ix.latest_date, ld=ds))
    ix.pages.append(("/data/", ix.latest_date))


def build_method(ix):
    panel = ix.panel
    instr = []
    for rid in reversed(ix.run_ids):
        engs = ix.engines_in(rid)
        instr.append(rule_head(month_label(rid), 3))
        extra = [("Questions left without an answer", str(sum(ix.stats[rid][e]["failed"] for e in engs))),
                 ("Attempts that errored and were retried", str(sum(ix.retried[rid].values()))),
                 ("Charge, panel calls", f"${sum(ix.stats[rid][e]['cost'] for e in engs):.2f}")]
        if rid in ix.variance_cost:
            extra.append(("Charge, same-day subsample", f"${ix.variance_cost[rid]:.2f}"))
        instr.append(facts([(ENGINE_NAMES[e], (esc(", ".join(ix.stats[rid][e]["models"])) or "no answers") if e in ix.stats[rid] else "not run") for e in ix.all_engines] + extra))
    var_sections = "".join(rule_head(month_label(rid), 3) + variance_html(v)
                           for rid, v in sorted(ix.variance.items(), reverse=True)) or "<p>No repeat subsample has been run yet.</p>"
    prompts_html = "<ol>" + "".join(f"<li>{esc(p['prompt'])}</li>" for p in panel["prompts"]) + "</ol>"
    head = lead("Method", ask=f"{ix.panel_size} fixed questions, {len(ix.all_engines)} engines, once a month",
                q="Instrument, what is counted, noise floor, changelog")
    body = head + f"""
<div class="prose">
<p>The index is a fixed panel of {ix.panel_size} questions put to the same AI engines once a month through their search-grounded APIs. Every answer and every cited URL is stored and published. Nothing on the site is typed in; every page is generated from the rows.</p>
<h2>Panel v1</h2>
<p>Template <code>{esc(panel['template'])}</code>, frozen {esc(panel['frozen'])}. {len(panel['verticals'])} verticals ({esc(', '.join(panel['verticals']))}) by {len(panel['cities'])} cities ({esc(', '.join(panel['cities']))}). A prompt is never edited. If the panel changes it gets a new version number and the old one stays comparable with itself.</p>
<h2>Instrument</h2>
<p>DataForSEO <code>ai_optimization/{{engine}}/llm_responses/live</code> with <code>web_search: true</code>, United States, English, no location override, no logged-in state. The model is part of the instrument: a month asked with a different model is a different instrument and is compared to earlier months as directional only. Movers are reported only between months with the same instrument. "Charge" is the DataForSEO task charge recorded per call, the figure the collector caps on.</p>
</div>
{"".join(instr)}
<div class="prose">
<p>July 2026 was collected for EVOIX's <a href="{STUDY_URL}">Central Florida AI Citation Study</a> on ChatGPT <code>gpt-5.3-chat-latest</code> and Perplexity <code>sonar</code>. From November 2026 the panel runs on four engines with pinned models (ChatGPT <code>gpt-5.4-2026-03-05</code>, Perplexity <code>sonar-pro</code>, Claude <code>claude-sonnet-5</code>, Gemini <code>gemini-3.6-flash</code>), so the ChatGPT and Perplexity lanes changed instrument between month zero and month one. The model shown on every page is the one the API reported serving, not the one requested: in November 2026 the collector asked for <code>gemini-3.5-flash</code> and DataForSEO served <code>gemini-3.6-flash</code> on all 100 rows, so the Gemini lane is pinned to the served name from December.</p>
<p>Gemini returns every citation as a <code>vertexaisearch.cloud.google.com</code> redirect link. The collector follows each link once and stores the real URL; the redirect link is kept in the row as <code>redirect_url</code>. The handful that fail to resolve fall back to the domain in the citation title and are flagged in the row.</p>
<h2>What is counted</h2>
<ul>
<li><strong>Answers returned.</strong> A question is left without an answer when every attempt at it errored or returned no text. Those are counted and shown, and excluded from every rate, so "88 of 100" means 88 questions came back answered. An attempt that errored and was then answered on a retry is not a failed question; the number of such retries is shown per month above.</li>
<li><strong>Answers with an extracted name.</strong> An answer counts if at least one business name is extracted from its bold text, its numbered headings or its table body rows (table headers are skipped). Since analysis a5 the extractor drops advice headings ("Get Multiple Estimates"), the model's own working headings ("Searching for recommendations"), ratings, addresses and phone lines, splits a bold run of three or more names into separate names, and treats a phrase made only of ordinary English words as a heading unless it carries a trade word (Roofing, Dental, Law, CPA and the like) or matches one of the answer's cited domains. Since a6 it also drops licence types and numbers, awards, certifications and accreditations, review-site phrases ("Google Reviews", "A+ BBB rating"), directory and review-site brands written as names ("Realtor.com", "Super Lawyers"), phrases made only of directory names and review words, regulators, associations and the bar (a department, institute, board, bureau or association), manufacturer contractor programmes ("Master Elite"), "X vs. Y" headings, check-list headings that start with an imperative or an adverb of advice (Verify, Confirm, Compare, Always, Never and a list of about twenty-five such words in <code>scripts/analysis.py</code>), single label words ("Doctors", "Referrals"), and the panel's own city names. The extraction is automatic and conservative. It misses a name written in plain prose, so "no extracted name" is not the same as "named nobody", and a phrase an engine wrote in bold can still slip through as a name when it is none of the above; those are filtered as they are found and logged below. The count on every page is therefore "answers with an extracted name", not "answers naming a business".</li>
<li><strong>One business, several spellings.</strong> On a question's page the names from all engines are grouped into one listing when they differ only in case, punctuation, a parenthesised tail or an entity suffix (Inc, LLC, P.A.). "Hartsock &amp; Mann, CPA" and "Hartsock &amp; Mann CPA" are one business; "Dr. John Cervenka" and "John Cervenka" are kept apart. The spelling shown is the most frequent one.</li>
<li><strong>Source classes.</strong> Each cited domain is one of three things in a given month. <em>Directory</em>: on the published list in <code>scripts/classify.py</code> (directories, aggregators, review, social, reference and lead-gen sites). <em>Multi-city site</em>: not on the list, but cited for the same template across {MULTI_CITY_THRESHOLD} or more of the 10 cities that month, which catches regional businesses, franchises and business sites that publish "best in {{city}}" listicles. <em>Own site</em>: everything else, read as a local business's own website. The class is decided per month across all engines, so a domain has one class per month and can change class between months; the domain pages show the class for every month. Disclosure: <code>delandlocal.com</code> is a DeLand business directory published by EVOIX, the publisher of this index. It is on the directory list, so a citation of it never counts as a business's own site, and it appears in the tables like any other directory.</li>
<li><strong>Own-site share.</strong> Each answer contributes its distinct cited domains once. The share is own-site citations divided by all domain citations (own site, directory and multi-city together), summed over the engine's answers that month. It is not the share of the engine's distinct domains across the whole month, which runs higher because directories repeat across answers and business sites mostly do not.</li>
<li><strong>Most cited source.</strong> The number of answers citing a domain at least once; a domain counts once per answer.</li>
<li><strong>Samples.</strong> One answer per question per engine per month. AI engines are not deterministic, so any single question's monthly result is provisional. The aggregate figures across 100 questions are the index. The noise floor is measured, not assumed, with the subsample below.</li>
</ul>
<h2>Same-day repeat subsample</h2>
<p>With each monthly run, 10 of the 100 questions (one per vertical, city rotating) are asked three times on the same day on every engine. The agreement rate on the named businesses and on the cited domains is published here and is the floor under which a month-over-month move is noise. "Same first-named business" is an exact match on the first extracted name, so a spelling or suffix difference counts as a miss, and a group in which any sample extracted no name counts as disagreement. The name rates are therefore conservative, and a low figure on an engine that often names nobody (Claude in November 2026) mixes real instability with answers that declined to name a business.</p>
</div>
{var_sections}
<div class="prose">
<h2>Changelog</h2>
<ul>
<li>2026-07-02: month zero collected (two engines) for the Central Florida AI Citation Study. Its published analysis (a1) split domains into two classes, aggregator and own site, with a 4-city rule; the figures on this site are recomputed under the current analysis and can differ from the study page.</li>
<li>2026-11-02: Local AI Sources filed as EVOIX aeo-lab experiment EXP-015 with predictions written before the first monthly run. Domain registered. Analysis a3: nine domains appended to the July directory list (experience.com, lawnstarter.com, homeguide.com, trustanalytica.com, bing.com, apple.com, tiktok.com, x.com, twitter.com); the city rule became its own class, multi-city site, at {MULTI_CITY_THRESHOLD} cities, decided per month across all engines, after a code review found the 4-city rule labelling regional businesses as directories; table header rows excluded from name extraction; failed calls counted and shown.</li>
<li>2026-11-02: month one collected, four engines, 400 answers, 04:52 to 05:30 EST, charge $13.36. Analysis a4: 46 domains appended to the directory list after reading the November top sources on the two new lanes and the long tail (directories, aggregators, ranking and listicle sites, media, reference, government, professional associations, manufacturer and insurer finders; the full list is in <code>scripts/classify.py</code>, including <code>delandlocal.com</code>, disclosed above). Nine domains cited in three or more answers could not be verified today and are left to the multi-city rule for now: smarfle.com, theroofingbrief.com, legaldirectorate.com, toptaxhq.com, prosgrade.com, cityvetted.com, myheronhome.com, roof.info, hvacservice.io. Gemini redirect links resolved to real URLs (above). The collector stops on a confirmed empty account balance and treats a one-off 40200 as a retryable row.</li>
<li>2026-11-02, later the same day: analysis a5. A review of the first November build found about one extracted name in ten was not a business (an address, a star rating, a line of advice such as "Verify Licensing &amp; Insurance", or three names bundled in one bold run; about one in five on the Gemini lane). The extractor now filters those as described under "Answers with an extracted name"; the word list it uses is published as <code>data/generic-words.txt</code>. Naming rates moved with it (Claude 76 to 69 of 100, Gemini 100 to 99). July is recomputed under the same rule.</li>
<li>2026-11-02, evening: analysis a6, with the redesign. Two independent checks of the rebuilt pages found strings listed as businesses that were none: a licence type ("Certified Roofing Contractor (CCC)" on the DeLand roofer page), bare directory and review-site names (Yelp, Zillow, Justia, Super Lawyers), regulators and associations (the Florida DBPR, the FICPA, the Florida Bar), label words ("Doctors", "Referrals"), city names and check-list headings. The filters named under "Answers with an extracted name" drop them: 160 of 2,116 extracted names in November (about one in 13) and 71 of 1,303 in July (one in 18). Numbered headings ("### 1. Name", including "Top for X: Name") are now read as list items. Each question's page groups the businesses by how many engines named them and merges spellings as described under "One business, several spellings". Rates moved with it: Claude 69 to 64 of 100 (five answers whose only extracted strings were a regulator, a directory or a label now count as none), Gemini 99 to 100 (a numbered-heading answer now counts), ChatGPT and Perplexity unchanged at 100 and 100; July unchanged at 94 and 100. The same check found that "named a business" overstated what the count measures, so every such label now reads "answers with an extracted name". Dates on the site are the collection day in Florida time (previously the UTC day; no date changed).</li>
</ul>
<h2>Related work</h2>
<p>Three public indexes measure AI citations at the global, category level and are worth reading alongside this one: <a href="https://promvia.app/ai-source-index">Promvia's AI Source Index</a> (weekly, 40 buyer questions, every row published), <a href="https://brandinsightai.com/sources">BrandInsightAI's AI Source Bias Index</a> and <a href="https://www.heyamos.com/ai-citation-index">HeyAmos's AI Sources Index</a>. This index is the local complement: fixed cities, fixed verticals, named businesses, monthly, from July 2026.</p>
<h2>Corrections</h2>
<p>If a name was extracted wrongly, a domain is misclassified, or a business believes an engine's answer about it is inaccurate, write through the <a href="{CONTACT_URL}">EVOIX contact page</a>. Extraction and classification errors are fixed in the next build and logged above. Engine answers themselves are reproduced as returned and are not edited.</p>
<h2>The 100 prompts</h2>
{prompts_html}
</div>
"""
    write("method/index.html", shell(ix, "Local AI Sources method, instrument and changelog",
                                     "How the Local AI Sources panel is collected and counted: 100 fixed prompts, four AI engines, pinned models, published rows, measured noise floor.", "/method/", body, ix.latest_date))
    ix.pages.append(("/method/", ix.latest_date))


def build_misc(ix):
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"<url><loc>{SITE}{p}</loc><lastmod>{lm}</lastmod></url>\n" for p, lm in ix.pages) + "</urlset>\n"
    write("sitemap.xml", sm)
    latest = ix.latest
    llms = f"""# {SITE_NAME}

> A public monthly record of which businesses and which source domains AI engines (ChatGPT, Perplexity, Claude, Gemini) cite when asked "Who is the best {{vertical}} in {{city}}, Florida?" for 10 service verticals in 10 Central Florida cities. Published by EVOIX LLC, DeLand, Florida. Author Stephane Morera. Data CC BY 4.0.

Latest run: {month_label(latest)}, collected {ix.latest_date}. Panel v1, 100 fixed prompts, one answer per prompt per engine per month so far, every row published.

## Pages
- [Home]({SITE}/): find the page for a city and trade; every line counts the engines whose answer carried an extracted name
- [Method]({SITE}/method/): panel, instrument, what is counted, changelog, noise floor
- [Data]({SITE}/data/): JSON and CSV downloads per month
- [Engines]({SITE}/engines/): per-engine pages
- [Sources]({SITE}/domains/): every cited domain with counts
- [Months]({SITE}/runs/): every monthly run with the per-engine figures

## Origin
- [Central Florida AI Citation Study]({STUDY_URL}): the July 2026 study that became month zero
"""
    write("llms.txt", llms)
    write("404.html", shell(ix, "Page not found", "This page does not exist on Local AI Sources.", "/404.html",
                            lead("Not here", q="This page is not in the book.") + '<div class="prose"><p>Try the <a href="/">home page</a>, the <a href="/runs/">monthly runs</a> or the <a href="/domains/">source list</a>.</p></div>', ix.latest_date))


def write_paper_plate():
    """assets/plates/paper.svg: the 32x160 paper crop mirror-tiled 2x2 so the seams vanish. site.css layers it twice
    at different scales over the paper colour. The PNG is the single source; the SVG is regenerated every build."""
    png = os.path.join(ROOT, "assets", "plates", "paper.png")
    b64 = base64.b64encode(open(png, "rb").read()).decode()
    img = f'<image href="data:image/png;base64,{b64}" width="32" height="160" opacity="0.42"/>'
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="320">'
           f'{img}<g transform="translate(64,0) scale(-1,1)">{img}</g>'
           f'<g transform="translate(0,320) scale(1,-1)">{img}</g>'
           f'<g transform="translate(64,320) scale(-1,-1)">{img}</g></svg>')
    write("assets/plates/paper.svg", svg)


def report_orphans(ix):
    """Pages on disk that this build did not write. Printed, never deleted: a page AI engines cite stays live."""
    built = {p for p, _ in ix.pages}
    orphans = []
    for d in ("domains", "engines", "runs"):
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.isdir(os.path.join(base, name)) and f"/{d}/{name}/" not in built:
                orphans.append(f"/{d}/{name}/")
    if orphans:
        print(f"{len(orphans)} page(s) on disk were not built this run (left in place): " + ", ".join(orphans[:10]))


def main():
    if not os.path.exists(os.path.join(ROOT, "assets", "site.css")):
        sys.exit("assets/site.css is missing; every page links it")
    panel = load_panel()
    runs = load_runs()
    if not runs:
        sys.exit("no runs found under data/runs/")
    ix = Index(panel, runs, load_variance())
    build_home(ix)
    build_questions(ix)
    build_domains(ix)
    build_engines(ix)
    build_runs(ix)
    build_data(ix)
    build_method(ix)
    build_misc(ix)
    write_paper_plate()
    report_orphans(ix)
    print(f"built {len(ix.pages)} pages from runs {', '.join(ix.run_ids)}")


if __name__ == "__main__":
    main()
