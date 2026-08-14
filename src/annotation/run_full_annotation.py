"""
run_full_annotation.py — Full-dataset annotation run (Parmida, Day 6)

Runs the locked model route (src/annotation/model_routes.py's
LOCKED_ROUTE_NAME) over every eligible record (data/interim/{opinion_main,
opinion_limited,opinion_untimed}.parquet — the apply_eligibility.py output,
233,006 records as of 2026-08-14, see docs/decision_log.md) with real
concurrency, since sequential calls at the Pilot's observed ~4.2s median
latency would take ~272 hours for one pass.

Two independent safety Gates (docs/pre_analysis_decision_table_v1.md) must
both pass before any annotation happens:
  1. Model lock — get_locked_route() raises RuntimeError until
     model_routes.LOCKED_ROUTE_NAME is set (done 2026-08-14).
  2. Cost cap — --confirm-cost-cap must equal APPROVED_COST_CAP_USD below,
     which itself must be backed by a dated docs/decision_log.md entry
     (done 2026-08-14, $100).

Team-parallel by design (docs/decision_log.md 2026-08-14): --shard-id/
--num-shards lets several teammates each own a disjoint slice of the
eligible records and run independently (their own machine, their own API
keys) — sharding is a deterministic hash of content_id, so re-running the
same --shard-id always gets the same slice. --workers controls in-process
concurrency (a ThreadPoolExecutor — llm_client.annotate() is a blocking
requests/SDK call, not async) on top of that.

--targets controls how many of the 3 primary Targets (schema.
PRIMARY_TARGET_IDS) each record is scored against for stance — 1 (cheap,
fast, only the first target) up to 3 (full per-Target stance coverage, 3x
the cost/time). Default is 1 so the team can start now and expand later
without touching code (see decision_log.md's reasoning).

Resumable: output is one JSONL file per shard
(outputs/full_annotation/shard_{id}of{n}.jsonl); on startup this script
reads its own shard file (if it exists) and skips any (content_id,
target_id) pair already present, so a killed/interrupted run picks up where
it left off for free — no separate checkpoint format needed.

Usage:
    # solo, 1 target, 20 concurrent workers, whole dataset as one shard
    python src/annotation/run_full_annotation.py --confirm-cost-cap 100.0

    # teammate 2 of 5, running their own slice in parallel with the others
    python src/annotation/run_full_annotation.py --confirm-cost-cap 100.0 --shard-id 1 --num-shards 5

    # once the team has time budget to spare: full 3-target stance coverage
    python src/annotation/run_full_annotation.py --confirm-cost-cap 100.0 --targets T01,T02,T03
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.annotation.decision_gate import require_decision_log_gate  # noqa: E402
from src.annotation.llm_client import AnnotationCache, annotate  # noqa: E402
from src.annotation.model_routes import get_locked_route  # noqa: E402
from src.annotation.schema import PRIMARY_TARGET_IDS  # noqa: E402

ELIGIBLE_PARQUETS = [
    ROOT / "data" / "interim" / "opinion_main.parquet",
    ROOT / "data" / "interim" / "opinion_limited.parquet",
    ROOT / "data" / "interim" / "opinion_untimed.parquet",
]
OUTPUT_DIR = ROOT / "outputs" / "full_annotation"
CACHE_SAVE_EVERY = 200  # rows between periodic AnnotationCache.save() flushes
PROGRESS_EVERY = 100

DECISION_LOG_PATH = ROOT / "docs" / "decision_log.md"

# Approved cost cap (USD) for the Full run, per docs/pre_analysis_decision_table_v1.md
# row "سقف هزینه و زمان اجرا". Must stay None — and this script must keep
# refusing to run — until a numeric cap has been decided from Pilot data and
# written down as a dated entry in docs/decision_log.md. When that happens,
# set this to the approved number and reference the decision_log.md date in a
# comment here, the same way LOCKED_ROUTE_NAME is documented in model_routes.py.
APPROVED_COST_CAP_USD: float | None = 100.0
# Approved 2026-08-14 — see docs/decision_log.md's dated entry for the
# Pilot-based math this is derived from (locked route's cost/1000 from
# evaluate_sentiment_accuracy.py's n=300 run, times eligible record count
# times up to 3 primary targets, plus margin).


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run LLM annotation over the FULL dataset using the locked model route. "
            "Refuses to run unless a model is locked (model_routes.LOCKED_ROUTE_NAME) "
            "and the caller explicitly confirms the cost cap approved in "
            "docs/decision_log.md."
        )
    )
    parser.add_argument(
        "--confirm-cost-cap",
        type=float,
        required=True,
        metavar="USD",
        help=(
            "The USD cost cap approved for this Full run, as written in a dated "
            "docs/decision_log.md entry. Must match APPROVED_COST_CAP_USD exactly "
            "in this script — this is a deliberate 'type it out' confirmation so a "
            "full, real-money run can't be triggered by accident (e.g. by a default "
            "flag value, or by copy-pasting a command without reading it)."
        ),
    )
    parser.add_argument(
        "--shard-id", type=int, default=0,
        help="This process's shard index (0-based). Combine with --num-shards "
             "so teammates can each run a disjoint slice in parallel.",
    )
    parser.add_argument(
        "--num-shards", type=int, default=1,
        help="Total number of shards the eligible dataset is split into. "
             "Sharding is a deterministic hash of content_id, so the same "
             "--shard-id always gets the same records across re-runs/people.",
    )
    parser.add_argument(
        "--workers", type=int, default=20,
        help="In-process concurrent threads (llm_client.annotate() is a "
             "blocking call, so this is a ThreadPoolExecutor, not asyncio). "
             "Start conservative (~15-20) — too high risks tripping the "
             "route's own rate limits, which just burns retries/time.",
    )
    parser.add_argument(
        "--targets", type=str, default="T01",
        help="Comma-separated Target IDs to score stance against, e.g. "
             "'T01' (default, cheapest) or 'T01,T02,T03' (full primary-"
             "Target coverage, ~3x the cost/time). Must be a subset of "
             f"PRIMARY_TARGET_IDS ({PRIMARY_TARGET_IDS}).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only process the first N tasks of this shard (smoke-testing).",
    )
    parser.add_argument(
        "--stratify-cap", type=int, default=None,
        help="Rate-limit-forced scope reduction (docs/decision_log.md 2026-08-14): "
             "cap each (platform, project_week) cell at this many records instead "
             "of annotating all eligible records. Omit for the full eligible set.",
    )
    return parser.parse_args()


def check_cost_cap(confirmed_cap: float) -> None:
    """Second Gate: refuse to run unless the caller's --confirm-cost-cap
    matches the cap actually approved and logged in docs/decision_log.md.
    Also prints a (non-fatal) warning if APPROVED_COST_CAP_USD, once set,
    can't actually be found anywhere in docs/decision_log.md — see
    decision_gate.require_decision_log_gate.
    """
    require_decision_log_gate(
        APPROVED_COST_CAP_USD,
        gate_name="APPROVED_COST_CAP_USD",
        decision_log_path=DECISION_LOG_PATH,
        missing_message=(
            "هنوز سقف هزینه‌ای برای Full run تأیید نشده — طبق "
            "docs/pre_analysis_decision_table_v1.md ('سقف هزینه و زمان اجرا'), "
            "اول باید سقف عددی بر اساس Pilot در docs/decision_log.md ثبت شود، "
            "بعد APPROVED_COST_CAP_USD در این فایل مقداردهی شود."
        ),
    )
    if confirmed_cap != APPROVED_COST_CAP_USD:
        raise ValueError(
            f"--confirm-cost-cap={confirmed_cap} با سقف تأییدشده "
            f"(APPROVED_COST_CAP_USD={APPROVED_COST_CAP_USD}) مطابقت ندارد — "
            "برای جلوگیری از اجرای تصادفی روی کل دیتاست، این دو باید دقیقاً برابر باشند."
        )


def load_eligible_records() -> pd.DataFrame:
    """Reads the three apply_eligibility.py output buckets that get
    annotated (opinion_main/opinion_limited/opinion_untimed — context_only/
    audit_only/quarantine never do, per docs/checklist.md §13). Returns one
    row per record with just the columns this script needs, deduplicated by
    content_id (the three buckets are mutually exclusive by construction,
    but this guards against re-running apply_eligibility.py with overlap)."""
    frames = []
    for path in ELIGIBLE_PARQUETS:
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found — run src/preprocessing/apply_eligibility.py first."
            )
        df = pd.read_parquet(path, columns=["platform_content_id", "text_raw", "platform", "dataset_target", "project_week"])
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(columns={"platform_content_id": "content_id", "text_raw": "text"})
    combined = combined.dropna(subset=["content_id", "text"])
    combined = combined[combined["text"].str.strip() != ""]
    combined = combined.drop_duplicates(subset=["content_id"])
    return combined


def stratified_subsample(records: pd.DataFrame, cap_per_cell: int, seed: int) -> pd.DataFrame:
    """docs/decision_log.md 2026-08-14 (rate-limit-forced scope reduction):
    at most `cap_per_cell` records per (platform, project_week) cell, so
    every cell that has enough data clears the checklist.md §22 n>=30
    low-sample threshold with real margin, instead of an arbitrary first-N
    slice that could silently empty out whole weeks/platforms. Cells with
    fewer than cap_per_cell available records keep everything they have
    (reported, not silently backfilled from elsewhere — a real data-gap week
    should still look like a data-gap week, not get papered over).
    opinion_untimed rows (project_week is null/'OUT') are kept in full —
    there are only 6 as of 2026-08-14, and they were never going to be part
    of the weekly-stratified cells anyway."""
    untimed = records[records["project_week"].isna() | (records["project_week"] == "OUT")]
    timed = records[~records.index.isin(untimed.index)]

    # Plain iteration over a groupby object (not .groupby(...).apply(func)):
    # each `group` here is a real slice of `timed` and keeps every column,
    # including the two grouping columns themselves. .groupby(...).apply()
    # is deliberately NOT used — as of pandas 3.0 (installed here) it drops
    # the grouping columns from what's passed into the lambda by default
    # (the finalized form of a change pandas warned about since 2.2's
    # "operated on the grouping columns" deprecation), which silently made
    # every sampled row's platform/project_week come back null. Found
    # 2026-08-14 when a real run wrote thousands of rows with
    # platform=NaN — see docs/decision_log.md.
    cell_sizes: dict[tuple, int] = {}
    parts = []
    for key, group in timed.groupby(["platform", "project_week"]):
        cell_sizes[key] = len(group)
        take = min(len(group), cap_per_cell)
        parts.append(group.sample(n=take, random_state=seed))
    sampled = pd.concat(parts, ignore_index=True) if parts else timed.iloc[0:0].copy()
    result = pd.concat([sampled, untimed], ignore_index=True)

    n_capped = sum(1 for n in cell_sizes.values() if n > cap_per_cell)
    n_short = sum(1 for n in cell_sizes.values() if 0 < n <= cap_per_cell)
    print(f"Stratified sample: cap={cap_per_cell}/cell — {n_capped} cell(s) capped, "
          f"{n_short} cell(s) kept in full (below cap), {len(untimed)} untimed row(s) kept whole.")
    return result


def assign_shard(content_id: str, num_shards: int) -> int:
    """Deterministic (content_id, num_shards) -> shard index, so the same
    --shard-id always gets the same records across re-runs and across
    different teammates' machines (no coordination needed beyond agreeing
    on --num-shards)."""
    return zlib.crc32(content_id.encode("utf-8")) % num_shards


def load_done_keys(output_path: Path) -> set[tuple[str, str]]:
    """Reads this shard's own output file (if any) and returns the set of
    (content_id, target_id) pairs already SUCCESSFULLY annotated — resume
    support. Only annotation_status=="ok" counts as done (bug fixed
    2026-08-14: this used to count every attempted pair regardless of
    outcome, so a row that failed — e.g. api_failure from a key hitting its
    daily quota — looked "already done" and was never retried on the next
    run; found when 4,954 api_failure rows from an exhausted-quota run
    would otherwise have been skipped forever instead of retried once quota
    reset). A corrupt/partial last line (e.g. process killed mid-write) is
    skipped, not fatal — that row is simply re-annotated. Note: a row can
    appear multiple times in the file across resumed attempts (once
    failed, once ok) — the file itself is not deduplicated, only this
    in-memory set is; downstream consumers should keep the last/best
    attempt per (content_id, target_id)."""
    done: set[tuple[str, str]] = set()
    if not output_path.exists():
        return done
    with output_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("annotation_status") == "ok":
                    done.add((row["content_id"], row["target_id"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def main() -> None:
    args = parse_args()

    # Gate 1: model must be locked (raises RuntimeError otherwise).
    route = get_locked_route()

    # Gate 2: cost cap must be explicitly confirmed and match decision_log.md.
    check_cost_cap(args.confirm_cost_cap)

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    unknown = [t for t in targets if t not in PRIMARY_TARGET_IDS]
    if unknown:
        raise ValueError(f"--targets contains non-primary target(s) {unknown} — must be a subset of {PRIMARY_TARGET_IDS}.")
    if args.shard_id < 0 or args.shard_id >= args.num_shards:
        raise ValueError(f"--shard-id must be in [0, {args.num_shards}).")

    api_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }

    print(f"Route: {route.route_name} ({route.model_name})")
    print(f"Cost cap: ${args.confirm_cost_cap}  |  Targets: {targets}  |  Workers: {args.workers}")
    print(f"Shard: {args.shard_id} of {args.num_shards}")

    records = load_eligible_records()
    if args.stratify_cap:
        records = stratified_subsample(records, args.stratify_cap, seed=1405)
    shard_records = records[records["content_id"].apply(lambda c: assign_shard(c, args.num_shards) == args.shard_id)]
    print(f"Eligible records total: {len(records):,}  |  This shard: {len(shard_records):,}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"shard_{args.shard_id}of{args.num_shards}.jsonl"
    done_keys = load_done_keys(output_path)
    if done_keys:
        print(f"Resuming: {len(done_keys):,} (content_id, target_id) pair(s) already done in {output_path.name}.")

    tasks = [
        (row.content_id, row.text, row.platform, target_id)
        for row in shard_records.itertuples(index=False)
        for target_id in targets
        if (row.content_id, target_id) not in done_keys
    ]
    if args.limit:
        tasks = tasks[: args.limit]
    print(f"Tasks to run this session: {len(tasks):,}")
    if not tasks:
        print("Nothing to do — shard already fully annotated.")
        return

    cache = AnnotationCache()
    output_lock = threading.Lock()
    cache_lock = threading.Lock()
    stop_flag = threading.Event()
    run_id = f"full_annotation_shard{args.shard_id}of{args.num_shards}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    state = {"completed": 0, "cost_usd": 0.0, "failures": 0, "started_at": time.monotonic()}
    state_lock = threading.Lock()

    def worker(task: tuple[str, str, str, str]) -> None:
        content_id, text, platform, target_id = task
        if stop_flag.is_set():
            return
        result = annotate(
            text=text, target_id=target_id, route=route, api_keys=api_keys,
            cache=cache, run_id=run_id, content_id=content_id,
        )
        row = {
            "content_id": content_id,
            "platform": platform,
            "target_id": target_id,
            "sentiment": (result.payload or {}).get("sentiment"),
            "stance": (result.payload or {}).get("stance"),
            "emotion": (result.payload or {}).get("emotion"),
            "content_type": (result.payload or {}).get("content_type"),
            "confidence": result.confidence,
            "reason_code": (result.payload or {}).get("reason_code"),
            "annotation_status": (
                "ok" if result.ok
                else "json_parse_failure" if result.parse_error
                else "validation_failure" if result.validation_error
                else "api_failure"
            ),
            "model_version": result.model_name,
            "prompt_version": result.prompt_version,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "annotated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with output_lock:
            with output_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        with state_lock:
            state["completed"] += 1
            state["cost_usd"] += result.cost_usd or 0.0
            if not result.ok:
                state["failures"] += 1
            completed = state["completed"]
            cost_so_far = state["cost_usd"]

        if cost_so_far > args.confirm_cost_cap:
            if not stop_flag.is_set():
                print(f"\n[STOP] Cost cap ${args.confirm_cost_cap} reached (${cost_so_far:.2f} spent this "
                      f"session) — no new tasks will start. In-flight tasks still finish.")
            stop_flag.set()

        if completed % CACHE_SAVE_EVERY == 0:
            with cache_lock:
                cache.save()

        if completed % PROGRESS_EVERY == 0:
            elapsed = time.monotonic() - state["started_at"]
            rate = completed / elapsed if elapsed > 0 else 0
            remaining = len(tasks) - completed
            eta_min = (remaining / rate / 60) if rate > 0 else float("nan")
            print(f"  [{completed:,}/{len(tasks):,}] cost=${cost_so_far:.2f} "
                  f"failures={state['failures']} rate={rate:.1f}/s eta={eta_min:.0f}min")

    print(f"\nStarting {args.workers} worker(s)...\n")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(worker, t) for t in tasks]
        for _ in as_completed(futures):
            if stop_flag.is_set():
                # Don't cancel in-flight requests (already billed); just stop
                # draining new ones from the queue — as_completed still needs
                # every future resolved before this loop returns.
                pass

    cache.save()  # final flush — guaranteed to run even if the cap was hit mid-run
    print(f"\nDone this session: {state['completed']:,} task(s), "
          f"${state['cost_usd']:.2f} spent, {state['failures']} failure(s).")
    print(f"Output: {output_path}")
    if args.num_shards > 1:
        print(f"Once every shard finishes, merge with: "
              f"cat outputs/full_annotation/shard_*of{args.num_shards}.jsonl > outputs/full_annotation/merged.jsonl")


if __name__ == "__main__":
    main()
