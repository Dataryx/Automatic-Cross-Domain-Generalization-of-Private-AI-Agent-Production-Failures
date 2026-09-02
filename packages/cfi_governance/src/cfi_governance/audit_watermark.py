"""Persistent watermark for incremental audit sink export."""

from __future__ import annotations

import os
from pathlib import Path


class AuditWatermark:
    """Tracks last-exported audit cursor; optional file persistence across restarts."""

    def __init__(self, initial: int = 0, persist_path: Path | None = None) -> None:
        self._value = initial
        self._path = persist_path
        if persist_path is not None and persist_path.exists():
            raw = persist_path.read_text(encoding="utf-8").strip()
            if raw:
                self._value = int(raw)

    @classmethod
    def from_env(cls) -> AuditWatermark:
        path = os.getenv("CFI_AUDIT_SINK_WATERMARK_PATH")
        return cls(persist_path=Path(path) if path else None)

    @property
    def value(self) -> int:
        return self._value

    def advance(self, new_value: int) -> None:
        self._value = new_value
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(str(new_value), encoding="utf-8")
