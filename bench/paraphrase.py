"""Generate and validate paraphrastic prompt variants."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from bench.api_clients import BaseClient
from bench.schema import Prompt


@dataclass(frozen=True)
class ParaphraseBatch:
    """Raw candidates plus schema-preserving validated prompts."""

    candidates: list[str]
    validated: list[Prompt]


def build_paraphrase_instruction(prompt: Prompt, n: int) -> str:
    """Build the paraphrasing instruction for one prompt."""
    return f"""You are paraphrasing a research prompt for controlled model evaluation.

Preserve the semantics of these four schema slots exactly:
- target: {prompt.slot_T}
- lens: {prompt.slot_L}
- voice: {prompt.slot_V}
- frame: {prompt.slot_F}

Only change surface wording in the prompt body. Keep the Target, Lens, Voice, and Frame lines present and semantically unchanged. Do not add new task requirements, remove constraints, introduce examples, or create new stimulus content. Return exactly {n} candidates.

Return JSON only in this shape:
{{"candidates": ["candidate prompt 1", "candidate prompt 2"]}}

Original prompt:
<<<
{prompt.base_text}
>>>"""


def generate_paraphrases(
    prompt: Prompt,
    client: BaseClient,
    n: int,
    *,
    max_tokens: int,
    temperature: float,
) -> ParaphraseBatch:
    """Call a paraphrasing model and return validated variants."""
    if n < 1:
        return ParaphraseBatch(candidates=[], validated=[])
    instruction = build_paraphrase_instruction(prompt, n)
    result = client.generate(instruction, max_tokens=max_tokens, temperature=temperature)
    candidates = extract_candidates(result.text)
    validated_texts = [candidate for candidate in candidates if validate_variant(prompt, candidate)]
    validated = [
        Prompt.from_text(
            slot_T=prompt.slot_T,
            slot_L=prompt.slot_L,
            slot_V=prompt.slot_V,
            slot_F=prompt.slot_F,
            base_text=text,
            paraphrase_idx=index,
        )
        for index, text in enumerate(validated_texts[:n], start=1)
    ]
    return ParaphraseBatch(candidates=candidates, validated=validated)


def extract_candidates(response_text: str) -> list[str]:
    """Extract candidate strings from a JSON model response."""
    payload = json.loads(_strip_code_fence(response_text))
    if isinstance(payload, dict):
        candidates = payload.get("candidates", [])
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise ValueError("paraphrase response must contain a candidates list")
    return [candidate.strip() for candidate in candidates if isinstance(candidate, str) and candidate.strip()]


def validate_variant(original: Prompt, candidate: str) -> bool:
    """Validate that a paraphrase preserves required slot scaffolding."""
    if not candidate.strip() or candidate.strip() == original.base_text.strip():
        return False
    required_fragments = [
        "Target:",
        "Lens:",
        "Voice:",
        "Frame:",
        original.slot_T,
        original.slot_L,
        original.slot_V,
        original.slot_F,
    ]
    return all(fragment in candidate for fragment in required_fragments)


def _strip_code_fence(text: str) -> str:
    """Remove a single markdown code fence around JSON."""
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped

