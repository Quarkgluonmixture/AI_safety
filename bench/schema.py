"""Pydantic schemas for prompts, generations, and annotations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def sha256_json(payload: dict[str, Any]) -> str:
    """Hash a JSON-serializable payload with stable key ordering."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def compute_prompt_hash(
    *,
    slot_T: str,
    slot_L: str,
    slot_V: str,
    slot_F: str,
    base_text: str,
    paraphrase_idx: int,
    condition: str = "D",
) -> str:
    """Compute the canonical prompt hash including condition code (D / LC)."""
    return sha256_json(
        {
            "slot_T": slot_T,
            "slot_L": slot_L,
            "slot_V": slot_V,
            "slot_F": slot_F,
            "base_text": base_text,
            "paraphrase_idx": paraphrase_idx,
            "condition": condition,
        }
    )


class Prompt(BaseModel):
    """A fully assembled prompt with immutable slot metadata."""

    model_config = ConfigDict(frozen=True)

    slot_T: str
    slot_L: str
    slot_V: str
    slot_F: str
    base_text: str
    paraphrase_idx: int = Field(ge=0)
    condition: str = Field(default="D", pattern="^(D|LC)$")
    prompt_hash: str = Field(min_length=64, max_length=64)

    @field_validator("slot_T", "slot_L", "slot_V", "slot_F", "base_text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject blank text fields."""
        if not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()

    @field_validator("prompt_hash")
    @classmethod
    def _is_sha256(cls, value: str) -> str:
        """Validate sha256 hex strings."""
        lowered = value.lower()
        if lowered != value or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("prompt_hash must be lowercase sha256 hex")
        return value

    @classmethod
    def from_text(
        cls,
        *,
        slot_T: str,
        slot_L: str,
        slot_V: str,
        slot_F: str,
        base_text: str,
        paraphrase_idx: int,
        condition: str = "D",
    ) -> "Prompt":
        """Build a prompt and derive its canonical hash. Condition is D or LC."""
        prompt_hash = compute_prompt_hash(
            slot_T=slot_T,
            slot_L=slot_L,
            slot_V=slot_V,
            slot_F=slot_F,
            base_text=base_text,
            paraphrase_idx=paraphrase_idx,
            condition=condition,
        )
        return cls(
            slot_T=slot_T,
            slot_L=slot_L,
            slot_V=slot_V,
            slot_F=slot_F,
            base_text=base_text,
            paraphrase_idx=paraphrase_idx,
            condition=condition,
            prompt_hash=prompt_hash,
        )


class Generation(BaseModel):
    """A model response for one prompt."""

    prompt_hash: str = Field(min_length=64, max_length=64)
    model: str
    response: str
    reasoning_trace: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    run_id: str


class Annotation(BaseModel):
    """A human or judge annotation record."""

    prompt_hash: str = Field(min_length=64, max_length=64)
    generation_id: str
    lvd_p_score: float | None = Field(default=None, ge=0, le=4)
    lvd_o_score: float | None = Field(default=None, ge=0, le=4)
    rsas: float | None = Field(default=None, ge=0, le=4)
    lens_uptake: float | None = Field(default=None, ge=0, le=4)
    voice_fidelity: float | None = Field(default=None, ge=0, le=4)
    mr_level: int | None = Field(default=None, ge=0, le=5)
    mr_timing: str | None = None
    mr_correction: str | None = None
    annotator_id: str = ""
    timestamp: datetime = Field(default_factory=utc_now)

