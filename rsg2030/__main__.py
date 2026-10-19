#!/usr/bin/env python3
"""RSG 2030 – vom Download bis zur Versorgungsdichte.

python -m rsg2030 alles              download → daten → versorgungsdichte (frischer Klon)
python -m rsg2030 download           Quellen laden, Prüfsummen prüfen (--neu = alle neu laden)
python -m rsg2030 daten              auslesen, korrigieren, prüfen → Planungsmatrizen (CSV + Excel-Mappe)
python -m rsg2030 versorgungsdichte  ÄAVE im ÖSG-Zuschnitt, Versorgungsdichte, Lage zum Soll-Intervall je BL und VR
python -m rsg2030 waechter           neue Verordnungen im RIS oder neue Fassungen der Quellen?

Nur zum Pflegen der Eingaben im Paket (neue Verordnung, siehe docs/PIPELINE.md):

python -m rsg2030 seiten             Seitenregister seiten.csv aus den PDFs erzeugen
python -m rsg2030 manuell            Blätter für Bildseiten in manuell.xlsx anlegen
python -m rsg2030 fussnoten          neue Fußnoten als Entwurf ins Verzeichnis fussnoten.csv (Einordnung von Hand)
python -m rsg2030 freigabe           Freigabe-Mappe freigabe.xlsx anlegen bzw. auf den Datenstand bringen
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
import time

from rsg2030.protokoll import einrichten

log = logging.getLogger(__name__)

BEFEHLE: dict[str, tuple[str, str]] = {
    "download": (
        "rsg2030.quellen.download",
        "alle Quelldateien laden (RIS, goeg.at, statistik.at) und Prüfsummen kontrollieren",
    ),
    "daten": (
        "rsg2030.pipeline",
        "Quellen prüfen → Matrizen auslesen, korrigieren, prüfen → Planungsmatrizen (CSV + Excel-Mappe)",
    ),
    "versorgungsdichte": (
        "rsg2030.versorgungsdichte",
        "ÄAVE im ÖSG-Zuschnitt, Versorgungsdichte und Lage zum Soll-Intervall je BL und VR",
    ),
    "waechter": (
        "rsg2030.waechter",
        "Neue Verordnungen im RIS oder neue Fassungen der Quellen? (Hinweis, ändert nichts)",
    ),
    "seiten": ("rsg2030.scripts.seiten", "Seitenregister seiten.csv aus den PDFs erzeugen (fragt nach Bildseiten)"),
    "manuell": ("rsg2030.scripts.manual_template", "Blätter für Bildseiten in manuell.xlsx anlegen bzw. ergänzen"),
    "fussnoten": ("rsg2030.fussnoten", "neue Fußnoten der Matrixseiten als Entwurf ins Verzeichnis fussnoten.csv"),
    "freigabe": ("rsg2030.freigabe", "Freigabe-Mappe freigabe.xlsx anlegen bzw. auf den Datenstand bringen"),
}
ALLES = ("download", "daten", "versorgungsdichte")


def _fuehre_aus(module_name: str, label: str, argv: list[str]) -> int:
    log.info(f"\n{'=' * 60}")
    log.info(f"▶ {label}")
    log.info(f"{'=' * 60}")
    t0 = time.perf_counter()
    rc = importlib.import_module(module_name).main(argv)
    elapsed = time.perf_counter() - t0
    if rc != 0:
        log.error(f"\n❌ Fehlgeschlagen (Exit {rc}) nach {elapsed:.1f}s")
        return rc
    log.info(f"✓ OK ({elapsed:.1f}s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    einrichten()
    parser = argparse.ArgumentParser(prog="python -m rsg2030", description="RSG 2030: Download bis Versorgungsdichte")
    parser.add_argument("command", nargs="?", choices=[*BEFEHLE, "alles"], help=f"Befehl: alles, {', '.join(BEFEHLE)}")
    # Optionen eines Befehls (z. B. download --neu) prüft der Befehl selbst; Unbekanntes bricht dort ab
    args, rest = parser.parse_known_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    if args.command == "alles" and rest:
        parser.error(f"«alles» kennt keine Optionen: {' '.join(rest)}")
    for cmd in ALLES if args.command == "alles" else (args.command,):
        module_name, label = BEFEHLE[cmd]
        rc = _fuehre_aus(module_name, label, rest)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
