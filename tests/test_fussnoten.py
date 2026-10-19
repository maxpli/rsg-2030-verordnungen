"""Fußnoten: Verzeichnis vollständig und wie gedruckt, jede eingeordnet (docs/PRUEFUNG.md, «Wer prüft was»)."""

from __future__ import annotations

import pandas as pd
import pytest

from rsg2030 import fussnoten as fn


def _eintrag(**w) -> dict:
    return {s: "" for s in fn.SPALTEN} | {"Land": "X", "Ebene": "BL", "Region_ID": "X", "Seite": "1"} | w


def test_vorlage_erkannt_auch_mit_anderem_zeichen():
    """Am Text, nicht am Zeichen (Salzburg: «(1) zugeordnet zu CH»); ausgefüllt ist es keine Vorlage mehr."""
    assert fn.ist_vorlage("zugeordnet zu CH")
    assert fn.ist_vorlage("davon in Akut-Ordinationen EVA: ÄAVE IST x, PLAN x/Planstellen IST x, PLAN x")
    assert not fn.ist_vorlage("davon in Akut-Ordinationen EVA: ÄAVE IST 0, PLAN 0/Planstellen IST 0, PLAN 0")


def test_verzeichnis_regeln():
    df = pd.DataFrame(
        [
            _eintrag(Zeichen="(1)", Text="zugeordnet zu CH", Einordnung="Hinweis"),  # ist Vorlage
            _eintrag(Zeichen="(2)", Text="ZMK einschließlich 7 SLS KFO", Einordnung="betrifft Werte"),  # ohne Verweis
            _eintrag(Zeichen="(3)", Text="etwas", Einordnung=""),  # nicht eingeordnet
            _eintrag(Zeichen="(4)", Text="davon 2 ÄAVE PSD", Einordnung="Teilmenge"),
            _eintrag(Region_ID="Y", Zeichen="(4)", Text="davon 2 ÄAVE PSD", Einordnung="Hinweis"),  # uneinheitlich
        ]
    )
    befunde = " | ".join(fn.pruefe_verzeichnis(df))
    for teil in (
        "wörtlich die ÖSG-Vorlage",
        "braucht einen Verweis",
        "fehlt oder unbekannt",
        "verschieden eingeordnet",
    ):
        assert teil in befunde


def test_eintrag_einer_ersetzten_fassung():
    """Ersetzt ein Land seine Verordnung, fallen Einträge zur alten Datei auf – der PDF-Abgleich sähe sie nicht."""
    from pathlib import Path

    register = [fn.Matrixseite("X", "BL", "X", Path("neu.pdf"), 0)]
    df = pd.DataFrame(
        [
            _eintrag(PDF="neu.pdf", Zeichen="(1)", Text="etwas", Einordnung="Hinweis"),
            _eintrag(PDF="alt.pdf", Zeichen="(2)", Text="anderes", Einordnung="Hinweis"),
        ]
    )
    befunde = fn.pruefe_verzeichnis(df, register)
    assert len(befunde) == 1 and "alt.pdf" in befunde[0] and "alte Fassung" in befunde[0]


@pytest.mark.slow
def test_verzeichnis_wie_pdf():
    """Jede Fußnote der Textseiten steht im Verzeichnis, jedes Zeichen der Tabelle hat eine, jeder Text steht so da."""
    df = fn.lade()
    assert fn.pruefe_verzeichnis(df, fn.seiten()) == []
    assert fn.pruefe_gegen_pdf(df) == []
