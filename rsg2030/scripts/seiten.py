"""Seitenregister `eingaben/2026/seiten.csv` aus den PDFs erzeugen (statt von Hand pflegen).

Je Bundesland werden alle PDFs aus dem Quellenregister (RIS, quellen/quellen.csv) durchsucht. Eine Seite ist eine Matrixseite, wenn
der Parser darauf mindestens `MIN_ZEILEN` verschiedene Matrixzeilen erkennt (echte Matrizen: 19–30,
Methodik-/Stationärseiten: 0–1):

- mit «Versorgungsregion NN» → VR-Matrix, ohne Nummer → BL-Matrix
- Seite direkt danach ohne Nummer mit `MIN_FOLGE`–`MIN_ZEILEN - 1` Zeilen → Folgeseite (Kärnten VR 22)
- Matrizen in mehreren Dokumenten eines Landes → die neueste Verordnung gilt (Datum der RIS-Nummer)

Was laut ÖSG fehlt (Bildseiten ohne Textebene), wird nachgefragt. Vorschlag: dasselbe Dokument und
die Bildseite zwischen den Nachbarmatrizen. Ohne Terminal bzw. mit `--ja` werden die Vorschläge
übernommen; ohne Vorschlag bleibt die Matrix offen (Exit 1).

    python -m rsg2030 seiten [--ja]
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pdfplumber

from oesg_methodik import LAND_KURZ
from oesg_methodik.pfade import OESG_REGIONEN_CSV
from rsg2030.config import quellen_dir, seiten_csv
from rsg2030.matrix_extract import TEXT_MIN_ZEICHEN, kompakt, lese_matrix
from rsg2030.protokoll import einrichten
from rsg2030.quellenpruefung import lade_dokumente

log = logging.getLogger(__name__)

MIN_ZEILEN = 10
MIN_FOLGE = 3
SPALTEN = ["Land", "Ebene", "Region_ID", "Region_Name", "Datei", "Seite", "Folgeseiten"]
_VR = re.compile(r"Versorgungsregion\s*(\d{2})")
_DATUM = re.compile(r"_(20\d{6})_")


@dataclass
class Dokument:
    datei: str
    """relativ zu `config.quellen_dir()`"""
    datum: str
    matrizen: dict[str, int] = field(default_factory=dict)
    """BL bzw. VR-Nummer → 1-basierte Seite"""
    folgeseiten: dict[str, list[int]] = field(default_factory=dict)
    bildseiten: list[int] = field(default_factory=list)


def scanne(datei: str, datum: str) -> Dokument:
    pdf = quellen_dir() / datei
    dok = Dokument(datei, datum)
    zeilen: dict[int, tuple[int, str | None]] = {}
    with pdfplumber.open(pdf) as d:
        for i, page in enumerate(d.pages):
            if len(page.chars) < TEXT_MIN_ZEICHEN:
                dok.bildseiten.append(i + 1)
                continue
            text = page.extract_text() or ""
            if "spitalsambulant" not in kompakt(text):
                continue
            n = len({r["Zeile_ID"] for r in lese_matrix(pdf, (i,), land="?", ebene="?", region_id="?").datensaetze})
            m = _VR.search(text)
            zeilen[i + 1] = (n, m.group(1) if m else None)
    letzte = None
    for seite in sorted(zeilen):
        n, vr = zeilen[seite]
        if n >= MIN_ZEILEN:
            key = vr or "BL"
            if key in dok.matrizen:
                raise ValueError(f"{datei}: {key} doppelt (S.{dok.matrizen[key]} und S.{seite})")
            dok.matrizen[key] = seite
            letzte = (key, seite)
        elif (
            vr is None
            and n >= MIN_FOLGE
            and letzte
            and seite == letzte[1] + len(dok.folgeseiten.get(letzte[0], [])) + 1
        ):
            dok.folgeseiten.setdefault(letzte[0], []).append(seite)
    return dok


def _frage(text: str, vorschlag: str, interaktiv: bool) -> str:
    if not interaktiv:
        return vorschlag
    antwort = input(f"   {text} [{vorschlag or 'leer = überspringen'}]: ").strip()
    return antwort or vorschlag


def vorschlag(*, interaktiv: bool) -> tuple[pd.DataFrame, list[str]]:
    oesg = pd.read_csv(OESG_REGIONEN_CSV)
    dokumente = lade_dokumente()
    pdfs = dokumente[(dokumente["Herkunft"] == "RIS") & dokumente["Datei"].str.lower().str.endswith(".pdf")]
    zeilen: list[dict] = []
    offen: list[str] = []
    for _, g in oesg.groupby("BL_Nr"):
        voll = g["Bundesland"].iloc[0]
        land = LAND_KURZ.get(voll, voll)
        soll = ["BL", *[str(v) for v in sorted(g["VR"].unique())]]
        namen = {str(r.VR): r.VR_Name for r in g.drop_duplicates("VR").itertuples()}
        kandidaten = []
        for _, d in pdfs[pdfs["Bundesland"] == voll].iterrows():
            m = _DATUM.search(d["Kennung"])
            dok = scanne(d["Datei"], m.group(1) if m else "")
            if dok.matrizen:
                kandidaten.append(dok)
        if not kandidaten:
            offen.append(f"{land}: keine Matrixseite in {len(pdfs[pdfs['Bundesland'] == voll])} PDFs gefunden")
            continue
        dok = max(kandidaten, key=lambda k: (k.datum, len(k.matrizen)))
        hinweis = [k.datei for k in kandidaten if k is not dok]
        log.info(
            f"{land}: {Path(dok.datei).name} – {len(dok.matrizen)} Matrizen gefunden"
            + (
                f" (ältere Verordnung mit Matrizen ignoriert: {', '.join(Path(h).name for h in hinweis)})"
                if hinweis
                else ""
            )
        )

        seiten = dict(dok.matrizen)
        for i, key in enumerate(soll):
            if key in seiten:
                continue
            vor = max([seiten[k] for k in soll[:i] if k in seiten], default=0)
            nach = min([seiten[k] for k in soll[i + 1 :] if k in seiten], default=10**6)
            bild = [p for p in dok.bildseiten if vor < p < nach]
            name = "BL" if key == "BL" else f"VR {key} ({namen[key]})"
            log.info(
                f"   {name}: nicht gefunden (Bildseite?)"
                + (f" – Bildseite(n) ohne Text dazwischen: {bild}" if bild else "")
            )
            datei = _frage("Dokument", dok.datei, interaktiv)
            seite = _frage("Seite", str(bild[0]) if bild else "", interaktiv)
            if not seite:
                offen.append(f"{land} {name}: Seite unbekannt")
                continue
            if datei != dok.datei:
                raise ValueError(f"{land} {name}: Matrizen eines Landes müssen in einem Dokument stehen ({dok.datei})")
            seiten[key] = int(seite)
        for key in soll:
            if key not in seiten:
                continue
            zeilen.append(
                {
                    "Land": land,
                    "Ebene": "BL" if key == "BL" else "VR",
                    "Region_ID": land if key == "BL" else key,
                    "Region_Name": "" if key == "BL" else namen[key],
                    "Datei": dok.datei,
                    "Seite": seiten[key],
                    "Folgeseiten": ";".join(str(p) for p in dok.folgeseiten.get(key, [])),
                }
            )
        extra = set(dok.matrizen) - set(soll)
        if extra:
            offen.append(f"{land}: Matrizen ohne VR laut ÖSG: {sorted(extra)}")
    return pd.DataFrame(zeilen, columns=SPALTEN), offen


def main(argv: list[str] | None = None) -> int:
    einrichten()
    parser = argparse.ArgumentParser(
        prog="python -m rsg2030 seiten", description="Seitenregister aus den PDFs erzeugen"
    )
    parser.add_argument(
        "--ja", action="store_true", help="Vorschläge übernehmen und seiten.csv ohne Rückfrage schreiben"
    )
    args = parser.parse_args(argv)
    interaktiv = sys.stdin.isatty() and not args.ja
    neu, offen = vorschlag(interaktiv=interaktiv)
    for o in offen:
        log.warning(f"  ✗ {o}")

    neu = neu.astype(str)
    pfad = seiten_csv()
    if pfad.is_file():
        alt = pd.read_csv(pfad, dtype=str, keep_default_na=False)
        if alt.equals(neu):
            log.info(f"\n{pfad.name}: unverändert ({len(neu)} Matrizen)")
            return 1 if offen else 0
        diff = alt.merge(neu, how="outer", indicator=True)
        log.info(f"\n{pfad.name} würde sich ändern:")
        for _, r in diff[diff["_merge"] != "both"].iterrows():
            log.info(
                f"   {'−' if r['_merge'] == 'left_only' else '+'} {r['Land']} {r['Region_ID']} S.{r['Seite']} "
                f"{r['Folgeseiten']} {Path(r['Datei']).name}"
            )
        ja = args.ja or (interaktiv and _frage("überschreiben? (j/n)", "n", True).lower() == "j")
        if not ja:
            log.info("nicht geschrieben (bestätigen oder --ja)")
            return 1
    pfad.parent.mkdir(parents=True, exist_ok=True)
    neu.to_csv(pfad, index=False, lineterminator="\n")
    log.info(f"{pfad.name}: {len(neu)} Matrizen geschrieben")
    return 1 if offen else 0


if __name__ == "__main__":
    raise SystemExit(main())
