"""Bevölkerung (Statistik Austria) je BL und Versorgungsregion – gegen veröffentlichte Werte.

Sollwerte als Literale aus den Quellen: ÖSG 2023 Textband S.39 (Wohnbevölkerung 1.1.2021),
Statistik Austria Open Data (Bevölkerung 1.1. je Gemeinde; Bevölkerungsprognose 2025, Hauptszenario).
"""

from __future__ import annotations

import conftest  # noqa: F401
import pandas as pd
import pytest

from oesg_methodik import bevoelkerung as pop
from oesg_methodik.pfade import OESG_REGIONEN_CSV

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
