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
from oesg_methodik.faecher import ZAE, ZAE_QUELLE, teile
from rsg2030.abgleich import gleiche_ab, paketversion
from rsg2030.analyse_eingang import lade_matrix_long
from rsg2030.config import LONG_DATEI, VERSORGUNGSDICHTE_DATEI, ausgabe_dir
from rsg2030.korrekturen import lade_regeln, regel_fuer_zelle
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll
from rsg2030.quellen import ist_rsg_verordnung, lade_quellen, ogd_pdf_url, ris_dokument_url
from rsg2030.schema import QUELLEN, massgeblicher_block, matrix_long

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

HERKUNFT_ZEILE = "insgesamt"
"""Zeile der Tabelle Versorgungsdichte, deren Herkunft die Seite zeigt – die einzige, die sie darstellt."""

QUELLE_ANGABE = ["pdf", "ris", "datei_url"]
"""`quellen` in `data.json`: je Verordnungs-PDF der Dateiname, die Seite des RIS-Dokuments (zum Nachlesen, mit
Kundmachung) und die Adresse der Datei selbst (ohne Sprungziel; `#page=<Seite>` hängt die Seite an)."""
MATRIX_ANGABE = ["quelle", "seite", "zeile_pdf", "block"]
"""`matrizen`: je Matrix und Abschnitt Index in `quellen`, Seite im PDF (1-basiert), die Beschriftung der Zeile
«insgesamt», wie sie im PDF gedruckt ist (`Zeile_PDF_roh`), und der maßgebliche Block – `aequivalent` bei den
Ländern, die in SVE planen (docs/DATEN.md, Fallstrick 3)."""
HERKUNFT_ANGABE = ["spalte", "roh", "wert", "quelle", "regel", "zeile_pdf"]
"""`herkunft`: je eingegangener Matrixspalte die Spalte, der Text wie gedruckt (`Roh`), der Wert nach Korrektur,
die `Quelle` (PDF | manuell | korrigiert | abgeleitet), der Index in `regeln` und – nur wo die Angabe aus einer
anderen Zeile als «insgesamt» kommt (ZAE) – deren Beschriftung im PDF."""
REGEL_ANGABE = ["regel", "art", "begruendung"]
"""`regeln`: je genannter Korrekturregel Name, Art und Begründung, wörtlich aus `korrekturen.csv`."""


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


def _adressen_je_pdf() -> dict[str, tuple[str, str]]:
    """Dateiname eines Verordnungs-PDF → (Seite des RIS-Dokuments, Adresse der Datei selbst)."""
    q = lade_quellen()
    return {
        Path(r["Datei"]).name: (
            ris_dokument_url(r["Kennung"]),
            ogd_pdf_url(r["Kennung"], r["Datei"], r["Praefix"]),
        )
        for _, r in q[ist_rsg_verordnung(q)].iterrows()
    }


def _matrizen(long: pd.DataFrame) -> dict[tuple[str, str], pd.DataFrame]:
    """(Ebene, Region_ID) → Zeilen der maßgeblichen Matrix (`schema.matrix_long`: SVE-Länder: Block der
    ÄAVE-Äquivalente) – dieselbe Auswahl wie in `analyse_eingang`, sonst zeigte die Seite die Herkunft eines
    anderen Werts."""
    out = {}
    for (land, ebene, rid), _ in long.groupby(["Land", "Ebene", "Region_ID"], sort=False):
        out[(str(ebene), str(rid))] = matrix_long(long, str(land), str(ebene), str(rid))
    return out


def _text(v: object) -> str | None:
    """Zelltext für JSON: fehlend und leer werden None (die Seite entscheidet, wie sie das schreibt)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return str(v) or None


def _zelle(zeilen: pd.DataFrame, zeile_id: str, fach: str) -> pd.Series | None:
    """Zelle einer Matrix; None, wenn die Matrix sie nicht hat (z. B. KFO ohne eigene Spalte)."""
    hit = zeilen[(zeilen["Zeile_ID"] == zeile_id) & (zeilen["Fach"] == fach)]
    return hit.iloc[0] if len(hit) else None


def baue_herkunft(insgesamt: pd.DataFrame, long: pd.DataFrame, regeln: pd.DataFrame) -> dict[str, object]:
    """`quellen`, `matrizen`, `herkunft` und `regeln` für `data.json`: woher jeder gezeigte ÄAVE-Wert kommt.

    Je Zelle der Zeile «insgesamt» die Matrixspalten, aus denen sie im ÖSG-Zuschnitt entstand
    (`oesg_methodik.faecher.teile`; die ZAE aus der Zeile spitalsambulant, `ZAE_QUELLE`), jede mit dem Text wie
    gedruckt (`Roh`), ihrer `Quelle` und – wo korrigiert wurde – der Regel mit Begründung.

    Bricht ab, wenn die Teile den veröffentlichten Wert nicht ergeben, wenn eine korrigierte Zelle keine
    eindeutige Regel hat oder wenn PDF und Seite einer Matrix nicht eindeutig sind: Dann zeigte die Seite eine
    Herkunft, die nicht zu den Zahlen gehört.
    """
    adressen = _adressen_je_pdf()
    pdfs: list[str] = []
    quellen: list[list[object]] = []
    matrizen: dict[str, list[object]] = {}
    herkunft: dict[str, list[list[object]]] = {}
    regel_angaben: list[list[object]] = []
    # Zeile in korrekturen.csv → Platz in `regel_angaben`. Nicht der Regelname als Schlüssel: Denselben Namen kann
    # es mehrfach geben, mit verschiedener Begründung (Kärnten, `plus:6.3`: in VR 22 eine Lücke, im Land ihre Folge).
    regel_platz: dict[object, int] = {}
    zeilen_je_matrix = _matrizen(long)

    def regel_index(zelle: pd.Series) -> int:
        """Platz der Regel in `regeln`; legt sie beim ersten Vorkommen an."""
        r = regel_fuer_zelle(regeln, zelle)
        if r is None:
            raise ValueError(
                f"keine eindeutige Korrekturregel für {zelle['Land']} {zelle['Ebene']} {zelle['Region_ID']} "
                f"{zelle['Abschnitt']} {zelle['Zeile_ID']} {zelle['Fach']} (Regel «{zelle['Regel']}»): "
                "passt korrekturen.csv noch zu den Daten?"
            )
        if r.name not in regel_platz:
            regel_platz[r.name] = len(regel_angaben)
            regel_angaben.append([str(r["Regel"]), str(r["Art"]), str(r["Begruendung"])])
        return regel_platz[r.name]

    for r in insgesamt.itertuples():
        if (r.Ebene, r.Region_ID) not in zeilen_je_matrix:
            raise ValueError(
                f"{r.Ebene} {r.Region_ID} steht in der Tabelle Versorgungsdichte, aber nicht in der Tabelle "
                "Planungsmatrizen: passen die beiden Dateien zusammen?"
            )
        zeilen = zeilen_je_matrix[(r.Ebene, r.Region_ID)]
        teil_zeilen = zeilen[zeilen["Abschnitt"] == r.Abschnitt]
        angaben: list[list[object]] = []
        teile_werte: list[float] = []
        for spalte in teile(r.Fach, HERKUNFT_ZEILE):
            aus_zeile = ZAE_QUELLE[0] if spalte == ZAE else HERKUNFT_ZEILE
            zelle = _zelle(teil_zeilen, aus_zeile, ZAE_QUELLE[1] if spalte == ZAE else spalte)
            if zelle is None:
                continue
            if zelle["Quelle"] not in QUELLEN:
                raise ValueError(f"unbekannte Quelle «{zelle['Quelle']}» in {r.Region_ID} {r.Abschnitt} {spalte}")
            wert = zelle["Wert"]
            if pd.notna(wert):
                teile_werte.append(float(wert))
            angaben.append(
                [
                    spalte,
                    _text(zelle["Roh"]),
                    float(wert) if pd.notna(wert) else None,
                    str(zelle["Quelle"]),
                    regel_index(zelle) if _text(zelle["Regel"]) else None,
                    _text(zelle["Zeile_PDF_roh"]) if aus_zeile != HERKUNFT_ZEILE else None,
                ]
            )
        if not angaben:
            raise ValueError(f"keine Herkunft für {r.Region_ID} {r.Abschnitt} {r.Fach}: passt die Seite zu den Daten?")
        summe = round(sum(teile_werte), 6)  # wie `faecher.summe_im_zuschnitt`: ohne Runden blieben Gleitkomma-Reste
        if abs(summe - float(r.AAVE)) > 1e-6:
            raise ValueError(
                f"Herkunft von {r.Region_ID} {r.Abschnitt} {r.Fach} ergibt {summe}, die Tabelle nennt {r.AAVE}: "
                "die gezeigten Spalten sind nicht die, aus denen der Wert entstand"
            )
        herkunft[f"{r.Region_ID}|{r.Abschnitt}|{r.Fach}"] = angaben

        schluessel = f"{r.Region_ID}|{r.Abschnitt}"
        if schluessel not in matrizen:
            benutzt = teil_zeilen[teil_zeilen["Zeile_ID"].isin([HERKUNFT_ZEILE, ZAE_QUELLE[0]])]
            datei, seite = sorted(set(benutzt["PDF"].dropna())), sorted(set(benutzt["Seite"].dropna()))
            if len(datei) != 1 or len(seite) != 1:
                raise ValueError(
                    f"{r.Region_ID} {r.Abschnitt}: PDF {datei} und Seite {seite} der Matrix nicht eindeutig"
                )
            if datei[0] not in adressen:
                raise ValueError(f"{datei[0]} steht nicht als RSG-Verordnung in quellen.csv")
            if datei[0] not in pdfs:
                pdfs.append(datei[0])
                quellen.append([datei[0], *adressen[datei[0]]])
            insgesamt_zeile = _zelle(teil_zeilen, HERKUNFT_ZEILE, r.Fach)
            matrizen[schluessel] = [
                pdfs.index(datei[0]),
                int(seite[0]),
                _text(insgesamt_zeile["Zeile_PDF_roh"]) if insgesamt_zeile is not None else None,
                massgeblicher_block(zeilen),
            ]
    return {"quellen": quellen, "matrizen": matrizen, "herkunft": herkunft, "regeln": regel_angaben}


def baue_daten(tabelle: pd.DataFrame, regionen: pd.DataFrame, kacheln: pd.DataFrame, faecher: pd.DataFrame,
               long: pd.DataFrame, regeln: pd.DataFrame, meta: dict[str, str]) -> dict[str, object]:  # fmt: skip
    """Inhalt von `data.json`: Zeile «insgesamt» der Tabelle Versorgungsdichte, wie sie ist, dazu die Herkunft
    jedes Werts aus der Tabelle Planungsmatrizen (`baue_herkunft`)."""
    fehlt = [s for s in SPALTEN if s not in tabelle.columns]
    if fehlt:
        raise ValueError(f"Tabelle Versorgungsdichte ohne Spalten {fehlt}: passt die Seite noch zu den Daten?")
    insgesamt = tabelle[tabelle["Zeile_ID"] == HERKUNFT_ZEILE]
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
        **baue_herkunft(insgesamt, long, regeln),
    }


def baue_seite(tabelle_csv: Path, long_csv: Path, ziel: Path) -> Path:
    """Seite bauen; gibt den Pfad von `data.json` zurück."""
    meta = {
        "datei": tabelle_csv.name,
        "version": paketversion(),
        "sha256": hashlib.sha256(tabelle_csv.read_bytes()).hexdigest(),
        "matrizen_datei": long_csv.name,
        "matrizen_sha256": hashlib.sha256(long_csv.read_bytes()).hexdigest(),
        "commit": seiten_commit(),
        "repo": repo_url(),
    }
    daten = baue_daten(
        pd.read_csv(tabelle_csv, dtype={"Region_ID": str}),
        lade_regionen(),
        pd.read_csv(web_dir() / "kacheln.csv", dtype=str),
        pd.read_csv(web_dir() / "faecher.csv", dtype=str),
        lade_matrix_long(long_csv),
        lade_regeln(),
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
    tabelle, long = ausgabe_dir() / VERSORGUNGSDICHTE_DATEI, ausgabe_dir() / LONG_DATEI
    for datei in (tabelle, long):
        if not datei.is_file():
            log.error(f"❌ {datei} fehlt: erst «python -m rsg2030 alles» oder die Datei des Release dorthin legen")
            return 1
        if gleiche_ab(datei) is not True:
            log.error(f"❌ {datei.name} ist nicht die Version {paketversion()}: Seite nicht gebaut")
            return 1
    try:
        daten = baue_seite(tabelle, long, ziel_dir())
    except (ValueError, KeyError, FileNotFoundError) as e:
        log.error(f"❌ Seite nicht gebaut: {e}")
        return 1
    log.info(f"Seite gebaut: {daten.parent} (Ansehen: python -m http.server -d {daten.parent})")
    schreibe_laufprotokoll(ausgabe_dir(), "web", [daten], {"Tabelle": tabelle.name, "Matrizen": long.name})
    return 0


if __name__ == "__main__":
    sys.exit(main())
