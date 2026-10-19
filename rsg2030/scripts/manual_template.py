"""Erfassungs-Workbook für Bildseiten (`eingaben/2026/manuell.xlsx`) anlegen bzw. ergänzen.

Die Zeilenstruktur (Block × Abschnitt × Zeile, Fachspalten) wird von einer per Parser
gelesenen Matrix desselben Bundeslands übernommen (erste andere VR mit Textebene, sonst BL).
Meldet `python -m rsg2030 daten` «bitte abtippen», legt dieser Befehl die fehlenden Blätter an. Bestehende Zeilen und
Werte bleiben unverändert; fehlende Zeilen werden leer angehängt. Excel vorher schließen.

    python -m rsg2030 manuell
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

import openpyxl
import pandas as pd

from rsg2030.config import manuell_xlsx
from rsg2030.manuell import ManuelleMatrix, lese_manuell, manuelle_matrizen, schreibe_manuell
from rsg2030.matrix_extract import hat_textebene, lese_matrix
from rsg2030.protokoll import einrichten
from rsg2030.seitenregister import lade_seitenregister
from rsg2030.specs import KANONISCHE_ZEILEN

log = logging.getLogger(__name__)

ID_SPALTEN = ["Abschnitt", "Jahr", "Block", "Zeile_ID", "Zeile"]

# Labels, deren PDF-Text gesperrt gesetzt ist («I S T A n z a h l …»)
_LABEL = {
    "amb_standorte": "IST Anzahl Ambulatorien-Standorte (mit Kassenvertrag und kasseneigen) gesamt",
    "umr_niedergelassen": "REGIOMED-Umrechnungsfaktor für niedergelassene ÄrztInnen (mit Kassenvertrag)",
    "umr_wahl": "Umrechnungsfaktor für WahlärztInnen und in selbstständigen Ambulatorien (ohne Kassenvertrag)",
}


def zeilen_label(zeile_id: str, roh: object) -> str:
    """Lesbares Zeilenlabel: PDF-Text, außer er ist gesperrt gesetzt oder fehlt."""
    if isinstance(roh, str) and len(re.findall(r"(?<!\S)\w(?!\S)", roh)) < 3 and "manuell" not in roh.lower():
        return roh
    return _LABEL.get(zeile_id) or KANONISCHE_ZEILEN.get(zeile_id) or (roh if isinstance(roh, str) else "")


def _referenz(m: ManuelleMatrix) -> pd.DataFrame:
    """Zeilenstruktur aus einer lesbaren Matrix desselben Landes (andere VR bevorzugt, sonst BL)."""
    src = next(s for s in lade_seitenregister() if s.land == m.land)
    for vr in src.vr:
        if vr.region_id != m.region_id and hat_textebene(src.pdf, vr.seite_idx):
            r = lese_matrix(
                src.pdf, (vr.seite_idx, *vr.folgeseiten_idx), land=m.land, ebene="VR", region_id=vr.region_id
            )
            return pd.DataFrame(r.datensaetze)
    if m.ebene != "BL" and hat_textebene(src.pdf, src.seite_idx):
        return pd.DataFrame(
            lese_matrix(src.pdf, (src.seite_idx,), land=m.land, ebene="BL", region_id=m.land).datensaetze
        )
    raise ValueError(f"{m.land}: keine Matrix mit Textebene als Vorlage für {m.blatt}")


def ergaenze(m: ManuelleMatrix, df: pd.DataFrame | None) -> tuple[pd.DataFrame, int]:
    ref = _referenz(m)
    faecher = list(dict.fromkeys(ref["Fach"]))
    faecher = [f for f in faecher if f != "gesamt"] + ["gesamt"]
    zeilen = ref[["Block", "Abschnitt", "Jahr", "Zeile_ID", "Zeile_PDF_roh"]].drop_duplicates(
        ["Block", "Abschnitt", "Zeile_ID"]
    )
    if df is None:
        df = pd.DataFrame(columns=[*ID_SPALTEN, "Quelle"], dtype=object)

    have = set(zip(df["Block"], df["Abschnitt"], df["Zeile_ID"]))
    neu = [
        {
            "Abschnitt": z["Abschnitt"],
            "Jahr": "" if pd.isna(z["Jahr"]) else str(int(z["Jahr"])),
            "Block": z["Block"],
            "Zeile_ID": z["Zeile_ID"],
            "Zeile": zeilen_label(z["Zeile_ID"], z["Zeile_PDF_roh"]),
            "Quelle": f"{m.pdf} S.{m.seite} (manuell)",
        }
        for _, z in zeilen.iterrows()
        if (z["Block"], z["Abschnitt"], z["Zeile_ID"]) not in have
    ]
    out = pd.concat([df, pd.DataFrame(neu, dtype=object)], ignore_index=True)
    for f in faecher:
        if f not in out:
            out[f] = None
    rest = [c for c in out.columns if c not in ID_SPALTEN and c != "Quelle"]
    return out[ID_SPALTEN + rest + ["Quelle"]], len(neu)


def vorlagen_anlegen() -> dict[str, int]:
    """Für jede Bildseite ein Blatt in manuell.xlsx anlegen bzw. fehlende Zeilen leer ergänzen.

    Vorhandene Werte bleiben erhalten. Rückgabe: Blatt → Anzahl neu angelegter Zeilen.
    """
    matrizen = manuelle_matrizen()
    pfad = manuell_xlsx()
    if pfad.is_file():
        wb = openpyxl.load_workbook(pfad, read_only=True)
        fremd = set(wb.sheetnames) - {"Anleitung"} - {m.blatt for m in matrizen}
        wb.close()
        if fremd:
            raise ValueError(f"{pfad.name}: Blätter ohne Bildseite in seiten.csv: {sorted(fremd)}")
    blaetter, neu = {}, {}
    for m in matrizen:
        blaetter[m.blatt], neu[m.blatt] = ergaenze(m, lese_manuell(m))
    if any(neu.values()) or not pfad.is_file():
        schreibe_manuell(blaetter, pfad)
    return neu


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 manuell", description="Blätter für Bildseiten in manuell.xlsx anlegen"
    ).parse_args(argv)
    for blatt, n in vorlagen_anlegen().items():
        log.info(f"{blatt}: {n} leere Zeilen ergänzt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
