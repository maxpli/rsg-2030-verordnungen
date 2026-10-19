"""Prüfbericht eines Laufs (`daten_ergebnis/Pruefbericht.md`): alle Zahlen an einer Stelle.

Die Doku beschreibt, *wie* geprüft wird (docs/PRUEFUNG.md); wie viele Zellen, Prüfungen, Korrekturen und Bestätigungen es
in einem Lauf sind, steht nur hier – erzeugt, nicht abgeschrieben. Ohne Zeitangabe, damit gleiche Daten einen gleichen
Bericht ergeben (Zeit und Git-Stand: Laufprotokoll).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from rsg2030.abgleich import paketversion
from rsg2030.manuell import manuelle_matrizen

if TYPE_CHECKING:
    from rsg2030.freigabe import FreigabeStand
    from rsg2030.pipeline import PipelineErgebnis

BERICHT_DATEI = "Pruefbericht.md"
_STATUS = ["ok", "bekannt", "nicht_pruefbar", "abweichung"]


def _zahl(n: int | float) -> str:
    return f"{int(n):,}".replace(",", ".")


def _tabelle(df: pd.DataFrame) -> list[str]:
    kopf = "| " + " | ".join(map(str, df.columns)) + " |"
    trenner = "|" + "|".join("---" if i == 0 else "---:" for i in range(len(df.columns))) + "|"
    zeilen = [
        "| " + " | ".join(_zahl(v) if isinstance(v, (int, float)) else str(v) for v in r) + " |"
        for r in df.itertuples(index=False)
    ]
    return [kopf, trenner, *zeilen]


def _zweitlesung(p: PipelineErgebnis) -> list[str]:
    zw = p.zweitlesung
    z = [
        f"{zw.matrizen} von {zw.matrizen + len(zw.fehlend)} Matrizen zweitgelesen (KI aus dem Seitenbild), "
        f"{_zahl(zw.verglichen)} Zellen verglichen, {_zahl(len(zw.abweichungen))} Abweichungen, "
        f"{_zahl(len(zw.nicht_verglichen))} Zellen nicht verglichen (Zeile der Zweitlesung unvollständig) – beides "
        "entschieden am PDF im Blatt «Zweitlesung» der Freigabe."
    ]
    if zw.fehlend:
        z += ["", "Ohne Zweitlesung: " + ", ".join(zw.fehlend)]
    if zw.unbekannt:
        z += ["", "Hinweise (Kopf oder Zeile der Zweitlesung nicht zugeordnet):", *[f"- {u}" for u in zw.unbekannt]]
    return z


def bericht(p: PipelineErgebnis, fg: FreigabeStand | None, ergebnis: str) -> str:
    long, checks, korr = p.long, p.checks, p.korrekturen
    n_bild = len(manuelle_matrizen())
    n_mat = long.groupby(["Land", "Ebene", "Region_ID"]).ngroups
    herkunft = long["Quelle"].value_counts()
    z: list[str] = [
        "# Prüfbericht RSG 2030 – Planungsmatrizen",
        "",
        f"Version {paketversion()} · Ergebnis: **{ergebnis}**",
        "",
        "Erzeugt von `python -m rsg2030 daten`. Was jede Ebene belegt und was nicht: docs/PRUEFUNG.md.",
        "",
        "## 1. Gelesen",
        "",
        *_tabelle(
            pd.DataFrame(
                [
                    ("Matrizen", n_mat),
                    ("  davon Textseiten (ausgelesen)", n_mat - n_bild),
                    ("  davon Bildseiten (abgetippt)", n_bild),
                    ("Zellen", len(long)),
                    ("  davon mit Wert", int(long["Wert"].notna().sum())),
                    ("  aus dem PDF gelesen", int(herkunft.get("PDF", 0))),
                    ("  abgetippt (Bildseiten)", int(herkunft.get("manuell", 0))),
                    ("  korrigiert (Regel in korrekturen.csv)", int(herkunft.get("korrigiert", 0))),
                    ("  abgeleitet (Zeile fehlt im PDF dieses Landes)", int(herkunft.get("abgeleitet", 0))),
                ],
                columns=["", "Anzahl"],
            )
        ),
        "",
        "## 2. Zweitlesung",
        "",
        *_zweitlesung(p),
        "",
        "## 3. Prüfungen",
        "",
        "Jede Prüfung läuft auf den korrigierten Daten; Status «bekannt» = begründet in `bekannte_abweichungen.csv`.",
        "",
    ]
    t = checks.groupby(["Check", "Status"]).size().unstack(fill_value=0).reindex(columns=_STATUS, fill_value=0)
    t["gesamt"] = t.sum(axis=1)
    t.loc["**Summe**"] = t.sum()
    z += _tabelle(t.reset_index())
    z += ["", "## 4. Korrekturen und bekannte Abweichungen", ""]
    if len(korr):
        k = korr.groupby("Art").agg(Regeln=("Regel_Nr", "nunique"), Zellen=("Regel_Nr", "size")).reset_index()
        k.loc[len(k)] = ["**Summe**", korr["Regel_Nr"].nunique(), len(korr)]
        z += _tabelle(k)
    bekannt = checks[checks["Status"] == "bekannt"].groupby("Check").size()
    z += [
        "",
        f"Bekannte Abweichungen: {_zahl(int(bekannt.sum()))} Prüfungen, je mit Grund ("
        + ", ".join(f"{c} {_zahl(n)}" for c, n in bekannt.items())
        + ").",
    ]
    z += ["", "## 5. Freigabe (freigabe.xlsx)", ""]
    if fg is None:
        z += ["Nicht geprüft – erst Fehler und Abweichungen klären."]
    else:
        f = pd.DataFrame(
            [(n, b.gesamt, b.bestaetigt, b.offen, len(b.abweichend)) for n, b in fg.blaetter.items()],
            columns=["Blatt", "Zeilen", "bestätigt", "offen", "Lesefehler"],
        )
        z += _tabelle(f)
        if fg.nicht_aktuell:
            z += ["", f"{_zahl(fg.nicht_aktuell)} Zeilen sind noch nicht in der Mappe (`python -m rsg2030 freigabe`)."]
    return "\n".join(z) + "\n"


def schreibe_pruefbericht(p: PipelineErgebnis, fg: FreigabeStand | None, ergebnis: str, out_dir: Path) -> Path:
    ziel = out_dir / BERICHT_DATEI
    ziel.write_text(bericht(p, fg, ergebnis), encoding="utf-8")
    return ziel
