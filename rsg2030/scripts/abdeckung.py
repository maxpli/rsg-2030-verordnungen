"""Abdeckung der Rechenprüfungen: Fällt ein falscher Wert auf? (von Hand aufgerufen, nicht Teil von «alles»)

Je Zeilenart – Land × Block × Abschnitt × Zeile_ID × Ebene × Fachspalte bzw. «gesamt» – wird eine Zelle mit Wert
verfälscht, und die Prüfungen des Landes laufen neu (`checks.pruefe_alle`, wie im Lauf). Eine Zeilenart gilt als
abgedeckt, wenn danach eine Prüfung neu abweicht oder nicht prüfbar ist – also der Lauf nicht mehr freigegeben wäre.
Was das Ergebnis heißt: docs/PRUEFUNG.md, «Was danach noch unsicher ist». Zwei Stufen:

- `grob` (Standard): + 100, Prozent ± 50, Faktor × 2. Prüft, ob jede Zelle in einer Rechnung steckt, die sie
  kontrolliert. Erwartet: jede Zeilenart fällt auf, außer abgeleiteten Zellen (dieselbe Rechnung wie die Prüfung)
  und %-Werten ohne Stellen; sonst Exit 1.
- `fein`: + 10 % (mindestens + 1), Prozent ± 10, Faktor × 1,1. Zeigt, wo ein kleiner Fehler innerhalb der Toleranz
  bleibt – die Toleranz ist die Rundung aller Werte einer Rechnung zusammen. Dort schützt nur die Zweitlesung.

Verfälscht wird möglichst eine Zelle ≠ 0 (bei %-Zeilen eine mit Stellen > 0), damit «nur Nullen» das Ergebnis nicht
verzerren. Dauer: rund zehn Minuten je Stufe.

    python -m rsg2030.scripts.abdeckung [--stufe grob|fein]
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from rsg2030.checks import OFFEN, pruefe_alle
from rsg2030.manuell import manuelle_matrizen
from rsg2030.matrix_extract import PROZENT_SUFFIX
from rsg2030.pipeline import baue_pipeline
from rsg2030.protokoll import einrichten

log = logging.getLogger(__name__)

KLASSE = ["Land", "Block", "Abschnitt", "Zeile_ID", "Ebene", "Spalte"]
SCHLUESSEL = ["Check", "Land", "Ebene", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"]


def falsch(wert: float, einheit: str, grob: bool) -> float:
    if einheit == "Prozent":
        d = 50 if grob else 10
        return wert - d if wert >= d else wert + d
    if einheit == "Faktor":
        return wert * (2 if grob else 1.1)
    return wert + (100 if grob else max(1.0, round(abs(wert) * 0.1, 1)))


def _offen(checks: pd.DataFrame) -> set[tuple[str, ...]]:
    return set(map(tuple, checks.loc[checks["Status"].isin(OFFEN), SCHLUESSEL].astype(str).values))


def mit_stellen(long: pd.DataFrame) -> pd.Series:
    """Je Zelle einer %-Zeile: Hat die Stellen-Zeile darüber in derselben Spalte einen Wert > 0?"""
    zelle = ["Land", "Ebene", "Region_ID", "Block", "Abschnitt", "Fach"]
    stellen = long[["Zeile_ID", *zelle, "Wert"]].rename(columns={"Zeile_ID": "Stellen_ID", "Wert": "Stellen"})
    p = long[zelle].assign(Stellen_ID=long["Zeile_ID"].str.removesuffix(PROZENT_SUFFIX))
    s = p.merge(stellen, on=["Stellen_ID", *zelle], how="left")["Stellen"].fillna(0).gt(0)
    return pd.Series(s.to_numpy(), index=long.index) & long["Zeile_ID"].str.endswith(PROZENT_SUFFIX)


def abdeckung(long: pd.DataFrame, voll: set[str], manuell_bl: set[str], grob: bool = True) -> pd.DataFrame:
    """Je Zeilenart die verfälschte Zelle und die Prüfungen, die danach neu abweichen (leer = nicht abgedeckt)."""
    basis = {
        land: _offen(pruefe_alle(long[long["Land"] == land], vr_vollstaendig=voll & {land}, nur_bl_zeilen=manuell_bl))
        for land in long["Land"].unique()
    }
    zellen = long[long["Wert"].notna()].assign(
        Spalte=lambda d: d["Fach"].where(d["Fach"] == "gesamt", "Fach"),
        Stellen=mit_stellen(long),
        Rang=lambda d: (d["Wert"] == 0).astype(int) * 2 + (~d["Stellen"]).astype(int),
    )
    zeilen = []
    for schluessel, g in zellen.groupby(KLASSE):
        i = g.sort_values("Rang", kind="stable").index[0]
        land = str(schluessel[0])
        sub = long[long["Land"] == land].copy()
        sub.at[i, "Wert"] = falsch(float(sub.at[i, "Wert"]), str(sub.at[i, "Einheit"]), grob)
        neu = _offen(pruefe_alle(sub, vr_vollstaendig=voll & {land}, nur_bl_zeilen=manuell_bl)) - basis[land]
        zeilen.append(
            dict(
                zip(KLASSE, schluessel),
                Region_ID=long.at[i, "Region_ID"],
                Fach=long.at[i, "Fach"],
                Einheit=long.at[i, "Einheit"],
                Quelle=long.at[i, "Quelle"],
                Wert=long.at[i, "Wert"],
                Stellen=bool(zellen.at[i, "Stellen"]),
                Zellen=len(g),
                Prueft=", ".join(sorted({k[0] for k in neu})),
            )
        )
    return pd.DataFrame(zeilen)


def grund(r: pd.Series) -> str:
    """Warum eine Zeilenart nicht abgedeckt ist – oder «offen», wenn es keinen der bekannten Gründe gibt."""
    if r["Quelle"] == "abgeleitet":
        return "abgeleitet (dieselbe Rechnung wie die Prüfung)"
    if r["Einheit"] == "Prozent" and not r["Stellen"]:
        return "%-Wert ohne Stellen"
    return "offen"


def main(argv: list[str] | None = None) -> int:
    einrichten()
    a = argparse.ArgumentParser(prog="python -m rsg2030.scripts.abdeckung", description=__doc__.splitlines()[0])
    a.add_argument("--stufe", choices=["grob", "fein"], default="grob", help="wie stark verfälscht wird")
    grob = a.parse_args(argv).stufe == "grob"
    p = baue_pipeline()
    manuell_bl = {m.land for m in manuelle_matrizen() if m.ebene == "BL"}
    erg = abdeckung(p.long, p.voll, manuell_bl, grob)
    nicht = erg[erg["Prueft"] == ""].assign(Grund=lambda d: d.apply(grund, axis=1))
    log.info("Stufe %s: %d Zeilenarten, %d fallen auf, %d nicht", "grob" if grob else "fein", len(erg),
             len(erg) - len(nicht), len(nicht))  # fmt: skip
    for g, n in nicht["Grund"].value_counts().items():
        log.info("   fallen nicht auf, %s: %d", g, n)
    offen = nicht[nicht["Grund"] == "offen"]
    if not grob:
        tab = offen.groupby(["Land", "Einheit"]).size().unstack(fill_value=0)
        log.info("   ohne bekannten Grund, je Land und Einheit (dort schützt nur die Zweitlesung):")
        for z in tab.to_string().splitlines():
            log.info("   %s", z)
        return 0
    for z in offen.drop(columns=["Prueft", "Grund"]).to_string(index=False).splitlines() if len(offen) else []:
        log.warning("   ✗ %s", z)
    if offen.empty:
        log.info("✓ Jede Zeilenart ohne einen der genannten Gründe fällt einer Prüfung auf.")
    return 1 if len(offen) else 0


if __name__ == "__main__":
    sys.exit(main())
