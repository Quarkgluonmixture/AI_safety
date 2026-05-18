"""CLI runner for pilot prompts, paraphrases, and model generations."""

from __future__ import annotations

import argparse
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bench.schema import Annotation, Generation, Prompt, sha256_json
from bench.stimuli import build_prompts
from bench.store import JSONLStore

if TYPE_CHECKING:
    from bench.api_clients import BaseClient


def main() -> None:
    """Run the pilot pipeline CLI."""
    args = parse_args()
    pilot_config = load_yaml(args.config)
    model_config_path = Path(pilot_config.get("models_config", "config/models.yaml"))
    model_configs = load_yaml(model_config_path).get("models", {})
    selected_models = select_models(model_configs, parse_csv(args.models))
    requested_conditions = parse_csv(args.conditions) or pilot_config.get("conditions") or []
    prompts = load_prompts_from_config(pilot_config, requested_conditions, allow_missing=args.dry_run, override_pilot_path=args.prompts)
    n_paraphrases = int(pilot_config.get("n_paraphrases", 3))
    n_samples = int(pilot_config.get("n_samples_per_prompt", 1))

    if args.dry_run:
        print_dry_run(prompts, selected_models, pilot_config, n_paraphrases, n_samples)
        return

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ensure_outputs_untracked(Path("outputs"))
    run_dir = Path("outputs") / "runs" / run_id
    generation_store = JSONLStore(run_dir / "store.jsonl", key_fields=("prompt_hash", "model", "paraphrase_idx", "sample_idx"))
    prompt_store = JSONLStore(run_dir / "prompts.jsonl", key_fields=("prompt_hash",))
    annotation_store = JSONLStore(
        run_dir / "annotation_templates.jsonl",
        key_fields=("prompt_hash", "generation_id"),
    )
    paraphrase_client = build_paraphrase_client(pilot_config, model_configs, selected_models, n_paraphrases)
    clients: dict[str, BaseClient] = {}

    written = 0
    skipped = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for prompt in prompts:
        # Persist prompt for downstream annotation lookup
        prompt_store.append(prompt.model_dump(mode="json"))
        variants = materialize_variants(prompt, paraphrase_client, pilot_config, n_paraphrases)
        for variant in variants:
            for model_key, model_cfg in selected_models.items():
                model_name = str(model_cfg["model"])
                for sample_idx in range(n_samples):
                    pending = {"prompt_hash": variant.prompt_hash, "model": model_name, "paraphrase_idx": variant.paraphrase_idx, "sample_idx": sample_idx}
                    if generation_store.has(pending):
                        skipped += 1
                        continue
                    from bench.api_clients import build_client

                    client = clients.setdefault(model_key, build_client(str(model_cfg["provider"]), model_cfg))
                    # CD condition always requires reasoning trace
                    capture_trace = bool(model_cfg.get("capture_reasoning_trace", False)) or variant.condition == "CD"
                    try:
                        result = client.generate(
                            variant.base_text,
                            max_tokens=int(model_cfg.get("token_budget", 1024)),
                            temperature=float(model_cfg.get("temperature", 0.2)),
                            capture_reasoning_trace=capture_trace,
                        )
                    except Exception as e:
                        print(f"  FAILED: {model_key} | hash={variant.prompt_hash[:16]}... | sample={sample_idx} | error={e}")
                        record = {
                            "prompt_hash": variant.prompt_hash,
                            "model": model_name,
                            "response": "",
                            "reasoning_trace": None,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "run_id": run_id,
                            "sample_idx": sample_idx,
                            "failure_reason": str(e),
                        }
                        record["generation_id"] = generation_id(record)
                        record["model_key"] = model_key
                        record["paraphrase_idx"] = variant.paraphrase_idx
                        record["condition"] = variant.condition
                        record["slot_T"] = variant.slot_T
                        record["slot_L"] = variant.slot_L
                        record["slot_V"] = variant.slot_V
                        record["slot_F"] = variant.slot_F
                        if generation_store.append(record):
                            annotation_store.append(make_annotation_template(record))
                            failed += 1
                        continue

                    generation = Generation(
                        prompt_hash=variant.prompt_hash,
                        model=model_name,
                        response=result.text,
                        reasoning_trace=result.reasoning_trace,
                        run_id=run_id,
                        sample_idx=sample_idx,
                    )
                    record = generation.model_dump(mode="json")
                    record["generation_id"] = generation_id(record)
                    record["model_key"] = model_key
                    record["paraphrase_idx"] = variant.paraphrase_idx
                    record["condition"] = variant.condition
                    record["slot_T"] = variant.slot_T
                    record["slot_L"] = variant.slot_L
                    record["slot_V"] = variant.slot_V
                    record["slot_F"] = variant.slot_F
                    if generation_store.append(record):
                        annotation_store.append(make_annotation_template(record))
                        written += 1
                        total_input_tokens += estimate_tokens(variant.base_text)
                        total_output_tokens += estimate_tokens(result.text or "")
                        if result.reasoning_trace:
                            total_output_tokens += estimate_tokens(result.reasoning_trace)
    print(f"run_id={run_id} written={written} skipped={skipped} failed={failed} store={generation_store.path}")
    est_cost = (total_input_tokens + total_output_tokens) / 1000 * 0.0015  # rough deepseek-reasoner cost
    print(f"estimated_tokens={total_input_tokens + total_output_tokens} est_cost_usd=${est_cost:.2f}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the pilot data pipeline.")
    parser.add_argument("--config", default="config/pilot.yaml", help="Pilot config YAML path.")
    parser.add_argument("--models", default="", help="Comma-separated model keys from config/models.yaml.")
    parser.add_argument("--conditions", default="", help="Comma-separated conditions or slot composites.")
    parser.add_argument("--prompts", default="", help="Override pilot JSONL path.")
    parser.add_argument("--dry-run", action="store_true", help="Print call counts and token estimates only.")
    parser.add_argument("--run-id", default="", help="Optional run id for outputs/runs/{run_id}.")
    return parser.parse_args()


def load_yaml(path: Path | str) -> dict[str, Any]:
    """Load a YAML mapping."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def parse_csv(value: str | list[str] | None) -> list[str]:
    """Parse comma-separated CLI values."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


def select_models(model_configs: dict[str, Any], requested: list[str]) -> dict[str, dict[str, Any]]:
    """Select target model configs by key."""
    if requested:
        missing = [key for key in requested if key not in model_configs]
        if missing:
            raise ValueError(f"unknown model keys: {', '.join(missing)}")
        selected = {key: model_configs[key] for key in requested}
    else:
        selected = {
            key: cfg
            for key, cfg in model_configs.items()
            if cfg.get("enabled", True) and cfg.get("role", "generation") == "generation"
        }
    for key, cfg in selected.items():
        if "provider" not in cfg or "model" not in cfg:
            raise ValueError(f"model config {key} must include provider and model")
    return selected


def load_prompts_from_config(
    pilot_config: dict[str, Any],
    conditions: list[str],
    *,
    allow_missing: bool,
    override_pilot_path: str = "",
) -> list[Prompt]:
    """Load prompts described by pilot config."""
    data_cfg = pilot_config.get("data", {})
    pilot_path = override_pilot_path or data_cfg.get("pilot_path", "data/pilot/pilot_v1.jsonl")
    try:
        return build_prompts(
            pilot_path=pilot_path,
            metadata_paths=data_cfg.get("metadata_paths", {}),
            conditions=conditions,
            sample_per_cell=pilot_config.get("sample_per_cell"),
        )
    except FileNotFoundError:
        if allow_missing:
            return []
        raise


def print_dry_run(
    prompts: list[Prompt],
    selected_models: dict[str, dict[str, Any]],
    pilot_config: dict[str, Any],
    n_paraphrases: int,
    n_samples: int = 1,
) -> None:
    """Print counts and approximate token usage."""
    variants_per_item = max(1, n_paraphrases)
    generation_calls = len(prompts) * len(selected_models) * variants_per_item * n_samples
    paraphrase_calls = len(prompts) if n_paraphrases > 0 else 0
    prompt_tokens = sum(estimate_tokens(prompt.base_text) for prompt in prompts)
    avg_prompt_tokens = math.ceil(prompt_tokens / len(prompts)) if prompts else 0
    output_tokens = sum(int(cfg.get("token_budget", 1024)) for cfg in selected_models.values())
    generation_token_budget = len(prompts) * variants_per_item * n_samples * (avg_prompt_tokens * len(selected_models) + output_tokens)
    paraphrase_cfg = pilot_config.get("paraphrase", {})
    paraphrase_token_budget = paraphrase_calls * (avg_prompt_tokens + int(paraphrase_cfg.get("max_tokens", 2048)))
    print(f"pilot_items={len(prompts)}")
    print(f"target_models={len(selected_models)}")
    print(f"paraphrases_per_item={variants_per_item}")
    print(f"samples_per_prompt={n_samples}")
    print(f"paraphrase_api_calls={paraphrase_calls}")
    print(f"generation_api_calls={generation_calls}")
    print(f"estimated_token_budget={generation_token_budget + paraphrase_token_budget}")


def estimate_tokens(text: str) -> int:
    """Estimate tokens with a simple character heuristic."""
    return max(1, math.ceil(len(text) / 4))


def build_paraphrase_client(
    pilot_config: dict[str, Any],
    model_configs: dict[str, Any],
    selected_models: dict[str, dict[str, Any]],
    n_paraphrases: int,
) -> BaseClient | None:
    """Build the paraphrase client when paraphrases are requested."""
    from bench.api_clients import build_client

    if n_paraphrases < 1:
        return None
    paraphrase_cfg = pilot_config.get("paraphrase", {})
    model_key = paraphrase_cfg.get("model_key") or next(iter(selected_models), "")
    if not model_key:
        raise ValueError("n_paraphrases > 0 requires at least one selected model or paraphrase.model_key")
    if model_key not in model_configs:
        raise ValueError(f"paraphrase model_key not found in models config: {model_key}")
    model_cfg = dict(model_configs[model_key])
    model_cfg.update(paraphrase_cfg.get("overrides", {}))
    return build_client(str(model_cfg["provider"]), model_cfg)


def materialize_variants(
    prompt: Prompt,
    paraphrase_client: BaseClient | None,
    pilot_config: dict[str, Any],
    n_paraphrases: int,
) -> list[Prompt]:
    """Return paraphrased variants or the base prompt."""
    from bench.paraphrase import generate_paraphrases

    if n_paraphrases < 1:
        return [prompt]
    if paraphrase_client is None:
        raise ValueError("paraphrase client is required when n_paraphrases > 0")
    paraphrase_cfg = pilot_config.get("paraphrase", {})
    batch = generate_paraphrases(
        prompt,
        paraphrase_client,
        n_paraphrases,
        max_tokens=int(paraphrase_cfg.get("max_tokens", 2048)),
        temperature=float(paraphrase_cfg.get("temperature", 0.4)),
    )
    if len(batch.validated) < n_paraphrases:
        raise ValueError(f"only {len(batch.validated)} of {n_paraphrases} paraphrases passed validation")
    return batch.validated


def ensure_outputs_untracked(outputs_root: Path) -> None:
    """Refuse to write outputs if git tracks that path."""
    if not Path(".git").exists():
        return
    result = subprocess.run(
        ["git", "ls-files", "--", str(outputs_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise RuntimeError(f"refusing to write tracked outputs path: {outputs_root}")


def generation_id(record: dict[str, Any]) -> str:
    """Derive a stable generation id from stored generation fields."""
    return sha256_json(
        {
            "prompt_hash": record["prompt_hash"],
            "model": record["model"],
            "run_id": record["run_id"],
            "timestamp": record["timestamp"],
            "sample_idx": record.get("sample_idx", 0),
        }
    )


def make_annotation_template(generation_record: dict[str, Any]) -> dict[str, Any]:
    """Create an unscored annotation template for one generation."""
    annotation = Annotation(
        prompt_hash=generation_record["prompt_hash"],
        generation_id=generation_record["generation_id"],
    )
    return annotation.model_dump(mode="json")


if __name__ == "__main__":
    main()
