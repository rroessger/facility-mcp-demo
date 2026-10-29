"""Lädt die synthetischen Demo-Daten. In einer echten Umgebung ersetzt eine Schicht
mit Datenbank- oder API-Zugriff dieses Modul. Die Werkzeuge bleiben unverändert."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Store:
    objekte: dict[str, dict[str, Any]]
    plaene: dict[str, list[dict[str, Any]]]
    reklamationen: dict[str, dict[str, Any]]
    material: list[dict[str, Any]]

    @classmethod
    def load(cls, data_dir: Path = DEFAULT_DATA_DIR) -> "Store":
        def read(name: str) -> Any:
            return json.loads((data_dir / f"{name}.json").read_text(encoding="utf-8"))

        return cls(
            objekte={o["id"]: o for o in read("objekte")},
            plaene={p["objekt_id"]: p["leistungen"] for p in read("reinigungsplaene")},
            reklamationen={r["id"]: r for r in read("reklamationen")},
            material=read("material"),
        )
