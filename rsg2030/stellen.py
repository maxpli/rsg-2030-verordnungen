"""Tabelle Stellen schreiben: vertragsärztliche Planstellen (IST) und Sachleistungsstellen (PLAN) im ÖSG-Zuschnitt,
je BL und VR, je Stellen-Zeile und Richtwert-Fach.

Warum es die Datei gibt: Die Tabelle Versorgungsdichte führt die ÄAVE im ÖSG-Zuschnitt (ZMK inkl. KFO, IM inkl. PUL,
CH inkl. KJC/PCH), die Stellen stehen in den Planungsmatrizen aber je **Matrixspalte**. Wer beides gegenüberstellt,
müsste den Zuschnitt sonst selbst nachbauen – und zwar genau so, sonst vergleicht er verschiedene Fächer. Geschnitten
wird deshalb mit derselben Funktion wie die ÄAVE (`oesg_methodik.faecher.summe_im_zuschnitt`).

Was die Datei **nicht** tut: ableiten. Sie führt die gedruckten Zeilen; eine Gesamtzeile gibt es nur, wo das Land sie
druckt (Wien). Spalten und Fallstricke: docs/DATEN.md; Belege: docs/METHODIK.md, «Stellen».

    python -m rsg2030 stellen
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from oesg_methodik.stellen_eingang import OHNE_PROZENT
from rsg2030.abgleich import gleiche_ab
from rsg2030.analyse_eingang import stellen_eingang
from rsg2030.config import STELLEN_DATEI, ausgabe_dir
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll

log = logging.getLogger(__name__)

CSV_FORMAT = {"index": False, "lineterminator": "\n"}


def baue_stellen() -> pd.DataFrame:
    return stellen_eingang()


def stellen_csv() -> Path:
    return ausgabe_dir() / STELLEN_DATEI


def ohne_anteil(stellen: pd.DataFrame) -> pd.DataFrame:
    """Zeilen mit Stellen > 0, für die kein Maximalanteil gerechnet werden konnte, weil er für einen Teil der Stellen
    nicht gedruckt ist. Ein Anteil, der nur einen Teil der Zeile abdeckt, wäre irreführend – deshalb bleibt er leer,
    und der Lauf sagt es. Dass es solche Zeilen heute nicht gibt, hält `tests/test_stellen.py` fest; beim Auslesen
    meldet sie schon `checks.pruefe_prozent_gewichtet` («% fehlt bei Stellen > 0», Tabellenband S.232)."""
    kann = ~stellen["Zeile_ID"].isin(OHNE_PROZENT)
    return stellen[kann & (stellen["Stellen"] > 0) & stellen["Max_VAEP_Stellen"].isna()]


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 stellen",
        description="Planstellen und Sachleistungsstellen im ÖSG-Zuschnitt je BL und VR",
    ).parse_args(argv)
    s = baue_stellen()
    ziel = stellen_csv()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(ziel, **CSV_FORMAT)
    log.info(f"{ziel.name}: {len(s)} Zeilen")
    log.info(s.groupby(["Ebene", "Abschnitt", "Zeile_ID"], sort=False).size().unstack().to_string())
    offen = ohne_anteil(s)
    if offen.empty:
        log.info("   ✓ Maximalanteil: für jede Stelle ist einer gedruckt")
    else:
        log.warning(f"   ✗ {len(offen)} Zeilen mit Stellen > 0 ohne Maximalanteil – Anteil bleibt leer:")
        for r in offen.head(10).itertuples():
            log.warning(f"      {r.Land} {r.Ebene} {r.Region_ID} {r.Abschnitt} {r.Zeile_ID} {r.Fach}: {r.Stellen:g}")
    gleich = gleiche_ab(ziel)
    schreibe_laufprotokoll(
        ziel.parent, "stellen", [ziel], {"Abgleich_Version": gleich, "Zeilen_ohne_Maximalanteil": len(offen)}
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
