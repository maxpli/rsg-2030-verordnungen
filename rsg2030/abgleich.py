"""Abgleich mit der veröffentlichten Version: stimmt das selbst erzeugte Ergebnis Byte für Byte?

`erwartete_ausgaben.csv` (im Paket) hält je Ausgabe SHA-256 und Zeilenzahl der Version fest, die zu diesem
Paket gehört. Wer die Daten selbst erzeugt, sieht am Ende jedes Laufs, ob er genau diese Fassung erhalten hat.
Weicht sie ab, haben sich Quellen, Eingaben oder Code geändert – dann CHANGELOG.md und den Diff prüfen.
"""

from __future__ import annotations

import csv
import hashlib
import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

log = logging.getLogger(__name__)

ERWARTET_CSV = Path(__file__).with_name("erwartete_ausgaben.csv")


def paketversion() -> str:
    try:
        return version("rsg-2030-verordnungen")
    except PackageNotFoundError:
        return "unbekannt"


def erwartet(name: str) -> dict[str, str] | None:
    """Zeile aus `erwartete_ausgaben.csv` (Datei, SHA256, Zeilen) oder None."""
    with ERWARTET_CSV.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r["Datei"] == name), None)


def gleiche_ab(pfad: Path) -> bool | None:
    """Datei gegen die erwartete Prüfsumme; meldet das Ergebnis. None = keine Erwartung hinterlegt."""
    soll = erwartet(pfad.name)
    if soll is None:
        return None
    ist = hashlib.sha256(pfad.read_bytes()).hexdigest()
    if ist == soll["SHA256"]:
        log.info(f"   ✓ {pfad.name} entspricht Version {paketversion()} (SHA-256 {ist[:12]}…)")
        return True
    log.warning(
        f"   ✗ {pfad.name} weicht von Version {paketversion()} ab (SHA-256 {ist[:12]}…, erwartet "
        f"{soll['SHA256'][:12]}…): Quellen, Eingaben oder Code geändert?"
    )
    return False
