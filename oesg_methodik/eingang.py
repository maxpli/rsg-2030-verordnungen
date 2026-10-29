"""Vertrag der ÄAVE-Eingangstabelle: was jeder Datensatz (Schicht 1) an Schicht 2 liefert.

Eine Zeile je Region × Abschnitt × Jahr × ÄAVE-Zeile × Fach × Basis. `Fach` ist bereits im ÖSG-Zuschnitt
(`faecher.OESG_ANALYSEKERN`, Zusammenfassungen laut R4 und R5), auch in den Teilzeilen (R10). Die Adapter liegen beim Datensatz
(z. B. `rsg2030.analyse_eingang.aave_eingang`), dieses Modul legt nur Spalten und Regeln fest.
Regeln und Bedeutung: docs/METHODIK.md (R1, R2, R10).
"""

from __future__ import annotations

import pandas as pd

from oesg_methodik.faecher import OESG_ANALYSEKERN

SPALTEN = [
    "Datensatz",
    "Land",
    "Ebene",
    "Region_ID",
    "Abschnitt",
    "Jahr",
    "Zeile_ID",
    "Fach",
    "Basis",
    "AAVE",
    "Zuschnitt",
]
"""`Zuschnitt`: aus welchen Spalten des Datensatzes der Wert entstand (`faecher.zuschnitt`), z. B. «ZMK + KFO»."""
SCHLUESSEL = [c for c in SPALTEN if c not in ("AAVE", "Zuschnitt")]
REGION = ["Land", "Ebene", "Region_ID", "Abschnitt", "Jahr"]
"""Schlüssel, über den die Bevölkerung zugeordnet wird."""

SACHLEISTUNG = "Sachleistung"
"""Zeile «insgesamt»: spitalsambulant + Kassenvertrag + Ambulatorien, ohne Wahlärzt:innen (R1, R2)."""
BASEN = (SACHLEISTUNG,)
"""Eine Basis «inkl. Wahlärzt:innen» gibt es für RSG 2030 nicht (R1): PLAN enthält sie nach ÖSG nie, IST nur
in 6 von 9 BL. Die Spalte `Basis` bleibt, damit Tabellen verschiedener Datensätze zusammenpassen."""

INSGESAMT = "insgesamt"
"""Die Zeile, für die es ein Versorgungsdichte-Soll-Intervall (ÖSG) gibt: Die Richtwerte beziehen sich auf alle ÄAVE eines Fachs (R1, R10)."""
ZEILEN = ("spitalsambulant", "extramural", INSGESAMT, "pve")
"""ÄAVE-Zeilen der RSG-Planungsmatrix, die es in IST und PLAN gibt (Tabellenband S.231–232), in der Reihenfolge der
Vorlage (Tabellenband S.239): spitalsambulant + extramural = insgesamt; pve ist eine Teilmenge von insgesamt (R10)."""
PVE_FAECHER = ("AM", "KIJU")
"""PVE-ÄAVE weist die Matrix nur «in der Allgemeinmedizin (AM) und der Kinder- und Jugendheilkunde (KIJU)» aus,
PLAN als «Mindestanzahl» (Tabellenband S.231)."""

EBENEN = {"BL", "VR"}  # keine Österreich-Ebene: der ÖSG misst je Versorgungsregion (Textband S.38)
ABSCHNITTE = {"IST", "PLAN"}


def pruefe(eingang: pd.DataFrame) -> pd.DataFrame:
    """Prüft den Vertrag; gibt die Tabelle in Spaltenreihenfolge zurück."""
    fehlt = [c for c in SPALTEN if c not in eingang.columns]
    if fehlt:
        raise ValueError(f"ÄAVE-Eingang: Spalten fehlen: {fehlt}")
    e = eingang[SPALTEN]
    for spalte, erlaubt in (
        ("Basis", set(BASEN)),
        ("Ebene", EBENEN),
        ("Abschnitt", ABSCHNITTE),
        ("Zeile_ID", set(ZEILEN)),
        ("Fach", set(OESG_ANALYSEKERN)),
    ):
        anders = set(e[spalte]) - erlaubt
        if anders:
            raise ValueError(f"ÄAVE-Eingang: unbekannte Werte in {spalte}: {sorted(anders)}")
    pve_anders = sorted(set(e.loc[e["Zeile_ID"] == "pve", "Fach"]) - set(PVE_FAECHER))
    if pve_anders:
        raise ValueError(f"ÄAVE-Eingang: pve nur für {PVE_FAECHER}, nicht für {pve_anders}")
    if e["AAVE"].isna().any():
        raise ValueError("ÄAVE-Eingang: leere ÄAVE – fehlende Werte weglassen, nicht leer liefern")
    doppelt = e.duplicated(SCHLUESSEL)
    if doppelt.any():
        raise ValueError(f"ÄAVE-Eingang: Schlüssel doppelt, z. B. {e[doppelt].iloc[0].to_dict()}")
    return e
