"""Tabelle Versorgungsdichte schreiben: ÄAVE im ÖSG-Zuschnitt, Versorgungsdichte und Lage zum Soll-Intervall je BL und
VR, IST und PLAN, je ÄAVE-Zeile (spitalsambulant, extramural, insgesamt, pve).

Setzt die Teile zusammen: ÄAVE-Eingang aus den Planungsmatrizen (`analyse_eingang.aave_eingang`) → Bevölkerung und
Richtwerte nach ÖSG-Methode → `oesg_methodik.dichte.kennzahlen`. Spalten und Bedeutung: docs/DATEN.md.

    python -m rsg2030 versorgungsdichte
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from oesg_methodik.bevoelkerung import bevoelkerung_fuer, lade_regionen, prognose_jahrgang
from oesg_methodik.dichte import kennzahlen
from oesg_methodik.richtwerte import lade_richtwerte
from rsg2030.abgleich import gleiche_ab
from rsg2030.analyse_eingang import aave_eingang
from rsg2030.config import VERSORGUNGSDICHTE_DATEI, ausgabe_dir
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll

log = logging.getLogger(__name__)

CSV_FORMAT = {"index": False, "lineterminator": "\n"}


def baue_versorgungsdichte() -> pd.DataFrame:
    aave = aave_eingang()
    return kennzahlen(aave, bevoelkerung_fuer(aave, lade_regionen()), lade_richtwerte())


def versorgungsdichte_csv() -> Path:
    return ausgabe_dir() / VERSORGUNGSDICHTE_DATEI


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 versorgungsdichte",
        description="ÄAVE im ÖSG-Zuschnitt, Versorgungsdichte und Lage zum Soll-Intervall je BL und VR",
    ).parse_args(argv)
    k = baue_versorgungsdichte()
    ziel = versorgungsdichte_csv()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    k.to_csv(ziel, **CSV_FORMAT)
    log.info(f"{ziel.name}: {len(k)} Zeilen")
    log.info(k.groupby(["Ebene", "Abschnitt", "Zeile_ID"], sort=False).size().unstack().to_string())
    jahrgang = prognose_jahrgang()
    log.info(f"Bevölkerung PLAN 2030: Bevölkerungsprognose {jahrgang} von Statistik Austria, Hauptszenario")
    gleich = gleiche_ab(ziel)
    schreibe_laufprotokoll(
        ziel.parent, "versorgungsdichte", [ziel], {"Abgleich_Version": gleich, "Prognose_Jahrgang": jahrgang}
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
