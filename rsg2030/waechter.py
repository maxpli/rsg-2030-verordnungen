"""Wächter: Gibt es neue RSG-2030-Verordnungen, einen neuen ÖSG, oder wurde eine Quelle online ersetzt?

Das Register (`quellen/quellen.csv`) legt fest, welche Dateien eine Datenversion enthält – der Download lädt nur diese
(notfalls die geprüfte Fassung aus dem Archiv). Der Wächter meldet nur **Hinweise**; ob daraus eine neue Datenversion
wird, entscheidet ein Mensch (docs/PIPELINE.md).

- **RIS** (immer): Suche nach allen geltenden RSG-Verordnungen mit «2030» gegen die Dokumentnummern im Register – neu
  (neue Verordnung oder Änderung, die eine neue Nummer bekommt) oder nicht mehr gefunden (außer Kraft, ersetzt).
  Ebenso das geltende ÖSG-Gutachten: Eine neue Fassung kann Richtwerte, Regionen oder die Vorlage der Matrix ändern.
- **Originale** (`--quellen`): jede URL-Quelle neu laden und die Prüfsumme mit dem Register vergleichen. Kein Raten:
  erkennt jeden Austausch unter derselben Adresse. Was unter *neuer* Adresse erscheint (neuer Prognose-Jahrgang,
  Regionale Gliederung oder Methodenband zu einem neuen ÖSG-Stand), erkennt es nicht – dafür die Termine in
  docs/PIPELINE.md.
- **Archivkopien** (`--archiv`): jede Archivkopie (Spalte «Archiv») laden und prüfen, ob sie die geprüfte Fassung ist.
  Sie springt ein, wenn das Original fehlt oder ersetzt wurde – das soll nicht erst dann auffallen. Die Wayback
  Machine leitet einen Zeitstempel ohne Aufnahme still auf die nächste Aufnahme um; das findet nur die Prüfsumme.

Exit 1 bei einem Hinweis, damit GitHub eine Mail schickt (RIS wöchentlich, Originale und Archivkopien monatlich).

    python -m rsg2030 waechter [--quellen] [--archiv]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
import urllib.error
import urllib.parse
from datetime import date

import pandas as pd

from rsg2030.protokoll import einrichten
from rsg2030.quellen import ist_rsg_verordnung, lade_quellen
from rsg2030.quellen.download import RIS_URL, abrufen, entpacke_archiv

log = logging.getLogger(__name__)

# --- RIS ---------------------------------------------------------------------------------------

# Suche im RIS «Strukturpläne Gesundheit»: nur RSG-Verordnungen, Suchwort 2030, kundgemacht ab 2017, Fassung heute.
SUCHE_RSG = {
    "Abfrage": "Spg",
    "VonKundmachungsdatum": "01.01.2017",
    "SucheNachOsgGutachten": "False",
    "SucheNachOsgVerordnung": "False",
    "SucheNachRsgGutachten": "False",
    "SucheNachRsgVerordnung": "True",
    "Suchworte": "2030",
    "ResultPageSize": "100",
    "Position": "1",
    "SkipToDocumentPage": "true",
}
# Der ÖSG ist im RIS als ÖSG-Gutachten kundgemacht; die Suche mit Fassung heute liefert nur das geltende.
SUCHE_OESG = {
    **SUCHE_RSG,
    "SucheNachOsgGutachten": "True",
    "SucheNachRsgVerordnung": "False",
    "Suchworte": "",
}
DOKUMENT_RE = re.compile(r"Dokumentnummer=(SPG_[A-Z0-9_]+)")


def such_url(stichtag: date, suche: dict[str, str] = SUCHE_RSG) -> str:
    heute = stichtag.strftime("%d.%m.%Y")
    return f"{RIS_URL}/Ergebnis.wxe?" + urllib.parse.urlencode(
        {**suche, "FassungVom": heute, "BisKundmachungsdatum": heute}
    )


def ris_dokumente(stichtag: date | None = None, suche: dict[str, str] = SUCHE_RSG) -> set[str]:
    """Dokumentnummern aller Treffer der RIS-Suche (Stand `stichtag`, sonst heute)."""
    seite = abrufen(such_url(stichtag or date.today(), suche)).decode("utf-8", errors="replace")
    treffer = set(DOKUMENT_RE.findall(seite))
    if not treffer:
        raise RuntimeError(
            "RIS-Suche ohne Treffer – eher hat sich die RIS-Seite geändert als die Rechtslage; Suche prüfen"
        )
    if len(treffer) >= int(suche["ResultPageSize"]):
        raise RuntimeError(f"RIS-Suche liefert {len(treffer)} Treffer – mehr als eine Seite, Abgleich unvollständig")
    return treffer


def pruefe_ris(q: pd.DataFrame) -> list[str]:
    ris = q[ist_rsg_verordnung(q)].drop_duplicates("Kennung")
    register, land = set(ris["Kennung"]), dict(zip(ris["Kennung"], ris["Bundesland"]))
    treffer = ris_dokumente()
    hinweise = [
        f"RIS: neue Verordnung/Änderung {k} – {RIS_URL}/Dokument.wxe?Abfrage=Spg&Dokumentnummer={k}"
        for k in sorted(treffer - register)
    ]
    hinweise += [
        f"RIS: {k} ({land[k]}) nicht mehr gefunden – außer Kraft oder ersetzt?" for k in sorted(register - treffer)
    ]
    if not hinweise:
        log.info(f"  ✓ RIS: {len(register)} Verordnungen wie im Register")
    return hinweise


def pruefe_oesg(q: pd.DataFrame) -> list[str]:
    """Das geltende ÖSG-Gutachten im RIS gegen das Register."""
    register = set(q.loc[(q["Herkunft"] == "RIS") & ~ist_rsg_verordnung(q), "Kennung"])
    treffer = ris_dokumente(suche=SUCHE_OESG)
    hinweise = [
        f"RIS: neuer ÖSG {k} – Richtwerte, Regionen und Vorlage der Matrix prüfen (docs/PIPELINE.md) – "
        f"{RIS_URL}/Dokument.wxe?Abfrage=Spg&Dokumentnummer={k}"
        for k in sorted(treffer - register)
    ]
    hinweise += [f"RIS: ÖSG {k} gilt nicht mehr – ersetzt?" for k in sorted(register - treffer)]
    if not hinweise:
        log.info(f"  ✓ RIS: ÖSG {', '.join(sorted(register))} gilt wie im Register")
    return hinweise


# --- Originale der URL-Quellen ------------------------------------------------------------------


def pruefe_originale(q: pd.DataFrame) -> list[str]:
    """Jede URL-Quelle laden und mit der registrierten Prüfsumme vergleichen."""
    url = q[q["Herkunft"] == "URL"]
    hinweise: list[str] = []
    for _, r in url.iterrows():
        try:
            daten = abrufen(r["Kennung"])
        except OSError as e:
            hinweise.append(
                f"{r['Datei']}: Originaladresse nicht erreichbar ({e}) – Archivkopie vorhanden: {bool(r['Archiv'])}"
            )
            continue
        if hashlib.sha256(daten).hexdigest() != r["SHA256"]:
            hinweise.append(f"{r['Datei']}: online durch eine andere Fassung ersetzt (Download nutzt die Archivkopie)")
    if not hinweise:
        log.info(f"  ✓ {len(url)} URL-Quellen: Originale unverändert")
    return hinweise


# --- Archivkopien der URL-Quellen ---------------------------------------------------------------


def pruefe_archiv(q: pd.DataFrame) -> list[str]:
    """Jede Archivkopie laden und mit der registrierten Prüfsumme vergleichen."""
    url = q[q["Herkunft"] == "URL"]
    hinweise: list[str] = []
    for _, r in url.iterrows():
        if not r["Archiv"]:
            hinweise.append(f"{r['Datei']}: keine Archivkopie im Register (Spalte «Archiv»)")
            continue
        try:
            daten = entpacke_archiv(abrufen(r["Archiv"]), r["SHA256"])
        except OSError as e:
            hinweise.append(f"{r['Datei']}: Archivkopie nicht erreichbar ({e})")
            continue
        if hashlib.sha256(daten).hexdigest() != r["SHA256"]:
            hinweise.append(
                f"{r['Datei']}: Archivkopie ist nicht die geprüfte Fassung – Original neu einreichen "
                "(web.archive.org/save), Zeitstempel in Spalte «Archiv» eintragen"
            )
    if not hinweise:
        log.info(f"  ✓ {len(url)} URL-Quellen: Archivkopien sind die geprüfte Fassung")
    return hinweise


def main(argv: list[str] | None = None) -> int:
    einrichten()
    parser = argparse.ArgumentParser(prog="python -m rsg2030 waechter", description="Neue Verordnungen oder Quellen?")
    parser.add_argument("--quellen", action="store_true", help="auch die Originale der URL-Quellen laden und prüfen")
    parser.add_argument("--archiv", action="store_true", help="auch die Archivkopien der URL-Quellen laden und prüfen")
    args = parser.parse_args(argv)
    q = lade_quellen()
    hinweise = (
        pruefe_ris(q)
        + pruefe_oesg(q)
        + (pruefe_originale(q) if args.quellen else [])
        + (pruefe_archiv(q) if args.archiv else [])
    )
    for h in hinweise:
        log.warning(f"  ✗ {h}")
    if hinweise:
        log.warning("Hinweis: Neues gefunden – prüfen, ob eine neue Datenversion sinnvoll ist (docs/PIPELINE.md)")
        return 1
    log.info("✓ Nichts Neues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
