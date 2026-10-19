"""Monitoring-Abgleich (rsg2030/scripts/monitoring_abgleich.py): Einlesen und Vergleich an einer kleinen Mappe."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd

from rsg2030.scripts.monitoring_abgleich import lies_monitoring, vergleiche


def _mappe(pfad: Path) -> None:
    """Aufbau wie in den Kurzfassungen: Fächer ab Spalte D, Beschriftung in Spalte B oder C, Fußnotenzeichen."""
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
    assert "insgesamt" not in m.index.get_level_values(0)  # nach den Planstellen nicht mehr gelesen


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
