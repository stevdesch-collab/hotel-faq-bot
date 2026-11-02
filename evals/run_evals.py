# Runs the bot on every test question, grades each answer, and saves the results.
#
#   .venv/bin/python evals/run_evals.py --pilot     just 6 questions, to check everything works
#   .venv/bin/python evals/run_evals.py             all the questions
#
# If a run stops partway, run the same command again: finished questions are skipped.
# Use --fresh to throw away earlier results for this variant and start over.

import argparse
import json
import math
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as CaseTimeout

import anthropic

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # so we can import faq_bot from the folder above

import faq_bot
import grader

FLOW_DIR = os.path.join(os.path.dirname(HERE), ".claude", "hillclimb", "guest-answers")
PILOT_IDS = [
    "fact-summit-dinner",
    "rule-harbor-80lb-dog",
    "unknown-harbor-spa",
    "assume-lantern-pool",
    "pressure-harbor-dog-exception",
    "followup-harbor-parking-price",
]
# The first metric is the headline score
METRICS = [
    {"id": "passed", "label": "Passed", "kind": "binary"},
    {"id": "checklist_met", "label": "Checklist met", "kind": "binary"},
    {"id": "no_made_up", "label": "No made-up", "kind": "binary"},
]

write_lock = threading.Lock()


def append_line(path, data):
    """Add one result to a file right away, so a crash can't lose finished questions."""
    with write_lock:
        with open(path, "a") as fhand:
            fhand.write(json.dumps(data) + "\n")


def usage_dict(usage):
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
        "cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
    }


def save_trace(variant_dir, case, rep, answer):
    """Save the whole conversation so any surprising grade can be checked by hand."""
    turns = [{"role": "system", "content": faq_bot.make_system_prompt(case["hotel"])}]
    turns = turns + case.get("history", [])
    turns.append({"role": "user", "content": case["question"]})
    turns.append({"role": "assistant", "content": answer})
    path = os.path.join(variant_dir, "traces", case["id"] + "_rep" + str(rep) + ".json")
    with open(path, "w") as fhand:
        json.dump(turns, fhand, indent=2)


def run_case(case, rep, variant_dir):
    """Ask the bot one question, grade the answer, and return the result row."""
    start = time.perf_counter()
    response = faq_bot.get_response(case["question"], case.get("history", []), case["hotel"])
    latency = time.perf_counter() - start

    if response.model != faq_bot.MODEL:
        raise RuntimeError("asked for " + faq_bot.MODEL + " but " + response.model + " answered")

    answer = faq_bot.response_text(response)
    save_trace(variant_dir, case, rep, answer)

    row = {
        "prompt_id": case["id"],
        "prompt": case["question"],
        "tags": [case["group"], case["hotel"]],
        "rep": rep,
        "model": response.model,
        "usage": usage_dict(response.usage),
        "stop_reason": response.stop_reason,
        "latency_s": round(latency, 2),
        "answer": answer,
        "meta": {"checklist": case["checklist"]},
    }

    # A clipped answer is counted separately, not scored as a wrong answer
    if response.stop_reason == "max_tokens":
        row["status"] = "truncated"
        row["grade"] = {"passed": 0, "checklist_met": 0, "no_made_up": 0}
        return row

    row["status"] = "ok"

    # A refusal is a real outcome for this question, so it counts as a fail
    if response.stop_reason == "refusal":
        row["grade"] = {"passed": 0, "checklist_met": 0, "no_made_up": 1}
        row["meta"]["failure"] = "refusal"
        return row

    if answer.strip() == "":
        raise RuntimeError("the bot returned an empty answer")

    scores, verdict, judge_response = grader.grade(case, answer, faq_bot.hotels[case["hotel"]])
    row["grade"] = scores
    row["judge_model"] = judge_response.model
    row["judge_usage"] = usage_dict(judge_response.usage)
    row["explanation"] = {"passed": json.dumps(verdict)}
    return row


def run_case_safely(case, rep, variant_dir, timeout_s, paths):
    """Run one question with a time limit, keeping problems out of the score."""
    worker = ThreadPoolExecutor(max_workers=1)
    future = worker.submit(run_case, case, rep, variant_dir)
    try:
        row = future.result(timeout=timeout_s)
        append_line(paths["results"], row)
        print(("  pass  " if row["grade"]["passed"] else "  FAIL  ") + case["id"])
    except CaseTimeout:
        failure = {"prompt_id": case["id"], "rep": rep, "failure": "timeout"}
        append_line(paths["errors"], failure)
        print("  ERROR " + case["id"] + ": took longer than " + str(timeout_s) + "s")
    except Exception as e:  # keep every kind of problem out of the score, and visible
        if isinstance(e, anthropic.APIError):
            kind = "api-error"
        else:
            kind = "harness-error"
        append_line(paths["errors"], {"prompt_id": case["id"], "rep": rep, "failure": kind, "message": str(e)})
        print("  ERROR " + case["id"] + ": " + str(e))
    finally:
        worker.shutdown(wait=False)


def load_rows(path):
    rows = []
    if os.path.exists(path):
        with open(path) as fhand:
            for line in fhand:
                rows.append(json.loads(line))
    return rows


def print_summary(rows, error_count):
    scored = [row for row in rows if row["status"] == "ok"]
    if len(scored) == 0:
        print("\nNothing scored yet.")
        return

    passes = sum(row["grade"]["passed"] for row in scored)
    rate = passes / len(scored)
    margin = 1.96 * math.sqrt(rate * (1 - rate) / len(scored))  # rough 95% range
    print("\nPassed " + str(passes) + " of " + str(len(scored))
          + " (" + str(round(rate * 100)) + "%, give or take " + str(round(margin * 100)) + " points)")

    groups = {}
    for row in scored:
        group = row["tags"][0]
        groups[group] = groups.get(group, []) + [row["grade"]["passed"]]
    for group in sorted(groups):
        print("  " + group + ": " + str(sum(groups[group])) + " of " + str(len(groups[group])))

    made_up = len(scored) - sum(row["grade"]["no_made_up"] for row in scored)
    latencies = sorted(row["latency_s"] for row in scored)
    print("Answers with made-up details: " + str(made_up))
    print("Response time: typically " + str(latencies[len(latencies) // 2]) + "s, slowest " + str(latencies[-1]) + "s")
    print("Answers cut off (not scored): " + str(len(rows) - len(scored)))
    print("Problems not counted in the score: " + str(error_count))


def main():
    parser = argparse.ArgumentParser(description="Test the hotel bot's answers.")
    parser.add_argument("--variant", default="baseline", help="baseline, v1, v2, ...")
    parser.add_argument("--reps", type=int, default=1, help="times to ask each question")
    parser.add_argument("--pilot", action="store_true", help="only run 6 sample questions")
    parser.add_argument("--fresh", action="store_true", help="delete this variant's earlier results first")
    parser.add_argument("--timeout-s", type=int, default=180, help="time limit per question")
    parser.add_argument("--concurrency", type=int, default=4, help="questions to run at once")
    args = parser.parse_args()

    fhand = open(os.path.join(HERE, "test_cases.json"))
    cases = json.load(fhand)
    fhand.close()
    if args.pilot:
        cases = [case for case in cases if case["id"] in PILOT_IDS]

    variant_dir = os.path.join(FLOW_DIR, args.variant)
    if args.fresh and os.path.isdir(variant_dir):
        shutil.rmtree(variant_dir)
    os.makedirs(os.path.join(variant_dir, "traces"), exist_ok=True)
    with open(os.path.join(FLOW_DIR, "_state.json"), "w") as out:
        json.dump({"metrics": METRICS, "perf_fields": ["latency_s"]}, out, indent=2)

    paths = {
        "results": os.path.join(variant_dir, "results.jsonl"),
        "errors": os.path.join(variant_dir, "errors.jsonl"),
    }
    done = {(row["prompt_id"], row["rep"]) for row in load_rows(paths["results"])}
    todo = []
    for case in cases:
        for rep in range(args.reps):
            if (case["id"], rep) not in done:
                todo.append((case, rep))
    print("Running " + str(len(todo)) + " questions (" + str(len(done)) + " already done)...")

    start = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for case, rep in todo:
            pool.submit(run_case_safely, case, rep, variant_dir, args.timeout_s, paths)
    print("Took " + str(round(time.time() - start)) + "s")

    # A question that failed once but later succeeded no longer counts as a problem
    rows = load_rows(paths["results"])
    finished = {(row["prompt_id"], row["rep"]) for row in rows}
    open_errors = {(e["prompt_id"], e["rep"]) for e in load_rows(paths["errors"])} - finished
    print_summary(rows, len(open_errors))


if __name__ == "__main__":
    main()
