"""ÖSG «Regionale Gliederung» (Excel von goeg.at) → `referenz/oesg_regionen.csv`.

Eine Zeile je politischem Bezirk mit Versorgungszone, Bundesland und Versorgungsregion
(ÖSG 2023, Gebietsstand 2019: 4 VZ, 9 BL, 32 VR, 116 Bezirke). Quelle siehe rsg2030/quellen/quellen.csv.
Nur nötig, wenn die GÖG eine neue Gliederung veröffentlicht; das Ergebnis liegt in git.

    python -m oesg_methodik.regionen_erzeugen
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from oesg_methodik.pfade import OESG_REGIONEN_CSV, original_dir

log = logging.getLogger(__name__)

QUELLE = Path("oesg") / "Regionale_Gliederung_Stand_2023.xlsx"
"""Relativ zu `daten_original/`."""
SPALTEN = ["VZ", "VZ_Name", "BL_Nr", "Bundesland", "VR", "VR_Name", "Bezirk", "Bezirk_Name"]


def lese(path: Path | None = None) -> pd.DataFrame:
    path = path or original_dir() / QUELLE
    df = pd.read_excel(path, header=None, skiprows=9).iloc[:, :8]
    df.columns = SPALTEN
    df = df.dropna(subset=["VR", "Bezirk"])
    for c in ("VZ", "BL_Nr", "VR", "Bezirk"):
        df[c] = df[c].astype(int)
    return df.reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        prog="python -m oesg_methodik.regionen_erzeugen", description="ÖSG-Gliederung → referenz/oesg_regionen.csv"
    ).parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    df = lese()
    if (df["VR"].nunique(), len(df)) != (32, 116):
        log.error(f"❌ erwartet 32 VR und 116 Bezirke, gelesen {df['VR'].nunique()} VR, {len(df)} Bezirke")
        return 1
    OESG_REGIONEN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OESG_REGIONEN_CSV, index=False, lineterminator="\n")
    log.info(f"{OESG_REGIONEN_CSV.name}: {df['VR'].nunique()} VR, {len(df)} Bezirke")
    return 0


if __name__ == "__main__":
    sys.exit(main())
