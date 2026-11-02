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
    "gemini": "gemini-3.5-flash",
}
MAX_TOKENS = 1500


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


def call(dfs, engine, prompt):
    body = json.dumps([{"user_prompt": prompt, "model_name": MODELS[engine], "web_search": True,
                        "max_output_tokens": MAX_TOKENS}])
    out = subprocess.run([dfs, f"ai_optimization/{engine}/llm_responses/live", body],
                         capture_output=True, text=True, timeout=660)
    if out.returncode != 0:
        raise RuntimeError(f"dfs.sh exit {out.returncode}: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    task = data["tasks"][0]
    row = {"task_id": task.get("id"), "status": task.get("status_message"), "cost": task.get("cost")}
    if task.get("status_code") != 20000:
        row["error"] = f"{task.get('status_code')} {task.get('status_message')}"
        return row
    ex = extract(task)
    if not ex or not ex["answer"]:
        row["error"] = "empty result"
        return row
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
    a = ap.parse_args()

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

    lock = Lock()
    stop = {"flag": False}

    def work(item):
        p, e, s = item
        if stop["flag"]:
            return None
        row = {"run_id": a.run_id, "panel_version": panel["panel_version"], "query_id": p["query_id"],
               "vertical": p["vertical"], "city": p["city"], "prompt": p["prompt"], "engine": e,
               "model_requested": MODELS[e], "sample": s,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try:
            row.update(call(a.dfs, e, p["prompt"]))
        except Exception as ex:  # noqa: BLE001
            row["error"] = f"{type(ex).__name__}: {str(ex)[:200]}"
        return row

    n_ok = n_err = 0
    with open(out_path, "a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        futures = [pool.submit(work, it) for it in plan]
        for fut in as_completed(futures):
            row = fut.result()
            if row is None:
                continue
            with lock:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                spent += float(row.get("cost") or 0)
                if row.get("error"):
                    n_err += 1
                else:
                    n_ok += 1
                print(f"{row['engine']:10} s{row['sample']} {row['query_id']:45} "
                      f"{'ERR ' + row['error'][:60] if row.get('error') else str(len(row.get('sources') or [])) + ' sources'}  "
                      f"${float(row.get('cost') or 0):.4f}  total ${spent:.2f}", flush=True)
                if spent >= a.cost_cap and not stop["flag"]:
                    stop["flag"] = True
                    print(f"cost cap ${a.cost_cap:.2f} reached; no further submissions", flush=True)
    print(f"done: {n_ok} ok, {n_err} errors, recorded cost ${spent:.2f}, file {out_path}")


if __name__ == "__main__":
    main()
