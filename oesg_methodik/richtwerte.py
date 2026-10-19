"""ÖSG-Planungsrichtwerte ambulant (ÖSG 2023 Textband S. 37), Planungshorizont 2030.

Quelle: `referenz/oesg_planungsrichtwerte.csv` (von Hand aus dem Textband abgeschrieben, in git).
"""

from __future__ import annotations

import pandas as pd

from oesg_methodik.faecher import OESG_ANALYSEKERN
from oesg_methodik.pfade import OESG_PLANUNGSRICHTWERTE_CSV


def richtwerte_fuer_vd(ref: pd.DataFrame) -> pd.DataFrame:
    """Richtwert-Zeilen, gegen die RSG-ÄAVE geprüft werden: die Fächer des Zuschnitts (`faecher.ZUSCHNITT`) mit VDmin.

    Die übrigen ÖSG-Zeilen haben kein Soll-Intervall («*»: KJC, NCH, PCH) oder keine Richtwertzeile (AN, STR, RAD …)."""
    return ref[ref["Fachrichtung"].isin(OESG_ANALYSEKERN) & ref["VDmin"].notna()].copy()


def lade_richtwerte() -> pd.DataFrame:
    if not OESG_PLANUNGSRICHTWERTE_CSV.exists():
        return pd.DataFrame(columns=["Fachrichtung", "VDmin", "VDmax"])

    ref = pd.read_csv(OESG_PLANUNGSRICHTWERTE_CSV, sep=";")
    numeric_cols = ["Err_Min", "VDmin", "VDmax", "VD2021", "BEVmin"]
    for col in numeric_cols:
        if col in ref.columns:
            ref[col] = ref[col].astype(str).str.replace(",", ".", regex=False)
            ref[col] = pd.to_numeric(ref[col], errors="coerce")

    keep = [
        c
        for c in [
            "Fachrichtung",
            "OESG_Code",
            "Err_Min",
            "VDmin",
            "VDmax",
            "VD2021",
            "BEVmin",
            "Fussnote",
            "Quelle",
            "Anmerkung",
        ]
        if c in ref.columns
    ]
    return ref[keep]
