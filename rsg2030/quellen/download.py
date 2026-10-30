#!/usr/bin/env python3
"""Alle Quelldateien laut `quellen/quellen.csv` herunterladen und Prüfsummen kontrollieren.

- Herkunft «URL»: direkter Download (GÖG, Statistik Austria).
- Herkunft «RIS»: alle PDF-Dateien des RIS-Dokuments (Verordnung + Anlagen) nach `<Datei>`-Ordner; HTML und RTF
  zeigen nur den Text des Hauptdokuments noch einmal (dessen PDF ist dabei), ohne die Anlagen;
  Spalte «Praefix» unterscheidet mehrere Verordnungen desselben Landes (Kärnten). Die Dateiliste kommt von der
  OGD-Schnittstelle des RIS (data.bka.gv.at), die Dateien von ogd.ris.bka.gv.at: Das RIS-Portal
  (www.ris.bka.gv.at) beantwortet Anfragen aus Rechenzentren seit Ende Oktober 2026 mit einem Bot-Schutz
  («Security Check», HTTP 503); die OGD-Schnittstelle ist der dokumentierte Weg für maschinelle Abrufe, und dass
  beide Wege dieselben Bytes liefern, hält die Prüfsumme im Register fest.

Rücksichtsvoll gegenüber RIS/goeg.at/statistik.at/Wayback Machine: eine Anfrage nach der anderen, mindestens
`PAUSE_S` Sekunden Abstand (plus Zufall); bei HTTP 429/503 wird gewartet (Retry-After, sonst steigend) statt sofort
wiederholt. Antwortet ein Server gar nicht (Zeitüberschreitung, keine Verbindung), gibt es höchstens einen zweiten
Versuch nach `PAUSE_NETZ_S`; danach wird er in diesem Lauf nicht mehr angefragt. Eine Datei, die so fehlt, meldet die
Prüfsummen-Kontrolle am Ende. Vorhandene Dateien werden nur mit `--neu` erneut geladen. Für URL-Quellen gibt es eine Archivkopie
(Spalte «Archiv»): Hat das Original eine andere Fassung oder ist es weg, wird die geprüfte Fassung von dort geladen. Am Ende: Prüfsummen aller Dateien;
Abweichung → Exit 1 (online geändert? dann bewusst neu prüfen und quellen.csv anpassen).

    python -m rsg2030 download [--neu]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import random
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from oesg_methodik.pfade import original_dir
from rsg2030.abgleich import paketversion
from rsg2030.protokoll import einrichten
from rsg2030.quellen import lade_quellen, pruefe

log = logging.getLogger(__name__)

RIS_URL = "https://www.ris.bka.gv.at"
RIS_API = "https://data.bka.gv.at/ris/api/v2.6/Sonstige"
REPO_URL = "https://github.com/maxpli/rsg-2030-verordnungen"


try:  # Stammzertifikate unabhängig von der Python-Installation (python.org-Python auf macOS hat keine)
    import certifi

    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL = ssl.create_default_context()

PAUSE_S = 5.0
PAUSE_NETZ_S = 120.0
# Server, die in diesem Lauf nicht geantwortet haben: nicht weiter anfragen, sondern gleich aufgeben
_unerreichbar: set[str] = set()
# Wer anfragt und wo man nachsieht – üblich bei automatischen Abrufen öffentlicher Server
USER_AGENT = f"rsg-2030-verordnungen/{paketversion()} (+{REPO_URL})"
VERSUCHE = 4
_letzte_anfrage = 0.0


def abrufen(url: str, netz_versuche: int = 2) -> bytes:
    """Eine Anfrage, mit Mindestabstand zur vorigen und Geduld bei «zu viele Anfragen». Antwortet der Server nicht,
    höchstens `netz_versuche` Versuche; danach ist er für den Rest des Laufs gesperrt (URLError ohne Anfrage)."""
    global _letzte_anfrage
    server = urllib.parse.urlsplit(url).netloc
    if server in _unerreichbar:
        raise urllib.error.URLError(f"{server} hat in diesem Lauf schon nicht geantwortet")
    netz = 0
    for versuch in range(1, VERSUCHE + 1):
        warte = _letzte_anfrage + PAUSE_S + random.uniform(0, 2) - time.monotonic()
        if warte > 0:
            time.sleep(warte)
        _letzte_anfrage = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or versuch == VERSUCHE:
                raise
            pause = float(e.headers.get("Retry-After") or 60 * versuch)
            log.info(f"  … Server bittet um Pause (HTTP {e.code}), warte {pause:.0f}s")
            time.sleep(pause)
        except OSError as e:  # Zeitüberschreitung, keine Verbindung, Verbindung abgebrochen
            netz += 1
            if netz >= netz_versuche or versuch == VERSUCHE:
                _unerreichbar.add(server)
                raise
            log.info(f"  … keine Antwort von {server} ({e}), letzter Versuch in {PAUSE_NETZ_S:.0f}s")
            time.sleep(PAUSE_NETZ_S)
    raise AssertionError("unreachable")


def _liste(x: object) -> list:
    """Die OGD-Antwort lässt bei genau einem Element die Liste weg."""
    return x if isinstance(x, list) else [x]


def pdf_links(antwort: dict, dokumentnummer: str) -> list[str]:
    """PDF-Adressen aus einer OGD-Antwort. Die Dokumentnummer wirkt in der Abfrage als Suche (viele Treffer);
    gelesen wird nur das Dokument, dessen ID genau die Dokumentnummer ist."""
    treffer = antwort["OgdSearchResult"]["OgdDocumentResults"].get("OgdDocumentReference", [])
    links: list[str] = []
    for ref in _liste(treffer):
        if ref["Data"]["Metadaten"]["Technisch"]["ID"] != dokumentnummer:
            continue
        for inhalt in _liste(ref["Data"]["Dokumentliste"]["ContentReference"]):
            for content in _liste(inhalt["Urls"]["ContentUrl"]):
                url = content["Url"]
                if url.lower().endswith(".pdf") and url not in links:
                    links.append(url)
    return links


def ris_links(dokumentnummer: str) -> list[str]:
    """PDF-Adressen eines RIS-Dokuments über die OGD-Schnittstelle (Begründung im Modul-Docstring)."""
    antwort = json.loads(
        abrufen(f"{RIS_API}?Applikation=Spg&Dokumentnummer={dokumentnummer}&DokumenteProSeite=OneHundred").decode(
            "utf-8"
        )
    )
    return pdf_links(antwort, dokumentnummer)


def _speichern(url: str, ziel: Path, neu: bool, root: Path) -> bool:
    if ziel.is_file() and not neu:
        return False
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(abrufen(url))
    log.info(f"  -> {ziel.relative_to(root)}")
    return True


def entpacke_archiv(archiv: bytes, sha256: str) -> bytes:
    """Wayback speichert manche Dateien so, wie der Server sie gzip-komprimiert schickte: dann entpacken."""
    if archiv[:2] == b"\x1f\x8b" and hashlib.sha256(archiv).hexdigest() != sha256:
        return gzip.decompress(archiv)
    return archiv


def _url_quelle(q: pd.Series, neu: bool, root: Path) -> bool:
    """Datei per URL laden. Liefert die Originaladresse eine andere Fassung (Prüfsumme) oder gar nichts mehr, wird die
    Archivkopie aus Spalte «Archiv» (Wayback Machine, Rohdatei) geladen – sofern sie die geprüfte Fassung ist."""
    ziel = root / q["Datei"]
    if ziel.is_file() and not neu:
        return False
    original: bytes | None = None
    try:  # mit Archivkopie kein zweiter Versuch: die Kopie ist der Ersatz
        original = abrufen(q["Kennung"], netz_versuche=1 if q.get("Archiv") else 2)
    except OSError as e:
        log.warning(f"  ✗ {q['Datei']}: Originaladresse nicht erreichbar ({e})")
    if original is not None and hashlib.sha256(original).hexdigest() == q["SHA256"]:
        daten, herkunft = original, ""
    elif q.get("Archiv"):
        if original is not None:
            log.warning(f"  ✗ {q['Datei']}: Original hat jetzt eine andere Fassung – lade die Archivkopie")
        try:
            archiv = abrufen(q["Archiv"])
        except OSError as e:
            log.warning(f"  ✗ {q['Datei']}: auch die Archivkopie nicht erreichbar ({e})")
            return False
        archiv = entpacke_archiv(archiv, q["SHA256"])
        if hashlib.sha256(archiv).hexdigest() == q["SHA256"]:
            daten, herkunft = archiv, " (Archivkopie)"
        else:
            log.warning(f"  ✗ {q['Datei']}: auch die Archivkopie ist nicht die geprüfte Fassung")
            daten, herkunft = original if original is not None else archiv, ""
    elif original is not None:
        daten, herkunft = original, ""
    else:
        return False
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(daten)
    log.info(f"  -> {ziel.relative_to(root)}{herkunft}")
    return True


def download(neu: bool = False, root: Path | None = None) -> int:
    root = root or original_dir()
    dok = lade_quellen()
    geladen = 0
    for _, q in dok[dok["Herkunft"] == "URL"].iterrows():
        geladen += _url_quelle(q, neu, root)
    for (herkunft, kennung, praefix), g in dok.groupby(["Herkunft", "Kennung", "Praefix"], sort=False):
        if herkunft == "URL":
            continue
        if not neu and all((root / d).is_file() for d in g["Datei"]):
            continue
        log.info(f"\n{herkunft} {kennung}")
        ordner = (root / g["Datei"].iloc[0]).parent
        try:
            links = ris_links(kennung)
            if not links:
                log.warning(f"  WARNUNG: keine Dateien im RIS gefunden für {kennung}")
            for url in links:
                name = Path(urllib.parse.unquote(url)).name
                geladen += _speichern(url, ordner / (f"{praefix}_{name}" if praefix else name), neu, root)
        except OSError as e:
            log.warning(f"  ✗ {kennung}: nicht erreichbar ({e})")
    log.info(f"\n{geladen} Dateien geladen")
    return 0


def main(argv: list[str] | None = None) -> int:
    einrichten()
    parser = argparse.ArgumentParser(prog="python -m rsg2030 download", description="Quellen laden, Prüfsummen prüfen")
    parser.add_argument("--neu", action="store_true", help="alle Dateien neu laden, nicht nur fehlende")
    args = parser.parse_args(argv)
    download(neu=args.neu)
    probleme = pruefe()
    for p in probleme:
        log.warning(f"  ✗ {p}")
    log.info("Prüfsummen ok" if not probleme else f"{len(probleme)} Problem(e)")
    return 1 if probleme else 0


if __name__ == "__main__":
    sys.exit(main())
