#!/usr/bin/env python3
"""One-click LVD full pipeline: generate -> annotate -> summarize."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_step(name: str, cmd: list[str]) -> None:
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"ERROR: {name} failed with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"OK: {name} completed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full LVD pipeline.")
    parser.add_argument("--models", default="deepseek_r1", help="Comma-separated model keys.")
    parser.add_argument("--conditions", default="D,LC,CD", help="Comma-separated conditions.")
    parser.add_argument("--judge-model", default="deepseek_judge", help="Judge model key.")
    parser.add_argument("--run-id", default="", help="Optional run ID.")
    parser.add_argument("--skip-generate", action="store_true", help="Skip generation step.")
    parser.add_argument("--skip-annotate", action="store_true", help="Skip annotation step.")
    parser.add_argument("--skip-summarize", action="store_true", help="Skip summarization step.")
    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path("outputs") / "runs" / run_id

    # Step 1: Generate
    if not args.skip_generate:
        run_step(
            "Generation",
            [
                sys.executable, "-m", "bench.runner",
                "--config", "config/pilot.yaml",
                "--models", args.models,
                "--conditions", args.conditions,
                "--run-id", run_id,
            ],
        )
    else:
        print(f"Skipping generation, using existing run_dir={run_dir}")

    # Step 2: Auto-annotate
    if not args.skip_annotate:
        gen_store = str(run_dir / "store.jsonl")
        prompt_store = str(run_dir / "prompts.jsonl")
        anno_output = str(run_dir / "annotations_auto.jsonl")

        if not Path(gen_store).exists():
            print(f"ERROR: generation store not found: {gen_store}")
            sys.exit(1)
        if not Path(prompt_store).exists():
            print(f"ERROR: prompt store not found: {prompt_store}")
            sys.exit(1)

        run_step(
            "Auto-Annotation",
            [
                sys.executable, "-m", "bench.auto_parser",
                "--generation-store", gen_store,
                "--prompt-store", prompt_store,
                "--output", anno_output,
                "--model-key", args.judge_model,
            ],
        )
    else:
        print("Skipping annotation")

    # Step 3: Summarize
    if not args.skip_summarize:
        gen_store = str(run_dir / "store.jsonl")
        anno_output = str(run_dir / "annotations_auto.jsonl")
        summary_md = str(run_dir / "summary_report.md")
        summary_json = str(run_dir / "summary_stats.json")

        if not Path(anno_output).exists():
            print(f"ERROR: annotations not found: {anno_output}")
            sys.exit(1)

        run_step(
            "Summarization",
            [
                sys.executable, "-m", "bench.auto_summarizer",
                "--annotations", anno_output,
                "--generations", gen_store,
                "--output-md", summary_md,
                "--output-json", summary_json,
            ],
        )
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"Run ID:     {run_id}")
        print(f"Generations: {gen_store}")
        print(f"Annotations: {anno_output}")
        print(f"Report MD:   {summary_md}")
        print(f"Report JSON: {summary_json}")
    else:
        print("Skipping summarization")


if __name__ == "__main__":
    main()
