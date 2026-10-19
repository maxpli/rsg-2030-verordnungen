"""Referenzdaten der Kennzahlen gegen ihre ÖSG-Quelle – bei jedem Lauf, damit sie kein Mensch bestätigen muss
(docs/PRUEFUNG.md, «Wer prüft was», Regel 1)."""

from __future__ import annotations

import math
import re

import pandas as pd
import pdfplumber
import pytest

from oesg_methodik import regionen_erzeugen
from oesg_methodik.pfade import OESG_PLANUNGSRICHTWERTE_CSV, OESG_REGIONEN_CSV, original_dir

pytestmark = pytest.mark.slow  # liest Quelldateien aus daten_original/

# ÖSG 2023, Stand 10.10.2025, aus dem RIS (ÖSG-Gutachten 5/2025): Hauptdokument = Textband, Anlage = Tabellenband
TEXTBAND = "SPG_AT_OSG_G_20251010_5_2025.pdf"
TABELLENBAND = "OeSG_2023_-_Tabellenband.pdf"
SEITE = 37
SPALTEN = ["Err_Min", "VDmin", "VDmax", "VD2021", "BEVmin"]


def _zahl(t: str) -> float:
    """«*» = kein Richtwert; «2.000» = 2000; «34,9» = 34.9."""
    return math.nan if t == "*" else float(t.replace(".", "").replace(",", "."))


def _tabelle_textband() -> dict[str, list[float]]:
    """Tabelle «Planungsrichtwerte für den gesamten ambulanten Bereich» (Textband S.37): Kürzel → die fünf Werte."""
    with pdfplumber.open(original_dir() / "oesg" / TEXTBAND) as pdf:
        text = pdf.pages[SEITE - 1].extract_text()
    teil = text[text.index("Planungsrichtwerte für den gesamten ambulanten Bereich") : text.index("Legende:")]
    zeilen: dict[str, list[float]] = {}
    for z in teil.splitlines():
        werte = z.split()[-5:]
        if len(z.split()) < 6 or not all(re.fullmatch(r"\*|[\d.,]+", w) for w in werte):
            continue  # Kopfzeile, Fußnoten
        kuerzel = "KFO" if "kieferorthopädisch" in z else re.findall(r"\(([A-Z]+)\)", z)[0]
        zeilen[kuerzel] = [_zahl(w) for w in werte]
    return zeilen


def test_richtwerte_wie_textband():
    """Jede Zeile der ÖSG-Tabelle steht mit denselben fünf Werten in oesg_planungsrichtwerte.csv («*» = leer)."""
    pdf = _tabelle_textband()
    assert len(pdf) >= 20, f"Tabelle auf S.{SEITE} nicht gefunden – andere Fassung des Textbands?"
    csv = pd.read_csv(OESG_PLANUNGSRICHTWERTE_CSV, sep=";", decimal=",")
    csv.index = list(csv["OESG_Code"])
    for kuerzel, werte in pdf.items():
        assert kuerzel in csv.index, f"{kuerzel} fehlt in {OESG_PLANUNGSRICHTWERTE_CSV.name}"
        ist = [float(v) for v in csv.loc[kuerzel, SPALTEN]]
        assert ist == pytest.approx(werte, nan_ok=True), f"{kuerzel}: CSV {ist}, Textband S.{SEITE} {werte}"


def test_regionen_wie_goeg_datei():
    """oesg_regionen.csv ist genau das, was regionen_erzeugen aus der GÖG-Datei «Regionale Gliederung» macht."""
    soll = regionen_erzeugen.lese().to_csv(index=False, lineterminator="\n")
    assert OESG_REGIONEN_CSV.read_text(encoding="utf-8") == soll


def test_fussnoten_vorlage_wie_tabellenband():
    """Jede Fußnote der ÖSG-Vorlage steht so in der RSG-Planungsmatrix des Tabellenbands (Anhang 9, S.259)."""
    from rsg2030.fussnoten import norm, vorlage
    from rsg2030.matrix_extract import kompakt

    with pdfplumber.open(original_dir() / "oesg" / TABELLENBAND) as pdf:
        seite = kompakt(norm(pdf.pages[259 - 1].extract_text()))
    for z, t in zip(vorlage()["Zeichen"], vorlage()["Text"]):
        assert kompakt(norm(z + t)) in seite, f"{z} {t}"


def test_zeilen_vorlage_wie_tabellenband():
    """Jede Zeilenbeschriftung der ÖSG-Vorlage (oesg_rsgpm_zeilen.csv) steht so in der RSG-Planungsmatrix des
    Tabellenbands (Anhang 9, S.259). Die Platzhalter der Zellen («x», «-», «n.v.») stehen dort mitten in umbrochenen
    Beschriftungen; sie fallen auf beiden Seiten weg (auch «-» in «ÖGK - Planstellen»)."""
    from rsg2030.matrix_extract import kompakt
    from rsg2030.vorlage import zeilen

    def ohne_platzhalter(t: str) -> str:
        return kompakt(" ".join(w for w in t.split() if w not in {"x", "-", "n.v."}))

    with pdfplumber.open(original_dir() / "oesg" / TABELLENBAND) as pdf:
        seite = ohne_platzhalter(pdf.pages[259 - 1].extract_text())
    for t in zeilen()["Beschriftung"]:
        assert ohne_platzhalter(t) in seite, t


def test_spalten_vorlage_wie_tabellenband():
    """Die Fachspalten der Vorlage (vorlage.SPALTEN_VORLAGE) sind die erste Kopfzeile der RSG-Planungsmatrix im
    Tabellenband (Anhang 9, S.259), ohne Fußnotenzeichen und in derselben Reihenfolge."""
    from rsg2030.vorlage import SPALTEN_VORLAGE

    with pdfplumber.open(original_dir() / "oesg" / TABELLENBAND) as pdf:
        text = pdf.pages[259 - 1].extract_text()
    kopf = next(z for z in text.splitlines() if z.startswith("AM(4)"))
    gelesen = re.sub(r"\(\d\)", " ", kopf).split()
    assert tuple(gelesen) == SPALTEN_VORLAGE, gelesen
