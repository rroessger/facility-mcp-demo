"""Rollen, Rechte und Datenbereiche.

Grundsatz: Zugriff wird verweigert, wenn nichts ausdrücklich erlaubt ist (fail closed).
Die Identität kommt aus der Server-Konfiguration, nicht vom Modell. Das Modell kann
seine eigene Rolle also nicht per Prompt ändern.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

TOOLS = (
    "objekte_suchen",
    "reinigungsplan_abrufen",
    "reklamationen_auflisten",
    "reklamation_details",
    "qualitaetskennzahlen",
    "material_bestand",
)

ROLE_TOOLS: dict[str, frozenset[str]] = {
    "objektleiter": frozenset(
        {"objekte_suchen", "reinigungsplan_abrufen", "reklamationen_auflisten"}
    ),
    "qualitaetssicherung": frozenset(
        {
            "objekte_suchen",
            "reinigungsplan_abrufen",
            "reklamationen_auflisten",
            "reklamation_details",
            "qualitaetskennzahlen",
        }
    ),
    "einkauf": frozenset({"material_bestand"}),
    "leitung": frozenset(TOOLS),
}

# Nur "leitung" darf niederlassungsübergreifend lesen.
BRANCH_UNRESTRICTED = frozenset({"leitung"})


class PolicyError(Exception):
    """Zugriff nicht erlaubt oder Konfiguration ungültig."""


@dataclass(frozen=True)
class Identity:
    role: str
    branch: str | None  # None = alle Niederlassungen (nur Rolle "leitung")

    def __post_init__(self) -> None:
        if self.role not in ROLE_TOOLS:
            raise PolicyError(f"Unbekannte Rolle: {self.role!r}")
        if self.role in BRANCH_UNRESTRICTED:
            return
        if not self.branch:
            raise PolicyError(
                f"Rolle {self.role!r} braucht eine Niederlassung (FACILITY_BRANCH)."
            )

    def may_call(self, tool: str) -> bool:
        return tool in ROLE_TOOLS[self.role]

    def may_see_branch(self, branch: str) -> bool:
        return self.branch is None or self.branch == branch

    @classmethod
    def from_env(cls) -> "Identity":
        role = os.environ.get("FACILITY_ROLE", "").strip().lower()
        branch = os.environ.get("FACILITY_BRANCH", "").strip() or None
        if not role:
            raise PolicyError(
                "FACILITY_ROLE ist nicht gesetzt. Der Server startet ohne Rolle nicht."
            )
        return cls(role=role, branch=branch)
