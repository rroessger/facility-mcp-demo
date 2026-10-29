import pytest

from facility_mcp.policy import Identity, PolicyError


def test_unbekannte_rolle_startet_nicht():
    with pytest.raises(PolicyError):
        Identity("root", "Chemnitz")


def test_rolle_ohne_niederlassung_startet_nicht():
    with pytest.raises(PolicyError):
        Identity("objektleiter", None)


def test_leitung_braucht_keine_niederlassung():
    assert Identity("leitung", None).may_see_branch("Leipzig")


def test_env_ohne_rolle_startet_nicht(monkeypatch):
    monkeypatch.delenv("FACILITY_ROLE", raising=False)
    with pytest.raises(PolicyError):
        Identity.from_env()
