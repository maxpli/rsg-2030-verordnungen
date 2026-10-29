"""Was wörtlich der ÖSG-Vorlage der RSG-Planungsmatrix entspricht (Tabellenband Anhang 9, S.239), prüft die Maschine.

Die Freigabe (freigabe.py) fragt einen Menschen nur nach dem, was davon abweicht (docs/PRUEFUNG.md, «Wer prüft was»,
Regel 1 und 3):

- **Zeilen:** Eine Beschriftung, die so in der Vorlage steht und der Zeile_ID dieser Vorlage-Zeile zugeordnet ist, ist
  durch die Vorlage festgelegt (`oesg_methodik/referenz/oesg_rsgpm_zeilen.csv`). Die Vorlage hat zwei Platzhalter, die
  die Länder ausfüllen: «ÄAVE (ggf. SVE)» steht im PDF als «ÄAVE (ggf. SVE)», «ÄAVE» oder «SVE»; «(- davon)» als
  «(- davon)», «- davon» oder gar nicht. Jahreszahlen sind schon als «20xx» vereinheitlicht.
- **Spalten:** Ein Spaltenkopf, der ohne Fußnotenzeichen genau seine Fachspalte ist («AM(4)», «ORTR3)» → AM, ORTR),
  braucht kein Urteil über die Zuordnung; ebenso «AM/PV» → AM, wie in der Vorlage über den ÄAVE-Äquivalenten. Ob ein
  Land andere Spalten hat als die Vorlage (zusätzlich KFO, ohne STR), ist dagegen ein Urteil: `spalten_abweichung`.
"""

from __future__ import annotations

import re
from functools import cache

import pandas as pd

from oesg_methodik.pfade import OESG_RSGPM_ZEILEN_CSV
from rsg2030.matrix_extract import kompakt

PLATZHALTER = {
    "ÄAVE (ggf. SVE)": ("ÄAVE (ggf. SVE)", "ÄAVE", "SVE"),
    "(- davon) ": ("(- davon) ", "- davon ", ""),
}
"""Platzhalter der Vorlage → wie die Länder sie drucken."""

PROZENT = "_max_vaep_prozent"
KOPF_WIE_VORLAGE = {"AM/PV": "AM"}
"""Spaltenköpfe der Vorlage, die nicht wie ihre Fachspalte heißen."""
SPALTEN_VORLAGE = (
    *("AM", "AN", "KIJU", "KJC", "KJP", "CH", "NCH", "IM", "GGH", "NEU", "PSY", "DER", "AU", "HNO"),
    *("URO", "PCH", "PUL", "ORTR", "MKG", "ZMK", "STR", "RAD", "NUK", "PMR", "PAT", "LAB", "SON/IDB", "gesamt"),
)
"""Fachspalten der Vorlage in ihrer Reihenfolge, ohne Fußnotenzeichen (Tabellenband S.239; tests/test_referenz.py)."""


def zeilen() -> pd.DataFrame:
    return pd.read_csv(OESG_RSGPM_ZEILEN_CSV, dtype=str)


def _varianten(text: str) -> set[str]:
    out = {text}
    for platzhalter, ersatz in PLATZHALTER.items():
        out = {v.replace(platzhalter, e) for v in out for e in ersatz}
    return {kompakt(v) for v in out}


@cache
def _vorlage_zeilen() -> frozenset[tuple[str, str, str]]:
    return frozenset(
        (a, v, z)
        for a, t, z in zip(zeilen()["Abschnitt"], zeilen()["Beschriftung"], zeilen()["Zeile_ID"])
        for v in _varianten(t)
    )


def zeile_wie_vorlage(abschnitt: str, beschriftung: str, zeile_id: str) -> bool:
    """Steht die Beschriftung (ohne Fußnotenzeichen, Jahr als 20xx) so in der Vorlage, in diesem Abschnitt und für
    diese Zeile_ID? Prozentzeilen («… in %») gehören zu jeder Stellenzeile."""
    z = "*" + PROZENT if zeile_id.endswith(PROZENT) else zeile_id
    return (abschnitt, kompakt(beschriftung), z) in _vorlage_zeilen()


def spalten_abweichung(faecher: set[str]) -> str:
    """Fachspalten eines Landes gegen die Vorlage: «zusätzlich: KFO · fehlt: STR», leer, wenn genau wie die Vorlage."""
    teile = []
    if zusaetzlich := sorted(faecher - set(SPALTEN_VORLAGE)):
        teile.append("zusätzlich: " + ", ".join(zusaetzlich))
    if fehlt := [f for f in SPALTEN_VORLAGE if f not in faecher]:
        teile.append("fehlt: " + ", ".join(fehlt))
    return " · ".join(teile)


def kopf_wie_vorlage(kopf: str, fach: str) -> bool:
    """Ist der Spaltenkopf ohne Fußnotenzeichen («(4)», «*», «3)», «(3,») genau seine Fachspalte? Sagt nichts darüber,
    ob die Vorlage diese Spalte hat (`spalten_abweichung`)."""
    kern = re.match(r"[^\s(*\d,)]*", kopf.strip())
    k = kern.group() if kern else ""
    return k == fach or KOPF_WIE_VORLAGE.get(k) == fach
