"""Wo die Daten liegen.

Quellen und Ergebnisse liegen **nicht** im Paket, sondern im Arbeitsordner: standardmäßig der Ordner, aus dem
man den Befehl startet (meist das geklonte Repo), oder der Ordner in der Umgebungsvariable `RSG2030_DATEN`.
So funktioniert dasselbe Paket im Daten-Repo und installiert in einem Analyse-Projekt.

    <Arbeitsordner>/daten_original/   heruntergeladene Quellen (Register: rsg2030/quellen/quellen.csv)
    <Arbeitsordner>/daten_ergebnis/   Long-CSV, Kennzahlen, Audit-Mappe, Laufprotokolle

Die Ordner sind Funktionen, keine Konstanten: Sie werden bei jedem Aufruf aus Arbeitsordner und Umgebung bestimmt,
nicht schon beim Import. Ein Projekt, das das Paket einbindet, kann `RSG2030_DATEN` also auch nach dem Import setzen.

Die Referenztabellen (Richtwerte, Bezirk → Versorgungsregion) gehören zum Paket und liegen in `referenz/`.
"""

from __future__ import annotations

import os
from pathlib import Path


def daten_basis() -> Path:
    """Arbeitsordner: `RSG2030_DATEN`, sonst der aktuelle Ordner."""
    return Path(os.environ.get("RSG2030_DATEN") or Path.cwd()).resolve()


def original_dir() -> Path:
    return daten_basis() / "daten_original"


def ergebnis_dir() -> Path:
    return daten_basis() / "daten_ergebnis"


def statistik_austria_dir() -> Path:
    return original_dir() / "statistik_austria"


# Die drei Bände des ÖSG, wie das Register sie ablegt (Herkunft und Prüfsumme: rsg2030/quellen/quellen.csv).
# Die Namen stehen nur hier: Ein neuer ÖSG-Stand wird an dieser Stelle umgestellt, und tests/test_zitate.py sagt
# dann, welche Seitenangabe der Doku gewandert ist.
OESG_BAENDE = {
    "Textband": "SPG_AT_OSG_G_20261009_8_2026.pdf",
    "Tabellenband": "OeSG_2023_-_Tabellenband__Stand_09.10.2026.pdf",
    "Methodenband": "Methodenband_2025.pdf",
}


def oesg_pdf(band: str) -> Path:
    """Pfad eines ÖSG-Bands («Textband», «Tabellenband», «Methodenband») im Datenordner."""
    return original_dir() / "oesg" / OESG_BAENDE[band]


REFERENZ_DIR = Path(__file__).with_name("referenz")
# Richtwerte ÖSG 2023 Textband S.39, von Hand abgeschrieben (in git)
OESG_PLANUNGSRICHTWERTE_CSV = REFERENZ_DIR / "oesg_planungsrichtwerte.csv"
# Bezirk → Versorgungsregion laut ÖSG 2023 (erzeugt von `regionen_erzeugen.py`)
OESG_REGIONEN_CSV = REFERENZ_DIR / "oesg_regionen.csv"
# Fußnoten der RSG-Planungsmatrix laut ÖSG-Vorlage (Tabellenband Anhang 9, S.239; geprüft in tests/test_referenz.py)
OESG_RSGPM_FUSSNOTEN_CSV = REFERENZ_DIR / "oesg_rsgpm_fussnoten.csv"
# Zeilenbeschriftungen der RSG-Planungsmatrix laut ÖSG-Vorlage (Tabellenband S.239) und ihre Zeile_ID (geprüft in tests/test_referenz.py)
OESG_RSGPM_ZEILEN_CSV = REFERENZ_DIR / "oesg_rsgpm_zeilen.csv"
# Je zitierter ÖSG-Seite ein wörtlicher Anker aus der gepinnten Fassung (geprüft in tests/test_zitate.py)
OESG_ZITATE_CSV = REFERENZ_DIR / "oesg_zitate.csv"
