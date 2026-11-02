# Local AI Sources

A public monthly record of which businesses and which source domains AI engines cite when asked "Who is the best {vertical} in {city}, Florida?" for 10 service verticals across 10 Central Florida cities. Published by EVOIX LLC, DeLand, Florida. Live at https://localaisources.com/.

Static site, no framework. GitHub Pages serves the repository root.

- `data/panel-v1.json` the 100 frozen prompts (a prompt is never edited, only replaced under a new panel version)
- `data/runs/YYYY-MM.jsonl` one row per prompt per engine per month, full answer and every cited URL
- `scripts/run_panel.py` collects a month (DataForSEO `llm_responses`, web search on)
- `scripts/analysis.py` reads the rows and computes every figure (name extraction, per-engine stats, cross-engine grouping, noise floor)
- `scripts/build.py` turns the figures into pages; run it after each collection and commit the output (`python3 -m unittest scripts/test_extract.py` runs the extraction tests)
- `scripts/classify.py` the directory and aggregator list used to split own-site citations from the rest
- `assets/` the stylesheet, the self-hosted fonts (League Gothic, Bebas Neue, Barlow Condensed, all SIL Open Font License) and the paper ground (`plates/paper.png`, tiled by the generated `plates/paper.svg`)

Method, instrument and changelog: https://localaisources.com/method/
Data license CC BY 4.0, code MIT (see LICENSE).

Experiment record: EVOIX aeo-lab EXP-015. Do not delete the Search Console verification file or the IndexNow key file once they are added at the root.
