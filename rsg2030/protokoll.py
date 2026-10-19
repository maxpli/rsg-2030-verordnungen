"""Konsolen-Ausgabe und Laufprotokoll der Pipelines.

Meldungen laufen über `logging` (je Modul `log = logging.getLogger(__name__)`); `einrichten()` im Einstieg
(`main`) leitet sie auf die Konsole. Warnungen (✗) und Fehler (❌) haben eigene Stufen,
damit ein Aufrufer sie filtern kann.

Das Laufprotokoll liegt neben den Daten-Ausgaben (`Laufprotokoll_<schritt>.json`) und hält fest, womit sie
entstanden sind: Zeit, Git-Stand, Python- und Paketversionen, SHA-256 jeder Ausgabe. Die Quellen selbst sind
über den Git-Stand festgelegt (Prüfsummen in `rsg2030/quellen/quellen.csv`, von der Pipeline geprüft).
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import subprocess
import sys
from collections.abc import Iterable
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rsg2030.abgleich import paketversion

# Git-Stand des Codes (bei editierbarer Installation das Repo; installiert aus einem Tag: keiner → Paketversion)
CODE_DIR = Path(__file__).resolve().parents[1]

# Pakete, deren Version die Ausgaben beeinflussen kann (pdfplumber/pdfminer: Textzerlegung)
PAKETE = ("pandas", "numpy", "openpyxl", "odfpy", "pdfplumber", "pdfminer.six", "pypdfium2")


def einrichten(*, ausfuehrlich: bool = False) -> None:
    """Meldungen als reinen Text nach stdout. Mehrfacher Aufruf schadet nicht."""
    logging.basicConfig(level=logging.DEBUG if ausfuehrlich else logging.INFO, format="%(message)s", stream=sys.stdout)


def _git(*args: str) -> str | None:
    if not (CODE_DIR / ".git").exists():  # installiert, nicht aus einem Klon: kein eigener Git-Stand
        return None
    try:
        r = subprocess.run(["git", *args], cwd=CODE_DIR, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return r.stdout.strip()


def _paketversion(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def schreibe_laufprotokoll(
    ordner: Path, schritt: str, ausgaben: Iterable[Path], zusatz: dict[str, object] | None = None
) -> Path:
    """`Laufprotokoll_<schritt>.json` in `ordner` schreiben (überschreibt den letzten Lauf).

    `zusatz`: Angaben des Schritts selbst, z. B. das Prüfergebnis."""
    status = _git("status", "--porcelain")
    inhalt = {
        "Schritt": schritt,
        "Paketversion": paketversion(),
        "Zeit": datetime.now().astimezone().isoformat(timespec="seconds"),
        "Git_Commit": _git("rev-parse", "HEAD"),
        "Git_Branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        # False = Lauf mit nicht committeten Änderungen: Ausgabe ist so nicht aus dem Commit reproduzierbar
        "Git_sauber": None if status is None else status == "",
        "Python": platform.python_version(),
        "Pakete": {p: _paketversion(p) for p in PAKETE},
        **(zusatz or {}),
        "Ausgaben": {
            a.name: {"SHA256": hashlib.sha256(a.read_bytes()).hexdigest(), "Bytes": a.stat().st_size} for a in ausgaben
        },
    }
    ziel = ordner / f"Laufprotokoll_{schritt}.json"
    ziel.write_text(json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ziel
