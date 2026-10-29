"""Fußnoten: Verzeichnis vollständig und wie gedruckt, jede eingeordnet (docs/PRUEFUNG.md, «Wer prüft was»)."""

from __future__ import annotations

import re

import pandas as pd
import pdfplumber
import pytest

from oesg_methodik.pfade import OESG_REGIONEN_CSV, original_dir
from rsg2030 import config
from rsg2030 import fussnoten as fn

# OÖ: Die KFO-Planstellen der ZMK-Fußnote stehen auf den Bezirksseiten einzeln, je Bezirk mit den drei Trägern
OOE_ANLAGE = "rsg_2030/oberoesterreich/4.VO_RSG_OOe_2030_Anlage.pdf"
KFO_BEZIRK = re.compile(
    r"zuzügl\. in Kieferorthopädie \(KFO\): (\d+) vertragskieferorthopädische Planstellen?: ÖGK, SVS, BVAEB"
)
# Angabe, die nur auf der Bezirksseite steht (Linz Stadt) – offene Frage in docs/offene_punkte.md, «Oberösterreich»
ZAHNGESUNDHEITSZENTRUM = "+ 2,2 Sachleistungsstellen in ÖGK-Zahngesundheitszentrum"


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


@pytest.mark.slow
def test_ooe_kfo_planstellen_stehen_auf_den_bezirksseiten():
    """Die 32 KFO-Planstellen der ZMK-Fußnote stehen auf den Bezirksseiten Oberösterreichs einzeln, je Bezirk mit den
    drei Trägern und dem Wort «zuzügl.» – während die ORTR-Fußnote derselben Zeile «davon in Unfallchirurgie (UC)»
    sagt. Das Dokument unterscheidet also enthalten von zusätzlich und nennt die Träger selbst: Beleg für die Lesart
    in METHODIK R4 (PRUEFUNG.md, «Steckt KFO schon in der gedruckten ZMK-Spalte?»)."""
    je_seite: dict[int, list[int]] = {}
    with pdfplumber.open(original_dir() / OOE_ANLAGE) as pdf:
        for nr, seite in enumerate(pdf.pages, start=1):
            text = " ".join((seite.extract_text() or "").split())
            if treffer := [int(t) for t in KFO_BEZIRK.findall(text)]:
                je_seite[nr] = treffer
                assert "davon in Unfallchirurgie (UC)" in text, f"S.{nr}: «davon» für UC fehlt"
    assert len(je_seite) == 6, f"Bezirksseiten mit KFO: {sorted(je_seite)}"  # eine je Versorgungsregion
    assert sum(sum(v) for v in je_seite.values()) == 32  # = Fußnote des Bundeslands
    # je Seite so viele Bezirke wie die Versorgungsregion hat (ÖSG-Referenz, Seiten in Reihenfolge der VR 41–46)
    regionen = pd.read_csv(OESG_REGIONEN_CSV, dtype=str)
    ooe = regionen[regionen["Bundesland"].str.startswith("Ober")]
    bezirke = ooe.groupby("VR")["Bezirk"].count().sort_index().tolist()
    assert [len(je_seite[nr]) for nr in sorted(je_seite)] == bezirke
    # und je Seite die Zahl der VR-Fußnote, wie sie als Korrekturregel hinterlegt ist
    regeln = pd.read_csv(config.korrekturen_csv(), dtype=str)
    vr = regeln[(regeln["Fach"] == "KFO") & (regeln["Ebene"] == "VR") & regeln["Zeile_ID"].str.contains("planstellen")]
    werte = {r["Region_ID"]: int(r["Regel"].removeprefix("zusatz:")) for _, r in vr.iterrows()}
    assert [sum(je_seite[nr]) for nr in sorted(je_seite)] == [werte[v] for v in sorted(werte)]


@pytest.mark.slow
def test_ooe_zahngesundheitszentrum_nur_auf_der_bezirksseite():
    """Die «+ 2,2 Sachleistungsstellen in ÖGK-Zahngesundheitszentrum» stehen nur auf der Bezirksseite (Linz Stadt),
    auf keiner BL- oder VR-Seite – deshalb ist nichts ergänzt (docs/offene_punkte.md, «Oberösterreich»)."""
    seiten = []
    with pdfplumber.open(original_dir() / OOE_ANLAGE) as pdf:
        for nr, seite in enumerate(pdf.pages, start=1):
            if ZAHNGESUNDHEITSZENTRUM in " ".join((seite.extract_text() or "").split()):
                seiten.append(nr)
    assert seiten == [13]  # Bezirksseite der VR 41 (Linz Stadt, Linz-Land)
