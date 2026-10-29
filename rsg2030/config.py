"""RSG-2030-Konstanten: Dateinamen, Eingaben je Verordnungsstand, Ordner.

Daten-Ordner kommen aus `oesg_methodik.pfade` (Arbeitsordner bzw. `RSG2030_DATEN`). Für einen Lauf in einem
leeren Ordner (Test «frisch geklont») lassen sie sich einzeln umlenken: RSG2030_QUELLEN_DIR,
RSG2030_AUSGABE_DIR, RSG2030_EINGABEN_DIR. Ordner und Eingabedateien sind Funktionen: Sie werden bei jedem Aufruf
bestimmt, nicht beim Import (siehe `oesg_methodik.pfade`).
"""

from __future__ import annotations

import os
from pathlib import Path

from oesg_methodik.pfade import ergebnis_dir, original_dir

AUDIT_DATEI = "RSG_2030_Planungsmatrizen.xlsx"
LONG_DATEI = "RSG_2030_Planungsmatrizen.csv"
VERSORGUNGSDICHTE_DATEI = "RSG_2030_Versorgungsdichte.csv"
STELLEN_DATEI = "RSG_2030_Stellen.csv"

VERORDNUNGSSTAND = "2026"
"""Ordner der Eingaben unter `eingaben/` (ein neuer Stand: neuer Ordner, hier umstellen)."""


def ausgabe_dir() -> Path:
    """Ergebnisse (Planungsmatrizen als CSV und Excel-Mappe, Versorgungsdichte, Stellen, Laufprotokolle) →
    «daten_ergebnis/»."""
    return Path(os.environ.get("RSG2030_AUSGABE_DIR") or ergebnis_dir())


def quellen_dir() -> Path:
    """Heruntergeladene Quelldateien (nicht in git; Pfade in quellen/quellen.csv und seiten.csv sind relativ dazu)."""
    return Path(os.environ.get("RSG2030_QUELLEN_DIR") or original_dir())


def eingaben_dir() -> Path:
    """Alles, was nicht automatisch aus dem PDF kommt – je Verordnungsstand ein Ordner (im Paket, in git)."""
    return Path(os.environ.get("RSG2030_EINGABEN_DIR") or Path(__file__).with_name("eingaben") / VERORDNUNGSSTAND)


def seiten_csv() -> Path:
    return eingaben_dir() / "seiten.csv"


def korrekturen_csv() -> Path:
    return eingaben_dir() / "korrekturen.csv"


def bekannte_abweichungen_csv() -> Path:
    return eingaben_dir() / "bekannte_abweichungen.csv"


def manuell_xlsx() -> Path:
    return eingaben_dir() / "manuell.xlsx"


def freigabe_xlsx() -> Path:
    return eingaben_dir() / "freigabe.xlsx"
