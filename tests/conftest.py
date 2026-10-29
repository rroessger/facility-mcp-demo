import json
from pathlib import Path

import pytest
from mcp import Client

from facility_mcp.policy import Identity
from facility_mcp.server import build_server


@pytest.fixture
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "audit.jsonl"


@pytest.fixture
def connect(audit_path):
    """Gibt eine Funktion zurück, die einen Client mit gewünschter Identität verbindet."""

    def _connect(role: str, branch: str | None = None) -> Client:
        return Client(build_server(Identity(role, branch), audit_path=audit_path))

    return _connect


def payload(result) -> dict:
    return result.structured_content


def audit_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
