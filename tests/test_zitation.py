"""CITATION.cff passt zur Version: gleiche Versionsnummer wie pyproject.toml, Abrufdaten = Tag des Release.

Was nur beim Release gilt (Version = Tag, Datum gesetzt und nicht in der Zukunft), prüft
`.github/workflows/release.yml`.
"""

from __future__ import annotations

import tomllib

import yaml
from conftest import ROOT


def _cff() -> dict:
    return yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))


def test_version_wie_pyproject() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert _cff()["version"] == pyproject["project"]["version"]


def test_abrufdatum_ist_tag_des_release() -> None:
    """Der Release-Lauf lädt jede Quelle frisch und prüft ihre Prüfsumme; belegt ist also der Abruf am Tag des
    Release. Vor dem ersten Datum hat keine Referenz eines."""
    cff = _cff()
    erwartet = cff.get("date-released")
    abweichend = {r["title"]: r.get("date-accessed") for r in cff["references"] if r.get("date-accessed") != erwartet}
    assert not abweichend, f"date-accessed muss date-released sein ({erwartet}): {abweichend}"
