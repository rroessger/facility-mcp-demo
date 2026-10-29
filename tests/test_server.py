import pytest

from conftest import audit_lines, payload

ALL_TOOLS = {"objekte_suchen", "reinigungsplan_abrufen", "reklamationen_auflisten",
             "reklamation_details", "qualitaetskennzahlen", "material_bestand"}


async def test_alle_werkzeuge_sind_nur_lesend(connect):
    async with connect("leitung") as c:
        tools = (await c.list_tools()).tools
    assert {t.name for t in tools} == ALL_TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True
        assert t.annotations.destructive_hint is False


async def test_objektleiter_sieht_nur_eigene_niederlassung(connect):
    async with connect("objektleiter", "Chemnitz") as c:
        data = payload(await c.call_tool("objekte_suchen", {}))["daten"]
    assert data and {o["niederlassung"] for o in data} == {"Chemnitz"}


async def test_fremde_niederlassung_wird_abgelehnt_nicht_still_ersetzt(connect, audit_path):
    async with connect("objektleiter", "Chemnitz") as c:
        r = await c.call_tool("objekte_suchen", {"niederlassung": "Leipzig"})
    assert r.is_error
    last = audit_lines(audit_path)[-1]
    assert last["decision"] == "deny" and "Leipzig" in last["reason"]


async def test_reklamationen_fremder_niederlassung_werden_abgelehnt(connect, audit_path):
    # Fund aus dem Test mit Qwen: Das Modell fragte nach Zwickau und bekam still Chemnitzer Daten.
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        r = await c.call_tool("reklamationen_auflisten", {"niederlassung": "Zwickau"})
    assert r.is_error
    last = audit_lines(audit_path)[-1]
    assert last["decision"] == "deny" and "Zwickau" in last["reason"]


async def test_reklamationslisten_nennen_die_niederlassung(connect):
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        rows = payload(await c.call_tool("reklamationen_auflisten", {"niederlassung": "Chemnitz"}))["daten"]
    assert rows and {r["niederlassung"] for r in rows} == {"Chemnitz"}


async def test_objekt_einer_fremden_niederlassung_ist_nicht_abrufbar(connect):
    async with connect("objektleiter", "Chemnitz") as c:
        r = await c.call_tool("reinigungsplan_abrufen", {"objekt_id": "O-1009"})  # Leipzig
    assert r.is_error


async def test_rolle_ohne_recht_wird_verweigert_und_protokolliert(connect, audit_path):
    async with connect("einkauf", "Chemnitz") as c:
        r = await c.call_tool("reklamation_details", {"reklamation_id": "R-2026-0900"})
    assert r.is_error
    entry = audit_lines(audit_path)[-1]
    assert (entry["tool"], entry["decision"], entry["reason"]) == (
        "reklamation_details", "deny", "tool_not_allowed")


async def test_listen_enthaelt_keinen_freitext(connect):
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        rows = payload(await c.call_tool("reklamationen_auflisten", {}))["daten"]
    assert rows and all("freitext" not in r for r in rows)


async def test_injection_in_reklamation_wird_gesperrt_und_protokolliert(connect, audit_path):
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        d = payload(await c.call_tool("reklamation_details", {"reklamation_id": "R-2026-0901"}))["daten"]
    assert d["freitext"]["gesperrt"] is True
    assert "Zugangsdaten" not in d["freitext"]["text"]
    entry = audit_lines(audit_path)[-1]
    assert entry["event"] == "injection_suspected" and entry["decision"] == "allow"


async def test_mail_und_link_im_freitext_werden_entfernt(connect):
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        d = payload(await c.call_tool("reklamation_details", {"reklamation_id": "R-2026-0900"}))["daten"]
    assert d["freitext"]["gesperrt"] is False
    assert "@" not in d["freitext"]["text"] and "http" not in d["freitext"]["text"]


async def test_eingabepruefung_lehnt_ungueltige_ids_ab(connect):
    async with connect("leitung") as c:
        r = await c.call_tool("reinigungsplan_abrufen", {"objekt_id": "'; DROP TABLE objekte;--"})
    assert r.is_error


async def test_kennzahlen_je_niederlassung(connect):
    async with connect("leitung") as c:
        rows = payload(await c.call_tool("qualitaetskennzahlen", {}))["daten"]
    assert {r["niederlassung"] for r in rows} == {"Chemnitz", "Zwickau", "Leipzig"}
    assert all(r["reklamationen_gesamt"] == r["erledigt"] + r["offen_oder_in_bearbeitung"] for r in rows)


async def test_material_unter_mindestbestand(connect):
    async with connect("einkauf", "Zwickau") as c:
        rows = payload(await c.call_tool("material_bestand", {"nur_unter_mindestbestand": True}))["daten"]
    assert all(m["bestand"] < m["mindestbestand"] and m["niederlassung"] == "Zwickau" for m in rows)


async def test_audit_log_enthaelt_keine_ergebnisinhalte(connect, audit_path):
    async with connect("qualitaetssicherung", "Chemnitz") as c:
        await c.call_tool("reklamation_details", {"reklamation_id": "R-2026-0900"})
    raw = audit_path.read_text(encoding="utf-8")
    assert "nicht durchgeführt" not in raw  # Freitext steht nicht im Log


async def test_ablehnung_nennt_dem_modell_den_grund(connect):
    async with connect("einkauf", "Chemnitz") as c:
        r = await c.call_tool("reklamation_details", {"reklamation_id": "R-2026-0900"})
    text = "".join(getattr(part, "text", "") for part in r.content)
    assert r.is_error and "einkauf" in text and "nicht verwenden" in text
