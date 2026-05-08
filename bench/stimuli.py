"""Load user-authored pilot items and assemble final prompts."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

from bench.schema import Prompt


SLOT_ALIASES: dict[str, tuple[str, ...]] = {
    "slot_T": ("slot_T", "T", "target", "target_id"),
    "slot_L": ("slot_L", "L", "lens", "lens_id"),
    "slot_V": ("slot_V", "V", "voice", "voice_id"),
    "slot_F": ("slot_F", "F", "frame", "frame_id"),
}

TEXT_ALIASES = ("base_text", "prompt_text", "text", "stimulus")


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """Load a JSONL file into dictionaries."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"pilot JSONL not found: {file_path}")
    records: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError(f"{file_path}:{line_number} must be a JSON object")
            records.append(record)
    return records


def load_metadata(path: Path | str | None) -> dict[str, Any]:
    """Load optional JSON, JSONL, or YAML metadata keyed by id."""
    if path is None:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    if file_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    elif file_path.suffix.lower() == ".jsonl":
        payload = load_jsonl(file_path)
    else:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    return _normalize_metadata(payload)


def build_prompts(
    *,
    pilot_path: Path | str,
    metadata_paths: Mapping[str, Path | str | None] | None = None,
    conditions: Iterable[str] | None = None,
    sample_per_cell: int | None = None,
) -> list[Prompt]:
    """Build prompt objects from user-authored pilot rows."""
    metadata = {
        "targets": load_metadata((metadata_paths or {}).get("targets")),
        "lenses": load_metadata((metadata_paths or {}).get("lenses")),
        "voices": load_metadata((metadata_paths or {}).get("voices")),
        "frames": load_metadata((metadata_paths or {}).get("frames")),
    }
    requested_conditions = set(conditions or [])
    prompts = [
        _prompt_from_record(record, metadata)
        for record in load_jsonl(pilot_path)
        if _condition_matches(record, requested_conditions)
    ]
    if sample_per_cell is not None:
        return _sample_per_cell(prompts, sample_per_cell)
    return prompts


def assemble_prompt_text(record: Mapping[str, Any], metadata: Mapping[str, Mapping[str, Any]]) -> str:
    """Assemble the final prompt without inventing stimulus content."""
    slots = _extract_slots(record)
    body = _extract_text(record)
    header = [
        f"Target: {_describe_slot(slots['slot_T'], metadata.get('targets', {}))}",
        f"Lens: {_describe_slot(slots['slot_L'], metadata.get('lenses', {}))}",
        f"Voice: {_describe_slot(slots['slot_V'], metadata.get('voices', {}))}",
        f"Frame: {_describe_slot(slots['slot_F'], metadata.get('frames', {}))}",
    ]
    return "\n".join([*header, "", body])


def _prompt_from_record(record: Mapping[str, Any], metadata: Mapping[str, Mapping[str, Any]]) -> Prompt:
    """Convert one pilot row into a hashed prompt."""
    slots = _extract_slots(record)
    return Prompt.from_text(
        slot_T=slots["slot_T"],
        slot_L=slots["slot_L"],
        slot_V=slots["slot_V"],
        slot_F=slots["slot_F"],
        base_text=assemble_prompt_text(record, metadata),
        paraphrase_idx=0,
    )


def _extract_slots(record: Mapping[str, Any]) -> dict[str, str]:
    """Extract canonical slot values from a pilot row."""
    slots: dict[str, str] = {}
    for canonical, aliases in SLOT_ALIASES.items():
        value = next((record[alias] for alias in aliases if alias in record), None)
        if value is None or not str(value).strip():
            raise ValueError(f"pilot row missing required slot {canonical}")
        slots[canonical] = str(value).strip()
    return slots


def _extract_text(record: Mapping[str, Any]) -> str:
    """Extract user-authored prompt text from a pilot row."""
    value = next((record[alias] for alias in TEXT_ALIASES if alias in record), None)
    if value is None or not str(value).strip():
        raise ValueError("pilot row missing user-authored base_text")
    return str(value).strip()


def _condition_matches(record: Mapping[str, Any], requested_conditions: set[str]) -> bool:
    """Check whether a pilot row is in the requested condition set."""
    if not requested_conditions:
        return True
    condition = str(record.get("condition", "")).strip()
    if condition in requested_conditions:
        return True
    slots = _extract_slots(record)
    composite = f"{slots['slot_T']}:{slots['slot_L']}:{slots['slot_V']}:{slots['slot_F']}"
    return composite in requested_conditions


def _sample_per_cell(prompts: list[Prompt], sample_per_cell: int) -> list[Prompt]:
    """Take the first N prompts per slot cell."""
    if sample_per_cell < 1:
        return []
    grouped: dict[tuple[str, str, str, str], list[Prompt]] = defaultdict(list)
    for prompt in prompts:
        key = (prompt.slot_T, prompt.slot_L, prompt.slot_V, prompt.slot_F)
        if len(grouped[key]) < sample_per_cell:
            grouped[key].append(prompt)
    return [prompt for group in grouped.values() for prompt in group]


def _normalize_metadata(payload: Any) -> dict[str, Any]:
    """Normalize metadata payloads into id-keyed dictionaries."""
    if isinstance(payload, dict):
        return {str(key): value for key, value in payload.items()}
    if isinstance(payload, list):
        normalized: dict[str, Any] = {}
        for item in payload:
            if isinstance(item, dict):
                item_id = item.get("id") or item.get("key") or item.get("name")
                if item_id:
                    normalized[str(item_id)] = item
        return normalized
    raise ValueError("metadata must be a mapping or a list of objects")


def _describe_slot(slot_id: str, metadata: Mapping[str, Any]) -> str:
    """Render a slot id with optional metadata labels."""
    payload = metadata.get(slot_id)
    if payload is None:
        return slot_id
    if isinstance(payload, str):
        return f"{slot_id} - {payload}"
    if isinstance(payload, Mapping):
        label = payload.get("label") or payload.get("name") or payload.get("title")
        description = payload.get("description")
        parts = [str(part).strip() for part in (label, description) if str(part or "").strip()]
        return f"{slot_id} - {'; '.join(parts)}" if parts else slot_id
    return slot_id

