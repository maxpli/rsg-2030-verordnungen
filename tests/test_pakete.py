"""Import-Richtungen: `oesg_methodik` ist eigenständig, `rsg2030` darf es nutzen, nicht umgekehrt.

    rsg2030 → oesg_methodik

So lässt sich die ÖSG-Methodik später ohne Umbau für weitere Datensätze verwenden (eigenes Paket/Repo).
Außerdem keine allgemeinen Modulnamen auf oberster Ebene (`paths`, `quellen` …): das Paket wird auch in
andere Projekte installiert.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from conftest import ROOT

ERLAUBT = {"oesg_methodik": {"oesg_methodik"}, "rsg2030": {"rsg2030", "oesg_methodik"}}


def _eigene_importe(datei: Path) -> set[str]:
    baum = ast.parse(datei.read_text(encoding="utf-8"))
    namen: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            namen |= {a.name.split(".")[0] for a in knoten.names}
        elif isinstance(knoten, ast.ImportFrom) and knoten.module and knoten.level == 0:
            namen.add(knoten.module.split(".")[0])
    return namen & set(ERLAUBT)


@pytest.mark.parametrize("paket", ERLAUBT)
def test_import_richtungen(paket):
    verstoesse = [
        f"{d.relative_to(ROOT)} → {sorted(_eigene_importe(d) - ERLAUBT[paket])}"
        for d in sorted((ROOT / paket).rglob("*.py"))
        if _eigene_importe(d) - ERLAUBT[paket]
    ]
    assert not verstoesse, "Verbotene Import-Richtung:\n" + "\n".join(verstoesse)


def test_nur_zwei_pakete():
    oben = {p.stem for p in ROOT.glob("*.py")} | {
        p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists()
    }
    assert oben == set(ERLAUBT), oben


def test_datenordner_beim_aufruf(tmp_path, monkeypatch):
    """Datenordner gelten ab dem Setzen von RSG2030_DATEN, auch nach dem Import (Einbinden in andere Projekte)."""
    from oesg_methodik import pfade
    from rsg2030 import config

    monkeypatch.delenv("RSG2030_AUSGABE_DIR", raising=False)
    monkeypatch.delenv("RSG2030_QUELLEN_DIR", raising=False)
    monkeypatch.setenv("RSG2030_DATEN", str(tmp_path))
    assert pfade.original_dir() == tmp_path.resolve() / "daten_original"
    assert config.ausgabe_dir() == tmp_path.resolve() / "daten_ergebnis"
    assert config.quellen_dir() == tmp_path.resolve() / "daten_original"


def test_cli_unbekannte_option(capsys):
    """Ein Tippfehler in einer Option bricht ab, statt still ignoriert zu werden."""
    from rsg2030.__main__ import main

    with pytest.raises(SystemExit) as e:
        main(["download", "--nue"])
    assert e.value.code == 2
    with pytest.raises(SystemExit):
        main(["alles", "--neu"])


ALTE_NAMEN = ("Matrix_long", "Kennzahlen_long", "Matrix_Audit", "rsg2030 kennzahlen", "Laufprotokoll_kennzahlen")
"""Namen vor der ersten Veröffentlichung (Dateien heißen seit 2026.1 Planungsmatrizen und Versorgungsdichte)."""


def test_keine_alten_namen():
    """Docs, Code und CI nennen die Ausgaben und Befehle so, wie sie heute heißen (CHANGELOG 2026.1)."""
    ohne = {".venv", ".git", "daten_original", "daten_ergebnis", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    dateien = [
        d
        for d in ROOT.rglob("*")
        if d.is_file()
        and "daten_original" not in d.relative_to(ROOT).parts
        and d.suffix in {".py", ".md", ".yml", ".toml", ".cff", ".csv"}
        and (not ohne & set(d.relative_to(ROOT).parts) or d.relative_to(ROOT).parts[-1] == "README.md")
        and ".venv" not in d.relative_to(ROOT).parts
        and d.name != "test_pakete.py"
    ]
    treffer = [f"{d.relative_to(ROOT)}: {n}" for d in dateien for n in ALTE_NAMEN if n in d.read_text(encoding="utf-8")]
    assert not treffer, "Alte Namen:\n" + "\n".join(treffer)
