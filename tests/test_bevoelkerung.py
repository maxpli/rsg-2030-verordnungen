"""Bevölkerung (Statistik Austria) je BL und Versorgungsregion – gegen veröffentlichte Werte.

Sollwerte als Literale aus den Quellen: ÖSG 2023 Textband S.39 (Wohnbevölkerung 1.1.2021),
Statistik Austria Open Data (Bevölkerung 1.1. je Gemeinde; Bevölkerungsprognose 2025, Hauptszenario).
"""

from __future__ import annotations

import re

import conftest  # noqa: F401
import pandas as pd
import pdfplumber
import pytest

from oesg_methodik import bevoelkerung as pop
from oesg_methodik.pfade import OESG_REGIONEN_CSV, oesg_pdf

pytestmark = pytest.mark.slow  # liest die Open-Data-Dateien (~10 s)


@pytest.fixture(scope="module")
def regionen():
    return pd.read_csv(OESG_REGIONEN_CSV)


@pytest.fixture(scope="module")
def ist_jahre_():
    """IST-Jahr je Land aus den Matrizen (wie in der Analyse)."""
    from rsg2030.analyse_eingang import ist_jahre, lade_matrix_long

    j = ist_jahre(lade_matrix_long())
    assert j == {
        "Burgenland": 2022,
        "Kärnten": 2022,
        "NÖ": 2023,
        "OÖ": 2022,
        "Salzburg": 2023,
        "Steiermark": 2022,
        "Tirol": 2023,
        "Vorarlberg": 2023,
        "Wien": 2022,
    }
    return j


def test_ist_wie_oesg_2021(regionen):
    """ÖSG-Wohnbevölkerung 2021: 8.932.664, ohne Wien 7.011.715 (Textband S.39)."""
    bl = pop.bevoelkerung_bl_ist((2021,), regionen).set_index("Land")["Bevoelkerung"]
    assert bl.sum() == 8_932_664
    assert bl.drop("Wien").sum() == 7_011_715


def test_alle_bezirke_zugeordnet(regionen):
    bez = pop.bevoelkerung_bezirke((2023,))
    assert len(bez) == 116 and set(bez["Bezirk"]) == set(regionen["Bezirk"])


def test_prognose_1_1_2030():
    """Hauptszenario der Prognose 2025, Bevölkerung zum Jahresanfang 2030."""
    fc = pop.bevoelkerung_prognose(2030).set_index("Land")["Bevoelkerung"]
    assert fc.sum() == 9_321_070
    assert fc["Wien"] == 2_101_123 and fc["NÖ"] == 1_742_943


def test_vr_summieren_sich_zum_bl(regionen, ist_jahre_):
    vr = pop.bevoelkerung_vr(regionen, ist_jahre=ist_jahre_)
    assert vr["VR"].nunique() == 32
    s = vr.groupby(["Abschnitt", "Land"])["Bevoelkerung"].sum()
    fc = pop.bevoelkerung_prognose(2030).set_index("Land")["Bevoelkerung"]
    assert (s["PLAN"] - fc).abs().max() < 1e-6
    ist = pop.bevoelkerung_bl_ist(tuple(sorted(set(ist_jahre_.values()))), regionen)
    ist = ist[ist["Jahr"] == ist["Land"].map(ist_jahre_)].set_index("Land")["Bevoelkerung"]
    assert (s["IST"] - ist).abs().max() == 0


def test_vr_oerok_anteil_vorarlberg(regionen, ist_jahre_):
    """Vorarlberg (RSG-Textteil S.6): VR 81 hat 2030 einen Anteil von 238.456 / 421.445 = 56,58 % –
    dieselbe ÖROK-Aufteilung wie hier."""
    vr = pop.bevoelkerung_vr(regionen, ist_jahre=ist_jahre_)
    p = vr[(vr["Abschnitt"] == "PLAN") & (vr["Land"] == "Vorarlberg")].set_index("VR")["Bevoelkerung"]
    assert p["81"] / p.sum() == pytest.approx(238_456 / 421_445, abs=5e-4)


def test_vr_oerok_anteil_kaernten(regionen, ist_jahre_):
    """Kärnten (Anhang S.19): Prognose 2030 nennt 339.930 für die VR 21 von 559.783 für Kärnten = 60,73 % –
    dieselbe ÖROK-Aufteilung wie hier (das zweite Land neben Vorarlberg, das den Anteil selbst druckt)."""
    vr = pop.bevoelkerung_vr(regionen, ist_jahre=ist_jahre_)
    p = vr[(vr["Abschnitt"] == "PLAN") & (vr["Land"] == "Kärnten")].set_index("VR")["Bevoelkerung"]
    assert p["21"] / p.sum() == pytest.approx(339_930 / 559_783, abs=5e-4)


# «EW insgesamt (2021)» je Versorgungsregion aus dem Anhang 5 des Tabellenbands (eine Seite je VR), als Literal
# mit PDF-Seite wie RICHTWERT_ZEILEN in test_referenz.py: So fällt ein neuer ÖSG-Stand oder eine verrutschte
# Seite mit Region und Wert auf. VR → (Seite, EW).
VR_EW_2021_TABELLENBAND = {
    "11": (29, 198_922), "12": (30, 97_088),
    "21": (31, 340_253), "22": (32, 221_836),
    "31": (33, 400_574), "32": (34, 134_471), "33": (35, 324_588), "34": (36, 583_672), "35": (37, 247_574),
    "41": (38, 358_928), "42": (39, 235_733), "43": (40, 279_021), "44": (41, 156_051), "45": (42, 240_095),
    "46": (43, 225_780),
    "51": (44, 371_032), "52": (45, 189_678),
    "61": (46, 448_987), "62": (47, 79_592), "63": (48, 157_205), "64": (49, 267_047), "65": (50, 195_441),
    "66": (51, 98_805),
    "71": (52, 397_213), "72": (53, 138_322), "73": (54, 175_756), "74": (55, 48_814),
    "81": (56, 225_812), "82": (57, 173_425),
    "91": (58, 831_855), "92": (59, 716_372), "93": (60, 372_722),
}  # fmt: skip
# Bekannte Abweichung unserer Bezirks-Summe vom Tabellenband (METHODIK, «Bekannte Grenzen»; DATEN.md, Fallstricke):
# vermutlich zählt der ÖSG die Gemeinde Sankt Josef (Weststeiermark) zur VR 64, der Bezirk Deutschlandsberg liegt
# laut GÖG-Gliederung ganz in VR 65. Unbestätigt (docs/offene_punkte.md, Rückfrage an die GÖG).
ABWEICHUNG_VR_64_65 = {"64": -1_671, "65": 1_671}


def test_vr_ew_2021_wie_tabellenband():
    """Jede VR-Seite des Anhangs 5 (Tabellenband S.29–60) trägt die Region und das «EW insgesamt (2021)» des
    Literals – ein neuer ÖSG-Stand oder eine verrutschte Seite fällt hier mit Seite und Wert auf."""
    titel = re.compile(r"Versorgungsregion (\d{2}):")
    ew_muster = re.compile(r"EW insgesamt \(2021\): ([\d.]+)")
    with pdfplumber.open(oesg_pdf("Tabellenband")) as pdf:
        for vr, (seite, ew) in VR_EW_2021_TABELLENBAND.items():
            zeilen = pdf.pages[seite - 1].extract_text().split("\n")
            m = titel.match(zeilen[1].strip())
            assert m is not None and m.group(1) == vr, f"S.{seite} ist nicht die Seite der VR {vr}: {zeilen[1][:60]}"
            e = ew_muster.search(zeilen[2])
            assert e is not None and int(e.group(1).replace(".", "")) == ew, f"VR {vr} (S.{seite}): {zeilen[2][:60]}"


def test_vr_bezirkssumme_wie_tabellenband(regionen):
    """Unsere VR-Bevölkerung 1.1.2021 (Summe der Bezirke laut GÖG-Gliederung) trifft das «EW insgesamt (2021)» des
    Tabellenbands in 30 von 32 VR exakt; VR 64/65 weichen um genau ±1.671 ab – als bekannte Abweichung
    festgehalten, damit jede Änderung auffällt. Der zweite Teil hält die Vermutung dazu nachrechenbar: Sankt Josef
    (Weststeiermark), GKZ 60326, ist die einzige Gemeinde des Bezirks Deutschlandsberg mit genau 1.671 EW."""
    unser = pop._mit_region(pop.bevoelkerung_bezirke((2021,)), regionen).groupby("VR")["Bevoelkerung"].sum()
    unser.index = unser.index.astype(str)
    for vr, (seite, ew) in VR_EW_2021_TABELLENBAND.items():
        soll = ew + ABWEICHUNG_VR_64_65.get(vr, 0)
        assert unser.loc[vr] == soll, f"VR {vr}: {int(unser.loc[vr])} statt {soll} (Tabellenband S.{seite}: {ew})"
    roh = pd.read_csv(pop._bevstand_csv(2021), sep=";")
    im_bezirk = roh[roh["C-GRGEMAKT-0"].astype(str).str.startswith("GRGEMAKT-603")]
    je_gemeinde = im_bezirk.groupby("C-GRGEMAKT-0")["F-ISIS-1"].sum()
    assert je_gemeinde["GRGEMAKT-60326"] == 1_671 and (je_gemeinde == 1_671).sum() == 1
