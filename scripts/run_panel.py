#!/usr/bin/env python3
"""Collect one monthly run of the Local AI Sources panel.

Calls DataForSEO ai_optimization/{engine}/llm_responses/live through the house
helper dfs.sh (which holds the credentials; this script never reads them).

  python3 scripts/run_panel.py --run-id 2026-11                 # the 100 prompts, four engines
  python3 scripts/run_panel.py --run-id 2026-11 --variance      # the 10-prompt N=3 same-day subsample
  python3 scripts/run_panel.py --run-id 2026-11 --limit 4 --engines chat_gpt   # smoke test
  python3 scripts/run_panel.py --run-id 2026-11 --dry-run       # print the plan, call nothing

Resumable: existing (query_id, engine, sample) rows without an error are skipped.
Cost cap: submissions stop when the recorded cost in the output file reaches --cost-cap.
Output: data/runs/{run_id}.jsonl (or {run_id}-variance.jsonl), one row per call.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DFS_DEFAULT = os.path.expanduser("~/Desktop/EVOIX/scripts/dfs.sh")
MODELS = {
    "chat_gpt": "gpt-5.4-2026-03-05",
    "perplexity": "sonar-pro",
    "claude": "claude-sonnet-5",
    # Requested gemini-3.5-flash on 2026-11-02; DataForSEO served gemini-3.6-flash on all 100 rows while
    # listing both names. Pinned to the served name so the instrument is what the data says it is.
    "gemini": "gemini-3.6-flash",
}
MAX_TOKENS = 1500


class PaymentRequired(RuntimeError):
    """DataForSEO 40200: the account balance is empty. Nothing else will succeed, so the run stops."""


def load_panel():
    return json.load(open(os.path.join(ROOT, "data", "panel-v1.json")))


def variance_prompts(panel, run_id):
    """One prompt per vertical; the city rotates with the month so the subsample walks the panel."""
    month = int(run_id.split("-")[1])
    cities = panel["cities"]
    out = []
    for vi, v in enumerate(panel["verticals"]):
        c = cities[(month + vi) % len(cities)]
        for p in panel["prompts"]:
            if p["vertical"] == v and p["city"] == c:
                out.append(p)
                break
    return out


def extract(task):
    res = (task.get("result") or [None])[0]
    if not res:
        return None
    text, sources = [], []
    for it in res.get("items") or []:
        for sec in it.get("sections") or []:
            if sec.get("text"):
                text.append(sec["text"])
            for ann in sec.get("annotations") or []:
                if ann.get("url"):
                    sources.append({"title": ann.get("title"), "url": ann["url"]})
    return {
        "answer": "\n".join(text),
        "sources": sources,
        "money_spent": res.get("money_spent"),
        "datetime": res.get("datetime"),
        "model_name": res.get("model_name"),
        "fan_out_queries": res.get("fan_out_queries"),
    }


def balance(dfs):
    """Account balance in dollars from appendix/user_data (a free call), or None if unreadable."""
    try:
        out = subprocess.run([dfs, "appendix/user_data", ""], capture_output=True, text=True, timeout=60)
        return float(json.loads(out.stdout)["tasks"][0]["result"][0]["money"]["balance"])
    except Exception:  # noqa: BLE001
        return None


REDIRECT_HOST = "vertexaisearch.cloud.google.com"


def resolve_sources(sources, workers=12):
    """Gemini grounding returns every citation as a vertexaisearch.cloud.google.com redirect link whose
    title is the real domain. Follow each distinct link once (302 Location) and keep the real URL as
    `url`, the redirect as `redirect_url`. A link that fails to resolve falls back to https://{title}/
    when the title is a bare domain, and is flagged `resolved: false` either way."""
    import urllib.request
    from urllib.parse import urlparse

    links = sorted({s["url"] for s in sources if urlparse(s["url"]).netloc == REDIRECT_HOST})
    if not links:
        return sources

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
            return None

    opener = urllib.request.build_opener(NoRedirect)

    def head(link):
        try:
            opener.open(urllib.request.Request(link, method="HEAD"), timeout=20)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                return link, e.headers["Location"]
        except Exception:  # noqa: BLE001
            pass
        return link, None

    resolved = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for link, target in pool.map(head, links):
            resolved[link] = target
    out = []
    for s in sources:
        if urlparse(s["url"]).netloc != REDIRECT_HOST:
            out.append(s)
            continue
        target = resolved.get(s["url"])
        title = (s.get("title") or "").strip().lower()
        if target:
            out.append({**s, "url": target, "redirect_url": s["url"], "resolved": True})
        elif title and "." in title and " " not in title and "/" not in title:
            out.append({**s, "url": f"https://{title}/", "redirect_url": s["url"], "resolved": False})
        else:
            out.append({**s, "redirect_url": s["url"], "resolved": False})
    return out


def call(dfs, engine, prompt):
    body = json.dumps([{"user_prompt": prompt, "model_name": MODELS[engine], "web_search": True,
                        "max_output_tokens": MAX_TOKENS}])
    out = subprocess.run([dfs, f"ai_optimization/{engine}/llm_responses/live", body],
                         capture_output=True, text=True, timeout=660)
    if out.returncode != 0:
        raise RuntimeError(f"dfs.sh exit {out.returncode}: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    if data.get("status_code") == 40200:
        raise PaymentRequired("40200 Payment Required (account balance empty)")
    if not data.get("tasks"):
        return {"task_id": None, "status": data.get("status_message"), "cost": 0,
                "error": f"{data.get('status_code')} {data.get('status_message')} (no tasks in response)"}
    task = data["tasks"][0]
    row = {"task_id": task.get("id"), "status": task.get("status_message"), "cost": task.get("cost")}
    if task.get("status_code") == 40200:
        raise PaymentRequired("40200 Payment Required (account balance empty)")
    if task.get("status_code") != 20000:
        row["error"] = f"{task.get('status_code')} {task.get('status_message')}"
        return row
    ex = extract(task)
    if not ex or not ex["answer"]:
        row["error"] = "empty result"
        return row
    if engine == "gemini":
        ex["sources"] = resolve_sources(ex["sources"])
    row.update(ex)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=time.strftime("%Y-%m"))
    ap.add_argument("--engines", default=",".join(MODELS))
    ap.add_argument("--limit", type=int, default=None, help="first N prompts only (smoke test)")
    ap.add_argument("--variance", action="store_true", help="run the 10-prompt N=3 subsample instead of the panel")
    ap.add_argument("--samples", type=int, default=3, help="samples per prompt in variance mode")
    ap.add_argument("--cost-cap", type=float, default=20.0)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--dfs", default=DFS_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resolve-existing", action="store_true",
                    help="rewrite the run file in place, resolving Gemini redirect links in rows collected before the resolver existed")
    a = ap.parse_args()

    if a.resolve_existing:
        path = os.path.join(ROOT, "data", "runs", f"{a.run_id}{'-variance' if a.variance else ''}.jsonl")
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        n_rows = n_links = n_fail = 0
        for r in rows:
            if r.get("sources") and any(s["url"].startswith(f"https://{REDIRECT_HOST}/") for s in r["sources"]):
                r["sources"] = resolve_sources(r["sources"])
                n_rows += 1
                n_links += sum(1 for s in r["sources"] if "redirect_url" in s)
                n_fail += sum(1 for s in r["sources"] if s.get("resolved") is False)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
        print(f"resolved redirects in {n_rows} rows, {n_links} source entries, {n_fail} fell back to the title domain; {path}")
        return

    panel = load_panel()
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    for e in engines:
        if e not in MODELS:
            sys.exit(f"unknown engine {e}")
    prompts = variance_prompts(panel, a.run_id) if a.variance else panel["prompts"]
    if a.limit:
        prompts = prompts[:a.limit]
    samples = range(1, a.samples + 1) if a.variance else [1]
    out_path = os.path.join(ROOT, "data", "runs", f"{a.run_id}{'-variance' if a.variance else ''}.jsonl")

    done = set()
    spent = 0.0
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            spent += float(r.get("cost") or 0)
            if not r.get("error"):
                done.add((r["query_id"], r["engine"], r.get("sample", 1)))

    plan = [(p, e, s) for p in prompts for e in engines for s in samples if (p["query_id"], e, s) not in done]
    print(f"run {a.run_id}{' variance' if a.variance else ''}: {len(prompts)} prompts x {len(engines)} engines x {len(samples)} sample(s); "
          f"{len(done)} done, {len(plan)} to do, ${spent:.2f} already recorded, cap ${a.cost_cap:.2f}", flush=True)
    if a.dry_run:
        for p, e, s in plan[:12]:
            print(f"  {e:10} s{s} {p['prompt']}")
        if len(plan) > 12:
            print(f"  ... {len(plan) - 12} more")
        return
    if not os.path.exists(a.dfs):
        sys.exit(f"dfs helper not found at {a.dfs}")

    if spent >= a.cost_cap:
        sys.exit(f"recorded cost ${spent:.2f} already meets the cap ${a.cost_cap:.2f}; raise --cost-cap to continue")

    lock = Lock()
    state = {"stop": False, "spent": spent, "ok": 0, "err": 0}

    def work(item):
        """Runs in a worker. The cap is checked before the call and the spend is added, under the
        lock, by the worker that receives the result, so the flag flips before any queued worker starts."""
        p, e, s = item
        with lock:
            if state["stop"]:
                return None
        row = {"run_id": a.run_id, "panel_version": panel["panel_version"], "query_id": p["query_id"],
               "vertical": p["vertical"], "city": p["city"], "prompt": p["prompt"], "engine": e,
               "model_requested": MODELS[e], "sample": s,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try:
            row.update(call(a.dfs, e, p["prompt"]))
        except PaymentRequired as ex:
            # 40200 also arrives as a one-off on a single call with money in the account (seen 2026-11-02
            # on a Claude call at a $49 balance), so the balance decides: empty = stop, otherwise a
            # transient row error that the next resume retries.
            bal = balance(a.dfs)
            if bal is None or bal > 0.5:
                row["error"] = f"{ex} transient, balance {bal}"
            else:
                row["error"] = str(ex)
                with lock:
                    if not state["stop"]:
                        state["stop"] = True
                        print(f"DataForSEO balance empty (40200, balance {bal}); no further submissions. Top up and rerun the same command to resume.", flush=True)
        except Exception as ex:  # noqa: BLE001
            row["error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
        with lock:
            state["spent"] += float(row.get("cost") or 0)
            if state["spent"] >= a.cost_cap and not state["stop"]:
                state["stop"] = True
                print(f"cost cap ${a.cost_cap:.2f} reached at ${state['spent']:.2f}; no further submissions", flush=True)
        return row

    with open(out_path, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        futures = [pool.submit(work, it) for it in plan]
        for fut in as_completed(futures):
            row = fut.result()
            if row is None:
                continue
            with lock:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                if row.get("error"):
                    state["err"] += 1
                else:
                    state["ok"] += 1
                print(f"{row['engine']:10} s{row['sample']} {row['query_id']:45} "
                      f"{'ERR ' + row['error'][:60] if row.get('error') else str(len(row.get('sources') or [])) + ' sources'}  "
                      f"${float(row.get('cost') or 0):.4f}  total ${state['spent']:.2f}", flush=True)
    print(f"done: {state['ok']} ok, {state['err']} errors, recorded cost ${state['spent']:.2f}, file {out_path}")


if __name__ == "__main__":
    main()
