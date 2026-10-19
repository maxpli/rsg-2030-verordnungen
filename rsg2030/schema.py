"""Vertrag der Long-CSV `RSG_2030_Planungsmatrizen.csv` – eine Stelle für Spalten, Schlüssel und Regeln.

Eine Zeile je Zelle: Region × Block × Abschnitt × Zeile × Fach. Extraktion, Audit-Mappe und Analyse
nutzen dieselben Namen und dieselbe Regel für den maßgeblichen Block (`bl_long`).
`tests/test_matrix.py::test_long_csv_schema` prüft die Datei gegen diesen Vertrag.
"""

from __future__ import annotations

import pandas as pd

from oesg_methodik import BUNDESLAENDER

# Spalten in dieser Reihenfolge
LONG_SPALTEN = [
    "Land",
    "Ebene",
    "Region_ID",
    "Region_Name",
    "Block",
    "Abschnitt",
    "Jahr",
    "Zeile_ID",
    "Einheit",
    "Fach",
    "Wert",
    "Roh",
    "Rundung",
    "Quelle",
    "Regel",
    "Zeile_PDF_roh",
    "PDF",
    "Seite",
]
MATRIX = ["Land", "Ebene", "Region_ID", "Block", "Abschnitt"]
ZELLE = [*MATRIX, "Zeile_ID", "Fach"]
"""Eindeutiger Schlüssel einer Zelle."""

LAENDER = BUNDESLAENDER
"""Kurznamen der neun Länder in der Long-CSV (eine Liste für beide Pakete)."""
EBENEN = {"BL", "VR"}
ABSCHNITTE = {"IST", "PLAN"}
QUELLEN = {"PDF", "manuell", "korrigiert", "abgeleitet"}
"""PDF = ausgelesen · manuell = Bildseite, von Hand erfasst · korrigiert = Regel aus korrekturen.csv ·
abgeleitet = nicht im PDF ausgewiesen, aus PDF-Zeilen derselben Matrix gerechnet (`ableitungen.py`)."""
EINHEITEN = {"ÄAVE", "SVE", "Stellen", "Anzahl", "Prozent", "Faktor"}

GESAMT = "gesamt"
"""Fachspalte «gesamt» (Zeilensumme laut PDF)."""

# Block «haupt» = Matrix in der Planungsgröße des Landes (ÄAVE oder SVE);
# Block «aequivalent» = Zusatzblock «sofern Planungsgröße nicht ÄAVE gemäß ÖSG» (SVE-Planung).
BLOCK_HAUPT = "haupt"
BLOCK_AEQ = "aequivalent"

# Fachspalten der Long-CSV: die Kürzel der ÖSG-Vorlage der RSG-Planungsmatrix (Tabellenband Anhang 9, S.259), ohne
# Fußnotenzeichen; dazu KFO, das einige Länder als eigene Spalte führen (in der Vorlage nicht vorgesehen). Spaltenköpfe im
# PDF bildet `specs.fachspalte` darauf ab. Den Zuschnitt für die Richtwerte (z. B. ZMK = ZMK + KFO) macht erst die
# Analyse (`oesg_methodik.faecher`, docs/METHODIK.md R4).
FACHSPALTEN: tuple[str, ...] = (
    "AM",
    "AN",
    "KIJU",
    "KJC",
    "KJP",
    "CH",
    "NCH",
    "IM",
    "GGH",
    "NEU",
    "PSY",
    "DER",
    "AU",
    "HNO",
    "URO",
    "PCH",
    "PUL",
    "ORTR",
    "MKG",
    "ZMK",
    "KFO",
    "STR",
    "RAD",
    "NUK",
    "PMR",
    "PAT",
    "LAB",
    "SON/IDB",
)


def massgeblicher_block(bl: pd.DataFrame) -> str:
    """«aequivalent», wenn die BL-Matrix diesen Block hat (SVE-Planung: Burgenland, Kärnten,
    Steiermark), sonst «haupt». Abgeleitet aus den Daten, nicht aus einer Länderliste."""
    return BLOCK_AEQ if (bl["Block"] == BLOCK_AEQ).any() else BLOCK_HAUPT


def matrix_long(long: pd.DataFrame, land: str, ebene: str = "BL", region_id: str | None = None) -> pd.DataFrame:
    """Zeilen einer Matrix (BL oder VR): maßgeblicher Block (dessen ÄAVE sind mit den ÄAVE der übrigen
    Länder vergleichbar), ergänzt um Zeilen, die nur im anderen Block stehen (Planstellen, Sachleistungsstellen, …)."""
    m = long[(long["Land"] == land) & (long["Ebene"] == ebene)]
    if region_id is not None:
        m = m[m["Region_ID"].astype(str) == str(region_id)]
    main = massgeblicher_block(m)
    primary = m[m["Block"] == main]
    have = set(zip(primary["Abschnitt"], primary["Zeile_ID"]))
    neu = pd.Series([k not in have for k in zip(m["Abschnitt"], m["Zeile_ID"])], index=m.index, dtype=bool)
    return pd.concat([primary, m[(m["Block"] != main) & neu]])


def bl_long(long: pd.DataFrame, land: str) -> pd.DataFrame:
    """BL-Matrix eines Landes, siehe `matrix_long`."""
    return matrix_long(long, land, "BL")
