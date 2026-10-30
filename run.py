"""Step 1: collect model responses for every coding task (resumable)."""
import argparse
import concurrent.futures as cf
import json
import threading
import time
from pathlib import Path

from slopbench.llm import chat
from slopbench.prompts import SYSTEM, all_tasks

MODELS = [
    "openai/gpt-oss-20b",
    "mistralai/mistral-large-4-1t-a52b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3.5-bolt-e4b",
    "minimaxai/minimax-m3.1-flash",
    "meta/muse-glimmer-30b",
    "stepfun-ai/step-5-preview",
]

OUT = Path(__file__).parent / "results" / "responses.jsonl"
_write_lock = threading.Lock()


def done_keys():
    if not OUT.exists():
        return set()
    return {(r["model"], r["id"], r["sample"]) for r in map(json.loads, OUT.open()) if not r["error"] and r["response"].strip()}


def run_one(model, task, sample):
    t0 = time.time()
    try:
        text = chat(model, [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": task["prompt"]}])
        err = None
    except Exception as e:  # noqa: BLE001
        text, err = "", str(e)[:200]
    rec = {**task, "model": model, "sample": sample, "response": text,
           "error": err, "latency_s": round(time.time() - t0, 1)}
    with _write_lock, OUT.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--workers-per-model", type=int, default=3)
    ap.add_argument("--models", nargs="*", default=MODELS)
    args = ap.parse_args()

    OUT.parent.mkdir(exist_ok=True)
    skip = done_keys()
    jobs = [(m, t, s) for m in args.models for t in all_tasks()
            for s in range(args.samples) if (m, t["id"], s) not in skip]
    print(f"{len(jobs)} jobs to run ({len(skip)} already done)", flush=True)

    # One pool per model so a slow/rate-limited model doesn't starve the others.
    pools = {m: cf.ThreadPoolExecutor(args.workers_per_model) for m in args.models}
    futures = [pools[m].submit(run_one, m, t, s) for m, t, s in jobs]
    for i, fut in enumerate(cf.as_completed(futures), 1):
        rec = fut.result()
        if i % 25 == 0 or rec["error"]:
            print(f"[{i}/{len(jobs)}] {rec['model']} {rec['id']} "
                  f"{'ERR ' + rec['error'] if rec['error'] else 'ok'}", flush=True)
    for p in pools.values():
        p.shutdown()


if __name__ == "__main__":
    main()
