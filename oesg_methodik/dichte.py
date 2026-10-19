"""Versorgungsdichte und Lage zum Versorgungsdichte-Soll-Intervall (ÖSG; docs/METHODIK.md, R3, R10).

Alle Kennzahlen zum Soll-Intervall setzen nur an den gedruckten Grenzen VDmin und VDmax an, nie an der Mitte: Die
druckt der ÖSG nicht, und wegen der Rundung liegen die Grenzen nicht genau bei Mitte ± 30 % (METHODIK R3).
"""

from __future__ import annotations

import pandas as pd

from oesg_methodik import eingang as e
from oesg_methodik.richtwerte import richtwerte_fuer_vd

LAGEN = ("unter", "im", "über")


def position_im_intervall(vd: float, vdmin: float, vdmax: float) -> float:
    """(VD − VDmin) / (VDmax − VDmin): 0 = Untergrenze, 1 = Obergrenze. Unsere Kennzahl, nicht aus dem ÖSG."""
    return (vd - vdmin) / (vdmax - vdmin)


def lage_im_intervall(vd: pd.Series, vdmin: pd.Series, vdmax: pd.Series) -> pd.Series:
    """«unter», «im» oder «über» dem Soll-Intervall; auf einer Grenze = «im». Leer ohne Soll-Intervall."""
    unter, im, ueber = LAGEN
    lage = pd.Series(im, index=vd.index, dtype=object)
    lage[vd < vdmin] = unter
    lage[vd > vdmax] = ueber
    lage[vdmin.isna() | vdmax.isna()] = None
    return lage


def aave_abstand_intervall(vd: pd.Series, vdmin: pd.Series, vdmax: pd.Series, bevoelkerung: pd.Series) -> pd.Series:
    """ÄAVE zwischen VD und nächster Grenze: 0 im Soll-Intervall, negativ = so viele ÄAVE fehlen bis VDmin, positiv =
    so viele ÄAVE liegen über VDmax. Leer ohne Soll-Intervall."""
    grenze = vd.clip(lower=vdmin, upper=vdmax)  # clip übergeht fehlende Grenzen → unten ausdrücklich leer
    abstand = (vd - grenze) * bevoelkerung / 100_000
    return abstand.where(vdmin.notna() & vdmax.notna())


def kennzahlen(aave: pd.DataFrame, bevoelkerung: pd.DataFrame, richtwerte: pd.DataFrame) -> pd.DataFrame:
    """ÄAVE-Eingang (`eingang.SPALTEN`) + Bevölkerung + Richtwerte → VD und Lage zum Soll-Intervall.

    `bevoelkerung`: Spalten `eingang.REGION` + Bevoelkerung (z. B. `bevoelkerung.bevoelkerung_fuer`).
    Reihenfolge der Zeilen wie im Eingang. VD = ÄAVE / Bevölkerung × 100.000. VDmin, VDmax, Lage, Position und
    ÄAVE-Abstand nur in der Zeile «insgesamt»: Für Teilzeilen (spitalsambulant, extramural, pve) hat der ÖSG keinen
    Richtwert (R10).
    """
    k = e.pruefe(aave).merge(bevoelkerung[[*e.REGION, "Bevoelkerung"]], on=e.REGION, how="left", validate="many_to_one")
    ohne = k[k["Bevoelkerung"].isna()]
    if len(ohne):
        raise ValueError(f"Keine Bevölkerung für {ohne[e.REGION].drop_duplicates().to_dict('records')[:3]}")
    k["VD"] = k["AAVE"] / k["Bevoelkerung"] * 100_000
    prw = richtwerte_fuer_vd(richtwerte)[["Fachrichtung", "VDmin", "VDmax"]].rename(columns={"Fachrichtung": "Fach"})
    k = k.merge(prw, on="Fach", how="left", validate="many_to_one")
    k.loc[k["Zeile_ID"] != e.INSGESAMT, ["VDmin", "VDmax"]] = float("nan")
    k["Lage_im_Intervall"] = lage_im_intervall(k["VD"], k["VDmin"], k["VDmax"])
    k["Position_im_Intervall"] = position_im_intervall(k["VD"], k["VDmin"], k["VDmax"])
    k["AAVE_Abstand_Intervall"] = aave_abstand_intervall(k["VD"], k["VDmin"], k["VDmax"], k["Bevoelkerung"])
    return k
