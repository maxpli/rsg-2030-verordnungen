"""Quelldateien, die die Pipeline liest, im Register `quellen/quellen.csv` (Verwendet = rsg_2030).

Jede Datei steht mit Herkunft (RIS-Dokumentnummer oder URL) und SHA-256-Prüfsumme im Register.
Weicht eine Prüfsumme ab, ist es nicht mehr dieselbe Datei, die ausgelesen und geprüft wurde.
Verwendet = von der Pipeline gelesen: die PDFs aus seiten.csv und die Referenzdateien (Herkunft «URL»);
fehlt eine davon oder ist sie verändert → Abbruch. Die übrigen Dateien prüft `python -m rsg2030 download`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rsg2030.config import VERORDNUNGSSTAND, quellen_dir, seiten_csv
from rsg2030.quellen import lade_quellen, sha256


def lade_dokumente() -> pd.DataFrame:
    """Register-Zeilen von RSG 2030: Verordnungen dieses Stands (RIS, Spalte «Stand» = `VERORDNUNGSSTAND`) und
    Referenzdateien (URL)."""
    q = lade_quellen()
    q = q[q["Verwendet"] == "rsg_2030"]
    return q[(q["Herkunft"] != "RIS") | (q["Stand"] == VERORDNUNGSSTAND)].reset_index(drop=True)


def verwendet(dok: pd.DataFrame) -> pd.Series:
    """Maske: Datei wird von der Pipeline gelesen (PDF laut seiten.csv oder Referenzdatei per URL)."""
    pfad = seiten_csv()
    seiten = set(pd.read_csv(pfad, dtype=str)["Datei"]) if pfad.is_file() else set()
    return dok["Datei"].isin(seiten) | (dok["Herkunft"] == "URL")


def pruefe_dateien(
    dok: pd.DataFrame | None = None, *, nur_verwendet: bool = True, root: Path | None = None
) -> list[str]:
    """Probleme je Datei (fehlt / Prüfsumme weicht ab); leere Liste = alles in Ordnung."""
    dok = lade_dokumente() if dok is None else dok
    root = root or quellen_dir()
    if nur_verwendet:
        dok = dok[verwendet(dok)]
    probleme: list[str] = []
    for _, d in dok.iterrows():
        p = root / d["Datei"]
        if not p.is_file():
            probleme.append(
                f"fehlt: {d['Datei']} (Herkunft {d['Herkunft']} {d['Kennung']}) → python -m rsg2030 download"
            )
        elif sha256(p) != d["SHA256"]:
            probleme.append(f"Prüfsumme weicht ab: {d['Datei']} – nicht mehr die geprüfte Fassung")
    return probleme
