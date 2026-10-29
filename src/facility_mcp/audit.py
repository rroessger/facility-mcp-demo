"""Audit-Log als JSON Lines. Jede Zeile ist ein eigener, maschinenlesbarer Eintrag.

Protokolliert werden Rolle, Werkzeug, Parameter, Entscheidung und Trefferzahl.
Es werden keine Ergebnisinhalte gespeichert (Datensparsamkeit).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, **fields: Any) -> dict[str, Any]:
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields}
        if self.path is not None:
            line = json.dumps(entry, ensure_ascii=False, sort_keys=False)
            with self._lock, self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return entry
