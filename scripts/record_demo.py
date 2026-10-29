"""Spielt vier Szenarien gegen den echten Server und schreibt die Antworten nach docs/demo-data.js.

Die Seite docs/index.html zeigt genau diese aufgezeichneten Antworten. Nichts davon ist von Hand
geschrieben. Aufruf: python scripts/record_demo.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import Client

from facility_mcp.policy import Identity
from facility_mcp.server import build_server

ROOT = Path(__file__).resolve().parent.parent

SCENARIOS = [
    {"id": "s1", "titel": "Offene Reklamationen eines Standorts",
     "frage": "Welche Reklamationen sind in Chemnitz offen, und was steht in der neuesten?",
     "rolle": ("qualitaetssicherung", "Chemnitz"),
     "calls": [("reklamationen_auflisten", {"status": "offen"}),
               ("reklamation_details", {"reklamation_id": "R-2026-0900"})],
     "erwartung": "Die Liste enthält keinen Freitext. Im Detail sind E-Mail-Adresse und Link entfernt."},
    {"id": "s2", "titel": "Eingeschleuste Anweisung im Freitext",
     "frage": "Was steht in Reklamation R-2026-0901?",
     "rolle": ("qualitaetssicherung", "Chemnitz"),
     "calls": [("reklamation_details", {"reklamation_id": "R-2026-0901"})],
     "erwartung": "Der Text enthält einen Befehl an die KI. Der Server liefert ihn nicht aus und markiert den Vorgang im Audit-Log."},
    {"id": "s3", "titel": "Zugriff verweigert",
     "frage": "Ein Einkäufer fragt nach Reklamationstexten. Ein Objektleiter aus Chemnitz fragt nach Leipzig. Die Qualitätssicherung aus Chemnitz fragt nach den Reklamationen in Zwickau.",
     "rolle": None,
     "calls": [(("einkauf", "Chemnitz"), "reklamation_details", {"reklamation_id": "R-2026-0900"}),
               (("objektleiter", "Chemnitz"), "objekte_suchen", {"niederlassung": "Leipzig"}),
               (("qualitaetssicherung", "Chemnitz"), "reklamationen_auflisten", {"niederlassung": "Zwickau"})],
     "erwartung": "Alle drei Anfragen werden abgelehnt, nichts wird still umgeleitet. Alle stehen im Audit-Log. Die dritte Anfrage stammt aus einem Test mit einem lokalen Modell, das nach Zwickau fragte."},
    {"id": "s4", "titel": "Kennzahlen für die Leitung",
     "frage": "Wie steht es um die Reklamationen in allen Niederlassungen?",
     "rolle": ("leitung", None),
     "calls": [("qualitaetskennzahlen", {})],
     "erwartung": "Nur die Rolle Leitung darf niederlassungsübergreifend lesen."},
]


def text_of(result) -> object:
    if result.structured_content is not None:
        return result.structured_content
    return "".join(getattr(c, "text", "") for c in result.content)


async def main() -> None:
    audit = Path(tempfile.mkdtemp()) / "audit.jsonl"
    out = []
    for s in SCENARIOS:
        steps = []
        for call in s["calls"]:
            if len(call) == 3:
                ident, tool, args = call
            else:
                ident, (tool, args) = s["rolle"], call
            async with Client(build_server(Identity(*ident), audit_path=audit)) as c:
                res = await c.call_tool(tool, args)
            steps.append({"rolle": ident[0], "niederlassung": ident[1], "werkzeug": tool,
                          "parameter": args, "fehler": bool(res.is_error), "antwort": text_of(res)})
        out.append({"id": s["id"], "titel": s["titel"], "frage": s["frage"],
                    "erwartung": s["erwartung"], "schritte": steps})
    log = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    payload = {"szenarien": out, "audit": log}
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "demo-data.js").write_text(
        "window.DEMO = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(out)} Szenarien, {len(log)} Audit-Einträge geschrieben")


if __name__ == "__main__":
    asyncio.run(main())
