"""Fachspalten- und Zeilennamen der RSG-2030-Planungsmatrizen.

Die Fachspaltennamen im Output (z. B. «AM», «KJC», «ZMK», «KFO», «SON/IDB») sind `schema.FACHSPALTEN`;
`oesg_methodik.faecher.aave_fach` fasst sie zum ÖSG-Zuschnitt zusammen (docs/METHODIK.md, R4).
"""

from __future__ import annotations

import re

from rsg2030.schema import FACHSPALTEN

# RSG-2030-Spaltenkopf → einheitliche Fachspalte (Kürzel wie in den RSG-Kurzfassungen der GÖG)
_FACH_MAP: dict[str, str] = {
    "AM": "AM",
    "AM/PV": "AM",
    "AM/PV*": "AM",
    "AM*": "AM",
    "AM(3)": "AM",
    "AM(4)": "AM",
    "AM(8)": "AM",
    "AN": "AN",
    "KIJU": "KIJU",
    "KIN": "KIJU",
    "KJC": "KJC",
    "KJC(1)": "KJC",
    "KJC(2)": "KJC",
    "KJC*": "KJC",
    "KJP": "KJP",
    "KJP(2)": "KJP",
    "KJP(6)": "KJP",
    "KJP(7)": "KJP",
    "CH": "CH",
    "CHI": "CH",
    "CH(8)": "CH",
    "CH*": "CH",
    "NCH": "NCH",
    "NCH(1)": "NCH",
    "NCH(3)": "NCH",
    "NCH*": "NCH",
    "IM": "IM",
    "GGH": "GGH",
    "NEU": "NEU",
    "PSY": "PSY",
    "DER": "DER",
    "AU": "AU",
    "AUG": "AU",
    "HNO": "HNO",
    "URO": "URO",
    "PCH": "PCH",
    "PCH(1)": "PCH",
    "PCH(2)": "PCH",
    "PCH*": "PCH",
    "PUL": "PUL",
    "PUL*": "PUL",
    "ORTR": "ORTR",
    "ORTR*": "ORTR",
    "ORTR+": "ORTR",
    "ORTR(2)": "ORTR",
    "ORTR(3)": "ORTR",
    "ORTR(4)": "ORTR",
    "MKG": "MKG",
    "MKG(6)": "MKG",
    "STR": "STR",
    "RAD": "RAD",
    "RAD(6)": "RAD",
    "RAD(10)": "RAD",
    "NUK": "NUK",
    "NUKT": "NUK",
    "NUK(6)": "NUK",
    "NUK(10)": "NUK",
    "PMR": "PMR",
    "PMR(6)": "PMR",
    "PMR(10)": "PMR",
    "PAT": "PAT",
    "PAT(6)": "PAT",
    "PAT(10)": "PAT",
    "LAB": "LAB",
    "LAB(6)": "LAB",
    "LAB(10)": "LAB",
    "SON": "SON/IDB",
    "SON/IDB": "SON/IDB",
    "SON/IDB(4)": "SON/IDB",
    "SON/IDB(5)": "SON/IDB",
    "SON/IDB(7)": "SON/IDB",
}


def fachspalte(token: str) -> str | None:
    """PDF-Spaltenkopf → Fachspalte (ZMK und KFO getrennt, Fußnoten wie «(7)» ignoriert)."""
    t = token.strip()
    if not t or t.lower() == "gesamt":
        return None
    t_compact = re.sub(r"\s+", "", t).upper()
    if t_compact.startswith("KFO"):
        return "KFO"
    if t_compact.startswith("ZMK") or t_compact == "ZM":  # «ZMK(5)», «ZMK*», «ZM» (abgeschnitten)
        return "ZMK"
    if t in _FACH_MAP:
        return _FACH_MAP[t]
    base = re.sub(r"\(.*$", "", t)
    if base in _FACH_MAP:
        return _FACH_MAP[base]
    if re.match(r"^[A-Z]{2,4}$", t):
        return t if t in FACHSPALTEN else None
    return None


# Lesbare Bezeichnung je Zeile_ID (Spalte «Zeile_kanonisch» in den Excel-Sheets)
KANONISCHE_ZEILEN: dict[str, str] = {
    "spitalsambulant": "ÄAVE spitalsambulant",
    "niedergelassen": "ÄAVE niedergelassene ÄrztInnen gesamt (mit Kassenvertrag)",
    "selbst_amb": "ÄAVE in selbständige Ambulatorien (mit Kassenvertrag)",
    "kassen_amb": ("ÄAVE in Kassenambulatorien (kasseneigene selbstständige Ambulatorien)"),
    "extramural": (
        "ÄAVE niedergelassene ÄrztInnen und in selbstständigen Ambulatorien (mit Kassenvertrag und kasseneigene) gesamt"
    ),
    "insgesamt": "ÄAVE insgesamt",
    "vgf": "davon in VGF gesamt (IST: Gruppenpraxen, PVE, Ambulatorien; PLAN: PVE, Ambulatorien)",
    "pve": "davon in PVE (Zentren und Netzwerke; PLAN: zumindest)",
    "wahl": "ÄAVE WahlärztInnen und in selbstständigen Ambulatorien (ohne Kassenvertrag)",
    "extramural_inkl_wahl": "ÄAVE Summe extramural inkl. WahlärztInnen",
    "insgesamt_als_extramural": (
        "vorläufig: beschriftet «gesamt extramural», Werte wie insgesamt (spitalsambulant + extramural) – eine Regel "
        "«umbenennen» je Matrix ordnet sie zu (Wien VR 92: insgesamt); sonst Prüfung zeile_zuordnen"
    ),
    "gastpat_spitalsambulant": "davon für inländische Gastpatient:innen, spitalsambulant (Teilmenge, Wien)",
    "gastpat_extramural": "davon für inländische Gastpatient:innen, extramural (Teilmenge, Wien)",
    "umr_spitalsambulant": "Umrechnungsfaktor SVE → ÄAVE, spitalsambulant (nur SVE-Länder)",
    "umr_niedergelassen": "Umrechnungsfaktor SVE → ÄAVE, niedergelassen mit Kassenvertrag (Regiomed; nur SVE-Länder)",
    "umr_selbst_amb": "Umrechnungsfaktor SVE → ÄAVE, selbständige Ambulatorien mit Kassenvertrag (nur SVE-Länder)",
    "umr_kassen_amb": "Umrechnungsfaktor SVE → ÄAVE, Kassenambulatorien (nur SVE-Länder)",
    "umr_wahl": "Umrechnungsfaktor SVE → ÄAVE, Wahlärzt:innen und Ambulatorien ohne Kassenvertrag (nur SVE-Länder)",
    "planstellen_oegk_svs_bvaeb": (
        "ÖGK/SVS/BVAEB Planstellen gesamt (Wien, Fußnote: ohne Bereinigung von Doppelzählungen; keine Summe der Träger)"
    ),
    "planstellen_oegk": "ÖGK-Planstellen",
    "planstellen_svs": "SVS-Planstellen",
    "planstellen_bvaeb": "BVAEB-Planstellen",
    "amb_standorte": "Anzahl Ambulatorien-Standorte (mit Kassenvertrag und kasseneigen)",
    "slst_gesamt": "Sachleistungsstellen gesamt",
    "slst_gemeinsam": "Gemeinsame Sachleistungsstellen aller KV-Träger",
    "slst_eva": "davon in EVA",
    "slst_zus_oegk": "zusätzliche ÖGK-Sachleistungsstellen",
    "slst_zus_svs": "zusätzliche SVS-Sachleistungsstellen",
    "slst_zus_bvaeb": "zusätzliche BVAEB-Sachleistungsstellen",
}
