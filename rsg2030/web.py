"""Webseite zur Tabelle Versorgungsdichte bauen: `data.json` und die Dateien aus `web/` → `daten_ergebnis/web/`.

Die Seite stellt die Tabelle mit Lesehilfen dar (docs/WEB.md); die Werte übernimmt sie unverändert aus
`RSG_2030_Versorgungsdichte.csv`. Gelesen wird die Tabelle in `daten_ergebnis/` – lokal nach `python -m rsg2030 versorgungsdichte`, im Workflow
die Datei des Release. Gebaut wird nur, wenn sie Byte für Byte der Version dieses Pakets entspricht
(`erwartete_ausgaben.csv`); nur dann darf die Seite «Release <Version>» sagen.

Namen und Lage kommen je aus einer Quelle: Regionen und Länder aus `oesg_regionen.csv`, Fächer aus
`web/faecher.csv`, Kacheln aus `web/kacheln.csv`. Passt eine davon nicht zur Tabelle, bricht der Bau ab.

    python -m rsg2030 web
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

import pandas as pd

from oesg_methodik.bevoelkerung import lade_regionen
from rsg2030.abgleich import gleiche_ab, paketversion
from rsg2030.config import VERSORGUNGSDICHTE_DATEI, ausgabe_dir
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll

log = logging.getLogger(__name__)

SEITE = ("index.html", "app.js", "style.css", "fonts")
"""Dateien und Ordner aus `web/`, die zur Seite gehören (die CSV-Dateien dort sind Eingaben für `data.json`)."""

SPALTEN = [
    "Land", "Ebene", "Region_ID", "Abschnitt", "Jahr", "Zeile_ID", "Fach", "AAVE", "Zuschnitt", "Bevoelkerung",
    "VD", "VDmin", "VDmax", "Lage_im_Intervall", "Position_im_Intervall", "AAVE_Abstand_Intervall",
]  # fmt: skip
"""Spalten der Tabelle Versorgungsdichte, die die Seite liest (docs/DATEN.md)."""

WERT = ["VD", "AAVE", "Bevoelkerung", "Jahr", "Lage_im_Intervall", "Position_im_Intervall", "AAVE_Abstand_Intervall", "Zuschnitt"]  # fmt: skip
"""Reihenfolge der Angaben je Zelle in `data.json` (`werte`); app.js liest sie in derselben Reihenfolge."""


def web_dir() -> Path:
    """Quelldateien der Seite im Klon (nicht Teil des installierten Pakets)."""
    return Path(__file__).resolve().parents[1] / "web"


def ziel_dir() -> Path:
    return ausgabe_dir() / "web"


def repo_url() -> str:
    """Adresse des Repositorys aus pyproject.toml (`[project.urls] Repository`)."""
    try:
        for eintrag in metadata("rsg-2030-verordnungen").get_all("Project-URL") or []:
            name, _, url = eintrag.partition(",")
            if name.strip() == "Repository":
                return url.strip()
    except PackageNotFoundError:
        pass
    return "https://github.com/maxpli/rsg-2030-verordnungen"


def seiten_commit() -> str:
    """Commit, aus dem die Seite gebaut wird: im Workflow `GITHUB_SHA`, sonst `git rev-parse HEAD`."""
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=web_dir(), capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unbekannt"


def _faecher(insgesamt: pd.DataFrame, faecher_csv: pd.DataFrame) -> list[dict[str, object]]:
    """Fächer in der Reihenfolge von `faecher.csv`, Soll-Intervall aus der Tabelle."""
    in_tabelle, in_liste = set(insgesamt["Fach"]), set(faecher_csv["Fach"])
    if in_tabelle != in_liste:
        raise ValueError(
            f"web/faecher.csv passt nicht zur Tabelle: fehlt {sorted(in_tabelle - in_liste)}, "
            f"zu viel {sorted(in_liste - in_tabelle)}"
        )
    unbekannt = set(faecher_csv["Teil_von"].dropna()) - in_liste
    if unbekannt:
        raise ValueError(f"web/faecher.csv: «Teil_von» nennt Fächer, die es nicht gibt: {sorted(unbekannt)}")
    intervall = insgesamt.drop_duplicates(["Fach", "VDmin", "VDmax"])
    if intervall["Fach"].duplicated().any():
        raise ValueError("Tabelle Versorgungsdichte: ein Fach hat mehr als ein Soll-Intervall")
    iv = intervall.set_index("Fach")
    return [
        {
            "id": f.Fach,
            "name": f.Name,
            "teil_von": None if pd.isna(f.Teil_von) else f.Teil_von,
            "min": float(iv.at[f.Fach, "VDmin"]),
            "max": float(iv.at[f.Fach, "VDmax"]),
        }
        for f in faecher_csv.itertuples()
    ]


def _regionen(insgesamt: pd.DataFrame, regionen: pd.DataFrame, kacheln: pd.DataFrame) -> list[dict[str, object]]:
    """Regionen der Tabelle mit Namen laut ÖSG-Gliederung und Kachel; VR vor BL, je nach Bundesland-Nummer."""
    vr = regionen.drop_duplicates("VR").assign(VR=lambda d: d["VR"].astype(str)).set_index("VR")
    # Kurzname des Landes (Spalte «Land» der Tabelle) → Name laut ÖSG-Gliederung, über die VR der Tabelle
    paare = insgesamt.loc[insgesamt["Ebene"] == "VR", ["Land", "Region_ID"]].drop_duplicates("Land")
    lang = {r.Land: vr.at[str(r.Region_ID), "Bundesland"] for r in paare.itertuples()}
    nr = dict(zip(vr["Bundesland"], vr["BL_Nr"]))
    kachel = {(k.Ebene, str(k.Region_ID)): k for k in kacheln.itertuples()}

    out: list[dict[str, object]] = []
    fehlt: list[str] = []
    for (ebene, rid), zeilen in insgesamt.groupby(["Ebene", "Region_ID"], sort=False):
        rid, land = str(rid), str(zeilen["Land"].iloc[0])
        k = kachel.get((ebene, rid))
        if k is None:
            fehlt.append(f"{ebene} {rid}")
            continue
        out.append(
            {
                "id": rid,
                "ebene": ebene,
                "land": land,
                "land_name": lang[land],
                "name": vr.at[rid, "VR_Name"] if ebene == "VR" else lang[land],
                "spalte": int(k.Spalte),
                "zeile": int(k.Zeile),
                "beschriftung": str(k.Beschriftung),
            }
        )
    if fehlt:
        raise ValueError(f"web/kacheln.csv: keine Kachel für {', '.join(fehlt)}")
    for ebene in ("VR", "BL"):
        felder = [(r["spalte"], r["zeile"]) for r in out if r["ebene"] == ebene]
        if len(felder) != len(set(felder)):
            raise ValueError(f"web/kacheln.csv: zwei Regionen der Ebene {ebene} auf demselben Feld")
    out.sort(key=lambda r: (r["ebene"] != "VR", nr[r["land_name"]], int(str(r["id"])) if r["ebene"] == "VR" else 0))
    return out


GANZZAHLIG = {"Bevoelkerung", "Jahr"}


def _wert(spalte: str, v: object) -> object:
    """Angabe für JSON: Bevölkerung und Jahr als ganze Zahl, fehlende Werte als None, sonst wie in der Tabelle."""
    if isinstance(v, float) and math.isnan(v):
        return None
    if spalte in GANZZAHLIG:
        return int(v)  # type: ignore[call-overload]
    return v.item() if hasattr(v, "item") else v


def baue_daten(tabelle: pd.DataFrame, regionen: pd.DataFrame, kacheln: pd.DataFrame, faecher: pd.DataFrame,
               meta: dict[str, str]) -> dict[str, object]:  # fmt: skip
    """Inhalt von `data.json`: Zeile «insgesamt» der Tabelle Versorgungsdichte, wie sie ist."""
    fehlt = [s for s in SPALTEN if s not in tabelle.columns]
    if fehlt:
        raise ValueError(f"Tabelle Versorgungsdichte ohne Spalten {fehlt}: passt die Seite noch zu den Daten?")
    insgesamt = tabelle[tabelle["Zeile_ID"] == "insgesamt"]
    if insgesamt.empty:
        raise ValueError("Tabelle Versorgungsdichte ohne Zeile «insgesamt»")
    if insgesamt["Lage_im_Intervall"].isna().any():
        raise ValueError("Zeile «insgesamt» ohne Lage zum Soll-Intervall: passt die Seite noch zu den Daten?")
    werte = {
        f"{r['Region_ID']}|{r['Abschnitt']}|{r['Fach']}": [_wert(s, r[s]) for s in WERT]
        for r in insgesamt.to_dict("records")
    }
    return {
        "meta": meta,
        "faecher": _faecher(insgesamt, faecher),
        "regionen": _regionen(insgesamt, regionen, kacheln),
        "werte": werte,
    }


def baue_seite(tabelle_csv: Path, ziel: Path) -> Path:
    """Seite bauen; gibt den Pfad von `data.json` zurück."""
    meta = {
        "datei": tabelle_csv.name,
        "version": paketversion(),
        "sha256": hashlib.sha256(tabelle_csv.read_bytes()).hexdigest(),
        "commit": seiten_commit(),
        "repo": repo_url(),
    }
    daten = baue_daten(
        pd.read_csv(tabelle_csv, dtype={"Region_ID": str}),
        lade_regionen(),
        pd.read_csv(web_dir() / "kacheln.csv", dtype=str),
        pd.read_csv(web_dir() / "faecher.csv", dtype=str),
        meta,
    )
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    for name in SEITE:
        quelle = web_dir() / name
        if quelle.is_dir():
            shutil.copytree(quelle, ziel / name)
        else:
            shutil.copyfile(quelle, ziel / name)
    pfad = ziel / "data.json"
    pfad.write_text(
        json.dumps(daten, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8"
    )
    return pfad


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 web",
        description="Webseite zur Tabelle Versorgungsdichte nach daten_ergebnis/web/ bauen (docs/WEB.md)",
    ).parse_args(argv)
    tabelle = ausgabe_dir() / VERSORGUNGSDICHTE_DATEI
    if not tabelle.is_file():
        log.error(f"❌ {tabelle} fehlt: erst «python -m rsg2030 alles» oder die Datei des Release dorthin legen")
        return 1
    if gleiche_ab(tabelle) is not True:
        log.error(f"❌ {tabelle.name} ist nicht die Version {paketversion()}: Seite nicht gebaut")
        return 1
    try:
        daten = baue_seite(tabelle, ziel_dir())
    except (ValueError, KeyError, FileNotFoundError) as e:
        log.error(f"❌ Seite nicht gebaut: {e}")
        return 1
    log.info(f"Seite gebaut: {daten.parent} (Ansehen: python -m http.server -d {daten.parent})")
    schreibe_laufprotokoll(ausgabe_dir(), "web", [daten], {"Tabelle": tabelle.name})
    return 0


if __name__ == "__main__":
    sys.exit(main())
