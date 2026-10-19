"""Gemeinsame Test-Fixtures: Projektpfade + einmaliger Pipeline-Lauf je Testsession.

Voraussetzung: Projekt editierbar installiert (README, «Installation»); Marker in pyproject.toml.
Schnell (ohne PDFs, ~1 s):    pytest -m "not slow"
Vollständig (vor Commit):     pytest
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def pipeline():
    """Extraktion → Korrekturen → Checks (ohne Dateien zu schreiben): `pipeline.PipelineErgebnis`."""
    from rsg2030.pipeline import baue_pipeline

    return baue_pipeline()


def erwartete_ausgabe(name: str) -> dict:
    """Erwartete Prüfsumme einer Ausgabe (`rsg2030/erwartete_ausgaben.csv`, dieselbe wie beim Abgleich am Ende eines
    Laufs). Eine bewusste Datenänderung: Unterschied prüfen, SHA256 und Zeilen dort eintragen, CHANGELOG ergänzen."""
    from rsg2030.abgleich import erwartet

    soll = erwartet(name)
    assert soll is not None, f"{name} fehlt in rsg2030/erwartete_ausgaben.csv"
    return soll


def pruefe_ausgabe(name: str, text: str, lokal: Path) -> None:
    """Frisch erzeugter Text == erwartete Prüfsumme; bei Abweichung erste Unterschiede zur lokalen Datei zeigen."""
    import hashlib

    soll = erwartete_ausgabe(name)
    ist = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if ist == soll["SHA256"]:
        return
    hinweis = ""
    if lokal.is_file():
        alt, neu = lokal.read_text(encoding="utf-8").splitlines(), text.splitlines()
        diff = [(i, a, b) for i, (a, b) in enumerate(zip(alt, neu), start=1) if a != b][:5]
        hinweis = f"\nlokale Datei {len(alt)} vs. neu {len(neu)} Zeilen; erste Unterschiede:\n" + "\n".join(
            f"  Z.{i}\n   alt: {a}\n   neu: {b}" for i, a, b in diff
        )
    pytest.fail(
        f"{name}: Inhalt geändert (SHA256 {ist[:12]}…, erwartet {soll['SHA256'][:12]}…, "
        f"{text.count(chr(10))} statt {soll['Zeilen']} Zeilen). Gewollt? Dann in rsg2030/erwartete_ausgaben.csv "
        f"eintragen.{hinweis}"
    )
