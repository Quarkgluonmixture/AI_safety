"""Append-only JSONL storage with idempotent hash keys."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


class JSONLStore:
    """Write JSONL records once per configured key."""

    def __init__(self, path: Path | str, key_fields: tuple[str, ...] = ("prompt_hash",)) -> None:
        self.path = Path(path)
        self.key_fields = key_fields
        self._keys: set[tuple[Any, ...]] | None = None

    def read_records(self) -> list[dict[str, Any]]:
        """Read all valid JSONL records."""
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records

    def read_deduped_by_hash(self) -> dict[str, dict[str, Any]]:
        """Read records deduped by prompt_hash, preserving the first record."""
        deduped: dict[str, dict[str, Any]] = {}
        for record in self.read_records():
            prompt_hash = record.get("prompt_hash")
            if prompt_hash and prompt_hash not in deduped:
                deduped[prompt_hash] = record
        return deduped

    def existing_keys(self) -> set[tuple[Any, ...]]:
        """Return the set of keys already written."""
        if self._keys is None:
            self._keys = {self._key(record) for record in self.read_records()}
        return self._keys

    def has(self, record: Mapping[str, Any]) -> bool:
        """Check whether a record key already exists."""
        return self._key(record) in self.existing_keys()

    def append(self, record: Mapping[str, Any]) -> bool:
        """Append a record if its key is new."""
        self._validate_record(record)
        key = self._key(record)
        if key in self.existing_keys():
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
        self.existing_keys().add(key)
        return True

    def append_many(self, records: Iterable[Mapping[str, Any]]) -> int:
        """Append multiple records and return the count written."""
        return sum(1 for record in records if self.append(record))

    def _key(self, record: Mapping[str, Any]) -> tuple[Any, ...]:
        """Build the configured idempotency key."""
        return tuple(record[field] for field in self.key_fields)

    def _validate_record(self, record: Mapping[str, Any]) -> None:
        """Validate minimum JSONL store invariants."""
        if "prompt_hash" not in record:
            raise ValueError("JSONL records must include prompt_hash")
        prompt_hash = record["prompt_hash"]
        if not isinstance(prompt_hash, str) or len(prompt_hash) != 64:
            raise ValueError("prompt_hash must be a sha256 hex string")
        if any(char not in "0123456789abcdef" for char in prompt_hash):
            raise ValueError("prompt_hash must be a sha256 hex string")
        missing = [field for field in self.key_fields if field not in record]
        if missing:
            raise ValueError(f"record missing key fields: {', '.join(missing)}")
