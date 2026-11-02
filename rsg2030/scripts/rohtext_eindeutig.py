"""Wie oft ist der Rohtext einer gezeigten Zelle auf seiner PDF-Seite eindeutig? (von Hand aufgerufen)

Belegt die Entscheidung der Webseite, die Zahl im PDF **nicht** zu markieren (docs/WEB.md, «Darstellungsregeln»):
Ein Betrachter, der `#search=` kennt, sucht eine Zeichenfolge auf der Seite – steht sie dort mehrfach, markiert er
die falsche Zelle. Gezählt wird je Rohtext, den die Seite in der Herkunft zeigt, wie oft dieselbe Zeichenfolge in
irgendeiner Zelle derselben PDF-Seite steht (alle Blöcke und Zeilen, denn so sucht der Betrachter).

Braucht `daten_ergebnis/RSG_2030_Planungsmatrizen.csv` und die gebaute Seite (`python -m rsg2030 web`).

    python -m rsg2030.scripts.rohtext_eindeutig
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter

import pandas as pd

from rsg2030.analyse_eingang import lade_matrix_long
from rsg2030.protokoll import einrichten
from rsg2030.web import ziel_dir

log = logging.getLogger(__name__)


def zaehle(long: pd.DataFrame, daten: dict) -> tuple[int, int, list[tuple[str, str, str, int]]]:
    """(eindeutig, mehrfach, die häufigsten Fälle) über alle Rohtexte, die die Seite zeigt."""
    je_seite = {(pdf, int(seite)): Counter(g["Roh"].dropna()) for (pdf, seite), g in long.groupby(["PDF", "Seite"])}
    eindeutig, mehrfach, faelle = 0, 0, []
    for schluessel, angaben in daten["herkunft"].items():
        region, abschnitt, _fach = schluessel.split("|")
        quelle, seite, *_ = daten["matrizen"][f"{region}|{abschnitt}"]
        pdf = daten["quellen"][quelle][0]
        for spalte, roh, *_ in angaben:
            if roh is None:
                continue
            n = je_seite[(pdf, seite)].get(roh, 0)
            if n == 1:
                eindeutig += 1
            else:
                mehrfach += 1
                faelle.append((schluessel, spalte, roh, n))
    faelle.sort(key=lambda f: -f[3])
    return eindeutig, mehrfach, faelle


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030.scripts.rohtext_eindeutig",
        description="Eindeutigkeit der Rohtexte auf ihrer PDF-Seite (Beleg für docs/WEB.md)",
    ).parse_args(argv)
    pfad = ziel_dir() / "data.json"
    if not pfad.is_file():
        log.error(f"❌ {pfad} fehlt: erst «python -m rsg2030 web»")
        return 1
    eindeutig, mehrfach, faelle = zaehle(lade_matrix_long(), json.loads(pfad.read_text(encoding="utf-8")))
    gesamt = eindeutig + mehrfach
    log.info(f"Rohtexte, die die Seite zeigt: {gesamt}")
    log.info(f"   auf ihrer PDF-Seite eindeutig: {eindeutig} ({eindeutig / gesamt:.0%})")
    log.info(f"   mehrfach auf der Seite:        {mehrfach} ({mehrfach / gesamt:.0%})")
    for schluessel, spalte, roh, n in faelle[:5]:
        log.info(f"      {schluessel} {spalte}: «{roh}» steht {n}× auf der Seite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
