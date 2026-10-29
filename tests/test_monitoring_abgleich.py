"""Monitoring-Abgleich (rsg2030/scripts/monitoring_abgleich.py): Einlesen und Vergleich an einer kleinen Mappe."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from rsg2030.scripts.monitoring_abgleich import kfo_vergleich, lies_monitoring, vergleiche


def _mappe(pfad: Path, *, plan_kopf: bool = True, planstellen: bool = True) -> None:
    """Aufbau wie in den Kurzfassungen: Fächer ab Spalte D, Beschriftung in Spalte B oder C, Fußnotenzeichen.
    Nach den IST-ÄAVE folgen die Planstellen, dann der PLAN-Abschnitt mit denselben Zeilenbeschriftungen."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Kärnten"
    ws.append([None, "Kärnten"])
    ws.append([None, None, None, "AM/PV", "OR", "UCH", "ORTR", "ZMK(3)", "STR(1)", "gesamt"])
    ws.append([None, None, "IST ÄAVE 2022"])
    ws.append([None, None, "ÄAVE spitalsambulant(4)", 10.04, 1, 2, 3, "-", "n.v.", 99])
    ws.append([None, "ÄAVE niedergelassene Ärztinnen/Ärzte gesamt (mit Vertrag)", None, 100, 0, 0, 0, 50, 0, 150])
    ws.append([None, "IST Kassenplanstellen bzw. Vertragsärztinnen/-ärzte"])
    if planstellen:
        ws.append([None, None, "ÖGK-Planstellen(4)", 200, 5, None, "-", 30, "-", 236])
        ws.append([None, None, "Vertragsärztinnen/-ärzte von BVAEB oder SVS ohne ÖGK-Vertrag", 7, 0, 0, 0, 0, 0, 7])
    if plan_kopf:
        ws.append([None, None, "PLAN ÄAVE - Planungsstand RSG per 12/2023 (RSG 2025)"])
    ws.append([None, None, "ÄAVE spitalsambulant", 888, 0, 0, 0, 0, 0, 888])
    ws.append([None, None, "ÄAVE insgesamt", 999, 0, 0, 0, 0, 0, 999])
    wb.save(pfad)


def test_lies_monitoring(tmp_path: Path) -> None:
    pfad = tmp_path / "kurzfassung.xlsx"
    _mappe(pfad)
    m = lies_monitoring(pfad).set_index(["Zeile_ID", "Fach"])["Monitoring"]
    assert set(lies_monitoring(pfad)["Jahr"]) == {2022}  # aus «IST ÄAVE 2022»
    assert m["spitalsambulant", "AM"] == 10.04
    assert m["spitalsambulant", "ORTR"] == 6  # OR + UCH + ORTR
    assert m["spitalsambulant", "ZMK"] == 0  # «-»
    assert pd.isna(m["spitalsambulant", "STR"])  # «n.v.»; Fußnotenzeichen abgezogen
    assert m["niedergelassen", "AM"] == 100  # Beschriftung in Spalte B
    assert ("spitalsambulant", "OR") not in m.index
    assert m["planstellen_oegk", "AM"] == 200
    assert m["planstellen_oegk", "ORTR"] == 5  # OR 5 + leere Spalte UCH + ORTR «-»
    assert m["planstellen_oegk", "ZMK"] == 30
    assert "insgesamt" not in m.index.get_level_values(0)  # PLAN-Abschnitt nicht mehr gelesen
    assert m["spitalsambulant", "AM"] == 10.04  # nicht die gleichnamige PLAN-Zeile


def test_lies_monitoring_meldet_anderen_aufbau(tmp_path: Path) -> None:
    """Ändert die GÖG den Aufbau, bricht das Einlesen ab, statt still PLAN-Zeilen als IST zu lesen."""
    ohne_plan_kopf, ohne_planstellen = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    _mappe(ohne_plan_kopf, plan_kopf=False)
    _mappe(ohne_planstellen, planstellen=False)
    for pfad in (ohne_plan_kopf, ohne_planstellen):
        with pytest.raises(RuntimeError):
            lies_monitoring(pfad)


def test_vergleiche() -> None:
    vo = pd.DataFrame(
        dict(Land="Kärnten", Jahr=2022, Zeile_ID="spitalsambulant", Fach=["AM", "ORTR", "ZMK"],
             Verordnung=[10.0, 6.2, 0.0], Rundung=0.05)
    )  # fmt: skip
    mon = pd.DataFrame(
        dict(Land=["Kärnten", "Kärnten", "Kärnten", "NÖ"], Jahr=2022, Zeile_ID="spitalsambulant",
             Fach=["AM", "ORTR", "ZMK", "AM"], Monitoring=[10.04, 6.0, 0.0, 5.0])
    )  # fmt: skip
    v = vergleiche(vo, mon).set_index("Fach")
    assert v.loc["AM", "gleich"]  # 10,0 gegen 10,04: innerhalb der Rundung
    assert not v.loc["ORTR", "gleich"]  # 6,2 gegen 6,0
    assert "ZMK" not in v.index  # auf beiden Seiten 0
    assert set(v["Land"]) == {"Kärnten"}  # NÖ hat kein IST 2022


def test_kfo_vergleich() -> None:
    """ZMK und KFO getrennt: Das Monitoring führt ZMK «inkl. KFO», die Summe muss dazu passen. Ohne KFO-Angabe
    (Vorarlberg, Wien) bleibt die Spalte leer, die Summe ist der gedruckte ZMK-Wert."""
    long = pd.DataFrame(
        dict(Land=["OÖ", "OÖ", "Wien"], Ebene="BL", Block="haupt", Abschnitt="IST", Jahr=2022,
             Zeile_ID="planstellen_oegk", Fach=["ZMK", "KFO", "ZMK"], Wert=[381.0, 32.0, 697.0])
    )  # fmt: skip
    mon = pd.DataFrame(
        dict(Land=["OÖ", "Wien"], Jahr=2022, Zeile_ID="planstellen_oegk", Fach="ZMK", Monitoring=[414.0, 697.0])
    )  # fmt: skip
    k = kfo_vergleich(long, mon).set_index("Land")
    assert k.loc["OÖ", "Summe"] == 413.0  # 381 gedruckt + 32 aus der Fußnote
    assert k.loc["OÖ", "Differenz"] == -1.0  # ohne die 32 wären es -33: sie stecken nicht in den 381
    assert pd.isna(k.loc["Wien", "KFO"])  # kein KFO ausgewiesen
    assert k.loc["Wien", "Summe"] == 697.0
    assert k.loc["Wien", "Differenz"] == 0.0
