"""Referenzdaten der Kennzahlen gegen ihre ÖSG-Quelle – bei jedem Lauf, damit sie kein Mensch bestätigen muss
(docs/PRUEFUNG.md, «Wer prüft was», Regel 1)."""

from __future__ import annotations

import math
import re

import pandas as pd
import pdfplumber
import pytest

from oesg_methodik import regionen_erzeugen
from oesg_methodik.pfade import OESG_PLANUNGSRICHTWERTE_CSV, OESG_REGIONEN_CSV, oesg_pdf

pytestmark = pytest.mark.slow  # liest Quelldateien aus daten_original/

# Welche Dateien die beiden Bände sind, steht in `oesg_methodik.pfade.OESG_BAENDE` (ein Ort je ÖSG-Stand).
SEITE = 39  # Textband: Tabelle der Planungsrichtwerte
SPALTEN = ["Err_Min", "VDmin", "VDmax", "VD2021", "BEVmin"]
# Die 20 Zeilen der Richtwerttabelle in ihrer Reihenfolge, als Literal aus der Quelle (Textband S.39): So fällt auf,
# wenn der Parser eine Zeile überspringt – sie bliebe sonst ungeprüft – oder der ÖSG eine aufnimmt, streicht oder
# umstellt. Eine Zählung allein («mindestens 20») würde beides übersehen. Abgelesen an der gerenderten Seite, nicht
# an der Textextraktion: Verschluckt die eine Zeile, fehlt sie dem Parser und der Kontrolle gleichermaßen.
# Rendern wie die Zweitlesung, `rsg2030/scripts/zweitlesung_ki.py` (`bild()`, pdfium) – derselbe zweite Weg neben
# der Textzerlegung (pdfminer), auf dem auch Ebene 3 des Prüfkonzepts beruht.
RICHTWERT_ZEILEN = ("AM", "KIJU", "KJC", "KJP", "CH", "NCH", "IM", "PUL", "GGH", "NEU",
                    "PSY", "DER", "AU", "HNO", "URO", "PCH", "ORTR", "MKG", "ZMK", "KFO")  # fmt: skip


def _zahl(t: str) -> float:
    """«*» = kein Richtwert; «2.000» = 2000; «34,9» = 34.9."""
    return math.nan if t == "*" else float(t.replace(".", "").replace(",", "."))


# Lauf aus Werten («*» oder Zahl). Gelesen werden die **letzten fünf** eines Laufs: Vor dem ersten Wert steht oft
# ein Fußnotenzeichen, das wie eine Zahl aussieht («Kinder- und Jugendpsychiatrie (KJP)1 30 0,8 1,4 1,0 100.000»).
WERTELAUF = re.compile(r"(?:\*|[\d.,]+)(?: (?:\*|[\d.,]+))*")
# Form der fünf Spalten: Err. (Min.) ganzzahlig, VDmin/VDmax/VD2021 mit einer Nachkommastelle, BEVmin mit
# Tausenderpunkt; «*» heißt «kein Richtwert» und ist überall erlaubt.
SPALTENFORM = [re.compile(r"\*|\d+"), *[re.compile(r"\*|\d+,\d") for _ in range(3)], re.compile(r"\*|[\d.]+")]
KUERZEL = re.compile(r"\(([A-Z]+)\)")


def _tabelle_textband() -> dict[str, list[float]]:
    """Tabelle «Planungsrichtwerte für den gesamten ambulanten Bereich» (Textband S.39): Kürzel → die fünf Werte.

    Nicht zeilenweise: Der ÖSG bricht manche Zeilen um, und zwar verschieden – bei PUL stehen die Werte nach dem
    ersten Teil der Beschriftung, bei PCH **vor** dem Kürzel («Plastische, … Ästhetische * * * * * Chirurgie
    (PCH)»). Darum: jede Folge von fünf Werten suchen und ihr das nächstgelegene Kürzel zuordnen."""
    with pdfplumber.open(oesg_pdf("Textband")) as pdf:
        text = pdf.pages[SEITE - 1].extract_text()
    teil = text[text.index("Planungsrichtwerte für den gesamten ambulanten Bereich") : text.index("Legende:")]
    teil = " ".join(teil.split())
    zeilen: dict[str, list[float]] = {}
    for lauf in WERTELAUF.finditer(teil):
        tokens = lauf.group(0).split()
        # von rechts das erste Fünfer-Fenster mit der Form der Tabellenspalten: So fallen Fußnotenzeichen weg,
        # die vorne («(KJP)1 30 …») wie hinten («… 3,9 * 1 vorrangig …») an die Werte stoßen.
        fenster = ((i, tokens[i : i + 5]) for i in range(len(tokens) - 5, -1, -1))
        passend = [(i, f) for i, f in fenster if all(m.fullmatch(w) for m, w in zip(SPALTENFORM, f))]
        if not passend:
            continue
        i, werte = passend[0]
        anfang = lauf.end() - len(" ".join(tokens[i:]))
        davor, danach = teil[:anfang], teil[lauf.end() :]
        if "kieferorthopädisch" in davor[-90:]:
            kuerzel = "KFO"  # Unterzeile ohne Kürzel: «- davon mit kieferorthopädischem Schwerpunkt»
        else:
            vorne = list(KUERZEL.finditer(davor))
            hinten = KUERZEL.search(danach)
            abstand_v = len(davor) - vorne[-1].end() if vorne else None
            if hinten is not None and (abstand_v is None or hinten.start() < abstand_v):
                kuerzel = hinten.group(1)  # Kürzel steht hinter den Werten (PCH)
            elif vorne:
                kuerzel = vorne[-1].group(1)
            else:
                continue  # Kopfzeile «Err. (Min.) VDmin …»
        zeilen[kuerzel] = [_zahl(w) for w in werte]
    return zeilen


def test_richtwerte_wie_textband():
    """Jede Zeile der ÖSG-Tabelle steht mit denselben fünf Werten in oesg_planungsrichtwerte.csv («*» = leer)."""
    pdf = _tabelle_textband()
    assert tuple(pdf) == RICHTWERT_ZEILEN, (
        f"andere Zeilen auf S.{SEITE} als erwartet – neue Fassung des Textbands? gelesen: {list(pdf)}"
    )
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
    """Jede Fußnote der ÖSG-Vorlage steht so in der RSG-Planungsmatrix des Tabellenbands (Anhang 9, S.239)."""
    from rsg2030.fussnoten import norm, vorlage
    from rsg2030.matrix_extract import kompakt

    with pdfplumber.open(oesg_pdf("Tabellenband")) as pdf:
        seite = kompakt(norm(pdf.pages[239 - 1].extract_text()))
    for z, t in zip(vorlage()["Zeichen"], vorlage()["Text"]):
        assert kompakt(norm(z + t)) in seite, f"{z} {t}"


def test_zeilen_vorlage_wie_tabellenband():
    """Jede Zeilenbeschriftung der ÖSG-Vorlage (oesg_rsgpm_zeilen.csv) steht so in der RSG-Planungsmatrix des
    Tabellenbands (Anhang 9, S.239). Die Platzhalter der Zellen («x», «-», «n.v.») stehen dort mitten in umbrochenen
    Beschriftungen; sie fallen auf beiden Seiten weg (auch «-» in «ÖGK - Planstellen»)."""
    from rsg2030.matrix_extract import kompakt
    from rsg2030.vorlage import zeilen

    def ohne_platzhalter(t: str) -> str:
        return kompakt(" ".join(w for w in t.split() if w not in {"x", "-", "n.v."}))

    with pdfplumber.open(oesg_pdf("Tabellenband")) as pdf:
        seite = ohne_platzhalter(pdf.pages[239 - 1].extract_text())
    for t in zeilen()["Beschriftung"]:
        assert ohne_platzhalter(t) in seite, t


def test_spalten_vorlage_wie_tabellenband():
    """Die Fachspalten der Vorlage (vorlage.SPALTEN_VORLAGE) sind die erste Kopfzeile der RSG-Planungsmatrix im
    Tabellenband (Anhang 9, S.239), ohne Fußnotenzeichen und in derselben Reihenfolge."""
    from rsg2030.vorlage import SPALTEN_VORLAGE

    with pdfplumber.open(oesg_pdf("Tabellenband")) as pdf:
        text = pdf.pages[239 - 1].extract_text()
    kopf = next(z for z in text.splitlines() if z.startswith("AM(4)"))
    gelesen = re.sub(r"\(\d\)", " ", kopf).split()
    assert tuple(gelesen) == SPALTEN_VORLAGE, gelesen


# ---------- VD2021 der Richtwerttabelle aus der Planungsgrundlagenmatrix (Anhang 5) nachrechnen ----------

A5_SEITEN = {"Österreich": 15, "Wien": 28}  # Anhang 5 (Tabellenband S.15, S.28)
# Spaltenkopf der Zeile «Ambulante ärztliche Versorgung», ohne Fußnotenzeichen; «insg» ohne Punkt (split).
A5_KOPF = ("AM", "KIJU", "KJC", "KJP", "CH", "NCH", "IM", "GGH", "NEU", "PSY", "DER", "AU", "HNO", "URO",
           "PCH", "PUL", "ORTR", "MKG", "ZMK", "KFO", "RAD", "NUK", "PMR", "PAT", "insg")  # fmt: skip
A5_SUMME = "Summe ÄAVE im ambulanten Bereich (exkl. WÄ)"
A5_WAE = "Niedergel. Wahlärztinnen/-ärzte (ÄAVE)"
A5_EW = re.compile(r"EW insgesamt \(2021\): ([\d.]+)")
# Der Anhang 5 schneidet fast alles schon wie die Richtwertzeilen: «CH inkl. KJC und PCH» (Fußnote 3),
# «ZMK inkl. Dr.med.dent, Dentisten und KFO» (Fußnote 5), ORTR = «Summe aus OR, UCH und ORTR» (Fußnote 1).
# Nur IM und PUL stehen getrennt – IM = IM + PUL ist die Teilmengen-Lesart («- davon», METHODIK R4).
A5_ZUSCHNITT = {"IM": ("IM", "PUL")}


def _anhang5() -> tuple[dict[tuple[str, str], dict[str, float]], int]:
    """Die beiden ÄAVE-Zeilen (Sachleistung, Wahlärzt:innen) je Seite und die Einwohner ohne Wien."""
    zeilen: dict[tuple[str, str], dict[str, float]] = {}
    ew: dict[str, int] = {}
    with pdfplumber.open(oesg_pdf("Tabellenband")) as pdf:
        for region, seite in A5_SEITEN.items():
            text = pdf.pages[seite - 1].extract_text()
            assert text.split("\n")[1].strip() == region, f"S.{seite} ist nicht die Seite «{region}»"
            ew[region] = int(A5_EW.search(text).group(1).replace(".", ""))  # type: ignore[union-attr]
            for anfang, name in ((A5_SUMME, "SL"), (A5_WAE, "WÄ")):
                zeile = next(z for z in text.split("\n") if z.startswith(anfang))
                werte = zeile.removeprefix(anfang).split()
                assert len(werte) == len(A5_KOPF), (region, anfang, werte)
                zeilen[region, name] = {
                    k: float(w.replace(".", "").replace(",", "."))
                    for k, w in zip(A5_KOPF, werte)
                    if w not in ("-", "n.v.")
                }
    return zeilen, ew["Österreich"] - ew["Wien"]


def test_vd2021_aus_der_planungsgrundlagenmatrix():
    """Die Spalte VD2021 der Richtwerttabelle (Textband S.39) ist exakt nachrechenbar – alle 17 Fächer auf die
    gedruckte Nachkommastelle – aus dem Anhang 5 (Tabellenband S.15, S.28): (Summe ÄAVE exkl. WÄ **plus**
    niedergelassene Wahlärzt:innen), Österreich minus Wien, geteilt durch die Einwohner ohne Wien, × 100.000.

    Damit sind drei Lesarten zugleich Zahl: Die Basis der Richtwerttabelle enthält Wahlärzt:innen (METHODIK R1,
    VD-Definition der Legende; ohne sie weichen 14 der 17 Zeilen ab), die Richtwertzeile IM enthält PUL
    («- davon», R4 – IM allein ergäbe 15,9 statt 18,2), und die Bevölkerung ist die ohne Wien (R3/R7). Für ZMK
    (inkl. KFO), CH (inkl. KJC/PCH) und ORTR bestätigt der Treffer den Schnitt der Anhang-5-Fußnoten, der dort
    schon dem der Richtwertzeilen entspricht."""
    from oesg_methodik.faecher import OESG_ANALYSEKERN

    zeilen, bev = _anhang5()
    assert bev == 7_011_715  # Statistik Austria, 1.1.2021 ohne Wien – dieselbe Zahl wie in METHODIK R7

    def vd(spalten: tuple[str, ...]) -> float:
        aave = sum(
            zeilen["Österreich", block].get(s, 0.0) - zeilen["Wien", block].get(s, 0.0)
            for s in spalten
            for block in ("SL", "WÄ")
        )
        return round(aave / bev * 100000, 1)

    soll = pd.read_csv(OESG_PLANUNGSRICHTWERTE_CSV, sep=";", decimal=",").set_index("Fachrichtung")["VD2021"]
    for fach in OESG_ANALYSEKERN:
        spalten = A5_ZUSCHNITT.get(fach, (fach,))
        assert zeilen["Österreich", "SL"].get(spalten[0]) is not None, f"{fach}: Spalte nicht gelesen"
        assert vd(spalten) == soll[fach], f"{fach}: {vd(spalten)} statt VD2021 {soll[fach]}"
    # Gegenprobe der Teilmengen-Lesart: IM ohne PUL verfehlt die gedruckte VD2021 deutlich
    assert vd(("IM",)) == 15.9 != soll["IM"]
