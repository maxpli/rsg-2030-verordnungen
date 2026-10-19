#!/usr/bin/env python3
"""RSG-2030: Planungsmatrizen (BL + VR) extrahieren, korrigieren, prüfen und schreiben.

Ablauf: `matrix_extract` (PDF-Koordinaten) + `manuell` (Bildseiten)
→ `checks` auf den Rohdaten (Befunde) → `korrekturen` (je Regel ein Befund) → `ableitungen` (Zeilen, die ein Land
nicht ausweist) → `checks` → Outputs:

- ``RSG_2030_Planungsmatrizen.csv``  Long-Tabelle, einzige Datenbasis (nicht in git; Prüfsumme in erwartete_ausgaben.csv)
- ``RSG_2030_Planungsmatrizen.xlsx`` `Lies mich`, `_Meta`, `_Checks`, `_Befunde_roh`, `_Korrekturen`, `_Auslesen`,
  `AT_Gesamt`,
  `BL_<Land>` und `VR_<Nr>` (je Matrix eine breite Tabelle zum Nachsehen)

Exit-Code 1, sobald ein Fehler (Parser, nicht erfasste Bildseite, Korrektur ohne Befund) oder eine unbegründete Prüfabweichung
bzw. nicht prüfbare Zelle vorliegt.
Der Lauf schreibt nur nach `daten_ergebnis/`, nie in die Eingaben im Paket: Freigabe-Mappe auf den Datenstand bringen
und Blätter für Bildseiten anlegen sind eigene Befehle (`python -m rsg2030 freigabe`, `python -m rsg2030 manuell`).
Am Ende steht `Pruefbericht.md` neben den Daten: alle Zahlen dieses Laufs (Zellen, Prüfungen, Korrekturen, Freigabe).
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from oesg_methodik.pfade import OESG_REGIONEN_CSV
from rsg2030.abgleich import gleiche_ab
from rsg2030.ableitungen import leite_ab
from rsg2030.checks import OFFEN, pruefe_alle, pruefe_vollstaendigkeit
from rsg2030.config import AUDIT_DATEI, LONG_DATEI, ausgabe_dir, manuell_xlsx, seiten_csv
from rsg2030.freigabe import FreigabeStand, zusammenfassung
from rsg2030.freigabe import stand as freigabe_stand
from rsg2030.fussnoten import lade as lade_fussnoten
from rsg2030.fussnoten import pruefe_verzeichnis, seiten
from rsg2030.korrekturen import korrigiere, pruefe_befunde
from rsg2030.manuell import lade_manuell_long, manuelle_matrizen
from rsg2030.matrix_extract import lese_quelle, prozent_strich_null
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll
from rsg2030.pruefbericht import schreibe_pruefbericht
from rsg2030.quellenpruefung import lade_dokumente, pruefe_dateien, verwendet
from rsg2030.schema import BLOCK_AEQ, LAENDER, LONG_SPALTEN, bl_long, massgeblicher_block
from rsg2030.seitenregister import Rsg2030Quelle, lade_seitenregister
from rsg2030.specs import KANONISCHE_ZEILEN
from rsg2030.zweitlesung import Vergleich, matrizen_aus, vergleiche

log = logging.getLogger(__name__)

AT_BLATT = "AT_Gesamt"
AUSLESEN_BLATT = "_Auslesen"
LIES_MICH_BLATT = "Lies mich"

# Erstes Blatt der Mappe: wer sie öffnet, sieht docs/DATEN.md nicht. Keine Zahlen eines Laufs (die stehen in _Meta).
LIES_MICH = [
    (
        "Zweck",
        "Zum Lesen und Nachsehen. Zum Weiterrechnen die CSV-Dateien RSG_2030_Planungsmatrizen.csv und "
        "RSG_2030_Versorgungsdichte.csv: Nur sie haben eine Version und eine Prüfsumme. Beschreibung: docs/DATEN.md.",
    ),
    (
        "Werte",
        "Alle Matrix-Blätter zeigen die Werte nach Korrektur und Ableitung, nicht unbedingt so, wie sie im PDF "
        "stehen. Was im PDF steht: Blatt _Korrekturen bzw. Spalte «Roh» der CSV. Parse_Status zeigt, ob in einer Zeile "
        "eine Zelle korrigiert oder abgeleitet ist.",
    ),
    (
        "Zellen",
        "0 = im PDF «-» oder 0 (in ÄAVE-, Stellen- und Anzahl-Zeilen). Leer = «n.v.», «x», leer oder "
        "schraffiert; den Unterschied zeigt nur die Spalte «Roh» der CSV.",
    ),
    (
        "Planungsgröße",
        "Burgenland, Kärnten und die Steiermark planen in SVE; ihre Blätter und AT_Gesamt zeigen die "
        "vergleichbaren ÄAVE (Block «aequivalent»).",
    ),
    (
        "BL_<Land>, VR_<Nr>",
        "Jede Matrix als Tabelle wie im PDF. Summe_Fachspalten und Gesamt_Delta (= «gesamt» minus "
        "Summe der Fachspalten): Ein kleines Delta ist meist Rundung im PDF, geprüft in _Checks (Prüfung «zeilensumme»).",
    ),
    (
        AT_BLATT,
        "Summe der neun Länder je Zeile und Fach. Keine Österreich-Zahl: Die Länder haben verschiedene "
        "IST-Jahre (Spalte Jahr), und eine leere Zelle eines Landes zählt wie 0. Gesamt_Delta ist die Summe der Deltas "
        "der Länder; diese heben sich teils auf.",
    ),
    ("_Meta", "Je Land: PDF, Seiten, Block, Zahl der Werte, davon korrigiert und abgeleitet, Status."),
    ("_Korrekturen", "Jede Zelle, die vom PDF abweicht: Wert im PDF, neuer Wert, Regel, Befund und Begründung."),
    (
        "_Checks",
        "Jede Prüfung jeder Zelle mit Soll, Differenz, Toleranz und Ergebnis (ok / bekannt / abweichung); "
        "was nicht ok ist, steht oben. Nach einer Zelle filtern, um zu sehen, wie sie geprüft wurde.",
    ),
    (
        "_Befunde_roh",
        "Was die Prüfungen am unkorrigierten PDF finden; jeder Befund ist durch eine Korrektur gelöst "
        "oder als bekannte Abweichung begründet.",
    ),
    (
        AUSLESEN_BLATT,
        "Was beim Auslesen der PDFs und beim Abgleich der Eingaben auffällt. «fehler» hält den Lauf an; "
        "«hinweis» ist nur zur Information (meist Seitenzahlen in der Fußzeile).",
    ),
]

# Schreibformat der Long-CSV (auch vom Test benutzt, der den Inhalt mit der erwarteten Prüfsumme vergleicht)
LONG_CSV_FORMAT = {"float_format": "%.10g", "lineterminator": "\n"}
_ID_SPALTEN = ["Abschnitt", "Jahr", "Planungsgröße", "Block", "Zeile_ID", "Zeile_kanonisch", "Zeile_PDF_roh"]
_END_SPALTEN = ["gesamt", "Summe_Fachspalten", "Gesamt_Delta", "Quelle", "Parse_Status"]
_NICHT_ADDITIV = {"Prozent", "Faktor"}
ISSUE_SPALTEN = ["Schwere", "Land", "Ebene", "Region_ID", "Seite", "Block", "Art", "Detail"]


@dataclass(frozen=True)
class PipelineErgebnis:
    """Ergebnis von `baue_pipeline` (Tabellen im Speicher, noch nichts geschrieben)."""

    quellen: tuple[Rsg2030Quelle, ...]
    """Seitenregister, aus dem gelesen wurde."""
    raw: pd.DataFrame
    """Long-Tabelle vor den Korrekturen."""
    long: pd.DataFrame
    """Long-Tabelle nach den Korrekturen, sortiert (= Inhalt der Long-CSV)."""
    issues: pd.DataFrame
    """Meldungen aus Auslesen, Korrektur und Vollständigkeit (`ISSUE_SPALTEN`; Schwere fehler | hinweis)."""
    befunde: pd.DataFrame
    """Prüfungen auf den Rohdaten."""
    checks: pd.DataFrame
    """Prüfungen auf den korrigierten Daten."""
    korrekturen: pd.DataFrame
    """Protokoll je geänderter Zelle (`korrekturen.LOG_SPALTEN`)."""
    voll: set[str]
    """Länder mit BL und allen VR-Matrizen (Σ VR = BL prüfbar)."""
    koepfe: pd.DataFrame
    """Je erkannte Kopfzeile einer Textseite: Seite, Block, Spaltenköpfe im PDF und zugeordnete Fachspalten."""
    zweitlesung: Vergleich
    """Lesung A (raw) gegen die Zweitlesung aus dem Seitenbild (zweitlesung.py)."""
    fussnoten: pd.DataFrame
    """Verzeichnis der Fußnoten aller Matrixseiten mit Einordnung (fussnoten.py)."""


def _issue(art: str, detail: str, *, land: str = "", ebene: str = "", region_id: str = "", seite=None) -> dict:
    """Fehlermeldung im Format der Parser-Issues (Blatt `_Auslesen`)."""
    return {
        "Schwere": "fehler",
        "Land": land,
        "Ebene": ebene,
        "Region_ID": region_id,
        "Seite": seite,
        "Block": "",
        "Art": art,
        "Detail": detail,
    }


def _mit_issues(issues: pd.DataFrame, neu: list[dict]) -> pd.DataFrame:
    return pd.concat([issues, pd.DataFrame(neu)], ignore_index=True) if neu else issues


# --- Daten aufbauen ---------------------------------------------------------------------------


def baue_long(quellen: tuple[Rsg2030Quelle, ...]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Alle Matrizen (PDF + manuell) → Long-Tabelle (unkorrigiert), Parser-Issues und erkannte Kopfzeilen."""
    datensaetze: list[dict] = []
    issues: list[dict] = []
    koepfe: list[dict] = []
    for src in quellen:
        r = lese_quelle(src)
        datensaetze += r.datensaetze
        issues += r.issues
        koepfe += r.koepfe
    for m in manuelle_matrizen():
        rec = lade_manuell_long(m)
        if not rec:
            issues.append(
                _issue(
                    "abtippen",
                    f"{m.pdf} S.{m.seite} hat keine Textebene – bitte abtippen: {manuell_xlsx().name} › Blatt "
                    f"«{m.blatt}» (fehlt das Blatt: python -m rsg2030 manuell)",
                    land=m.land,
                    ebene=m.ebene,
                    region_id=m.region_id,
                    seite=m.seite,
                )
            )
        datensaetze += rec
    long = prozent_strich_null(pd.DataFrame(datensaetze))
    return long, pd.DataFrame(issues, columns=ISSUE_SPALTEN), pd.DataFrame(koepfe)


def vr_vollstaendig(long: pd.DataFrame, quellen: tuple[Rsg2030Quelle, ...]) -> set[str]:
    """Bundesländer, für die BL und alle VR-Matrizen Werte haben (Voraussetzung Σ VR = BL)."""
    out: set[str] = set()
    for src in quellen:
        sub = long[long["Land"] == src.land]
        has_bl = (sub["Ebene"] == "BL").any()
        vrs = set(sub.loc[sub["Ebene"] == "VR", "Region_ID"])
        if has_bl and src.vr and vrs == {v.region_id for v in src.vr}:
            out.add(src.land)
    return out


def sortiere_long(long: pd.DataFrame) -> pd.DataFrame:
    order = {land: i for i, land in enumerate(LAENDER)}
    df = long.copy()
    df["_l"] = df["Land"].map(order)
    df["_e"] = (df["Ebene"] == "VR").astype(int)
    df["_r"] = df.groupby(["Land", "Ebene", "Region_ID"], sort=False).ngroup()
    df["_i"] = range(len(df))  # Reihenfolge innerhalb einer Region = Reihenfolge im PDF
    df = df.sort_values(["_l", "_e", "Region_ID", "_i"]).drop(columns=["_l", "_e", "_r", "_i"])
    return df[LONG_SPALTEN].reset_index(drop=True)


# --- Excel: eine Tabelle je Matrix, wie im PDF ---------------------------------------------------


def _matrix_tabelle(sub: pd.DataFrame, *, planungsgroesse: str) -> pd.DataFrame:
    """Long-Ausschnitt einer Matrix → breite Tabelle (eine Zeile je Abschnitt × Zeile)."""
    if sub.empty:  # Matrix fehlt (z. B. Bildseite noch nicht erfasst) – leeres Blatt statt Absturz
        return pd.DataFrame(columns=_ID_SPALTEN + _END_SPALTEN)
    keys = ["Abschnitt", "Block", "Zeile_ID"]
    faecher = [f for f in dict.fromkeys(sub["Fach"]) if f != "gesamt"]
    rows: list[dict] = []
    for (abschnitt, block, zeile), g in sub.groupby(keys, sort=False):
        vals = dict(zip(g["Fach"], g["Wert"]))
        einheit = g["Einheit"].iloc[0]
        teile = [vals[f] for f in faecher if f in vals and pd.notna(vals[f])]
        ssum = round(sum(teile), 1) if teile and einheit not in _NICHT_ADDITIV else None
        ges = vals.get("gesamt")
        rows.append(
            {
                "Abschnitt": abschnitt,
                "Jahr": g["Jahr"].dropna().iloc[0] if g["Jahr"].notna().any() else None,
                "Planungsgröße": planungsgroesse,
                "Block": block,
                "Zeile_ID": zeile,
                "Zeile_kanonisch": KANONISCHE_ZEILEN.get(zeile, zeile),
                "Zeile_PDF_roh": g["Zeile_PDF_roh"].iloc[0],
                **{f: vals.get(f) for f in faecher},
                "gesamt": ges,
                "Summe_Fachspalten": ssum,
                "Gesamt_Delta": round(ges - ssum, 1)
                if ssum is not None and ges is not None and pd.notna(ges)
                else None,
                "Quelle": f"{g['PDF'].iloc[0]} S.{g['Seite'].iloc[0]}",
                "Parse_Status": next((q for q in ("korrigiert", "abgeleitet") if (g["Quelle"] == q).any()), "ok"),
            }
        )
    df = pd.DataFrame(rows)
    return df[_ID_SPALTEN + faecher + _END_SPALTEN]


def _planungsgroesse(long: pd.DataFrame, land: str) -> str:
    bl = long[(long["Land"] == land) & (long["Ebene"] == "BL")]
    return "ÄAVE_Äquivalente" if massgeblicher_block(bl) == BLOCK_AEQ else "ÄAVE_direkt"


def _ist_jahre_text(allbl: pd.DataFrame) -> str:
    """«2022: Burgenland, … · 2023: NÖ, …» – die Österreich-Summe im IST ist kein Stand zu einem Stichtag."""
    ist = allbl[allbl["Abschnitt"] == "IST"].dropna(subset=["Jahr"]).drop_duplicates("Land")
    teile = [f"{int(j)}: {', '.join(g['Land'])}" for j, g in ist.groupby("Jahr")]
    return "Summe der Länder, IST aus verschiedenen Jahren – " + " · ".join(teile)


def _at_tabelle(bl_longs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    allbl = pd.concat(bl_longs.values())
    ist_hinweis = _ist_jahre_text(allbl)
    allbl = allbl[~allbl["Einheit"].isin(_NICHT_ADDITIV)]
    agg = (
        allbl.groupby(["Abschnitt", "Zeile_ID", "Fach"], sort=False)
        .agg(Wert=("Wert", lambda s: s.sum(min_count=1)), n=("Land", "nunique"))
        .reset_index()
    )
    agg = agg[agg["Wert"].notna()]
    rows: list[dict] = []
    for (abschnitt, zeile), g in agg.groupby(["Abschnitt", "Zeile_ID"], sort=False):
        laender = sorted(allbl.loc[(allbl["Abschnitt"] == abschnitt) & (allbl["Zeile_ID"] == zeile), "Land"].unique())
        rows.append(
            {
                "Abschnitt": abschnitt,
                "Jahr": ist_hinweis if abschnitt == "IST" else 2030,
                "Planungsgröße": "Summe 9 BL",
                "Block": "",
                "Zeile_ID": zeile,
                "Zeile_kanonisch": KANONISCHE_ZEILEN.get(zeile, zeile),
                "Zeile_PDF_roh": f"Summe {len(laender)} Bundesländer"
                + ("" if len(laender) == len(LAENDER) else f" ({', '.join(laender)})"),
                **dict(zip(g["Fach"], g["Wert"])),
                "Quelle": "(Summe der BL-Sheets)",
                "Parse_Status": "ok",
            }
        )
    df = pd.DataFrame(rows)
    faecher = [c for c in df.columns if c not in _ID_SPALTEN + _END_SPALTEN and c != "gesamt"]
    # Wie in den Blättern je Matrix; das Delta ist hier die Summe der Deltas der Länder (heben sich teils auf)
    df["Summe_Fachspalten"] = df[faecher].sum(axis=1, min_count=1).round(1)
    df["Gesamt_Delta"] = (df["gesamt"] - df["Summe_Fachspalten"]).round(1)
    for c in _END_SPALTEN:
        if c not in df:
            df[c] = None
    return df[_ID_SPALTEN + faecher + _END_SPALTEN]


def _meta(p: PipelineErgebnis) -> pd.DataFrame:
    long, issues, checks, voll = p.long, p.issues, p.checks, p.voll
    rows: list[dict] = []
    for land in LAENDER:
        sub = long[long["Land"] == land]
        bl = bl_long(long, land)
        ins = bl[(bl["Abschnitt"] == "IST") & (bl["Zeile_ID"] == "insgesamt")]
        n_fehler = int(((issues["Land"] == land) & (issues["Schwere"] == "fehler")).sum()) if len(issues) else 0
        n_abw = int(((checks["Land"] == land) & checks["Status"].isin(OFFEN)).sum())
        src = next(s for s in p.quellen if s.land == land)
        rows.append(
            {
                "Land": land,
                "Planungsgröße": _planungsgroesse(long, land),
                "IST_Jahr": int(ins["Jahr"].dropna().iloc[0]) if ins["Jahr"].notna().any() else None,
                "PDF": src.pdf.name,
                "Seite(n)": ", ".join(str(p) for p in sorted(sub["Seite"].unique())),
                "BL_Sheet_Block": massgeblicher_block(long[(long["Land"] == land) & (long["Ebene"] == "BL")]),
                "VR_Matrizen": f"{sub.loc[sub['Ebene'] == 'VR', 'Region_ID'].nunique()}/{len(src.vr)}",
                "VR_Summe_geprüft": land in voll,
                "Werte": int(sub["Wert"].notna().sum()),
                "davon_korrigiert": int((sub["Quelle"] == "korrigiert").sum()),
                "davon_abgeleitet": int((sub["Quelle"] == "abgeleitet").sum()),
                "Parser_Fehler": n_fehler,
                "Prüf_Abweichungen": n_abw,
                "Status": "ok" if not (n_fehler or n_abw) else "✗",
            }
        )
    rows.append({"Land": "Österreich", "Planungsgröße": "Summe 9 BL", "IST_Jahr": "2022/2023"})
    return pd.DataFrame(rows)


def _lesbar(blatt: Worksheet) -> None:
    """Breite Spalten und Zeilenumbruch, damit der Text ohne Klicken lesbar ist."""
    blatt.column_dimensions["A"].width = 20
    blatt.column_dimensions["B"].width = 110
    for zeile in blatt.iter_rows(min_row=2):
        for zelle in zeile:
            zelle.alignment = Alignment(wrap_text=True, vertical="top")


def schreibe_ausgaben(p: PipelineErgebnis, out_dir: Path, *, mit_long: bool = True) -> tuple[Path, Path]:
    """Audit-Mappe immer; Long-CSV (Analyse-Schnittstelle) nur mit `mit_long` (= Lauf fehlerfrei)."""
    long, issues, checks, befunde = p.long, p.issues, p.checks, p.befunde
    out_dir.mkdir(parents=True, exist_ok=True)
    long_path = out_dir / LONG_DATEI
    xlsx_path = out_dir / AUDIT_DATEI

    if mit_long:
        long.to_csv(long_path, index=False, **LONG_CSV_FORMAT)

    bl_longs = {land: bl_long(long, land) for land in LAENDER}
    status_order = {"abweichung": 0, "nicht_pruefbar": 1, "bekannt": 2, "ok": 3}
    checks_sorted = checks.sort_values("Status", key=lambda s: s.map(status_order), kind="stable")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(LIES_MICH, columns=["Thema", "Erklärung"]).to_excel(
            writer, sheet_name=LIES_MICH_BLATT, index=False
        )
        _lesbar(writer.sheets[LIES_MICH_BLATT])
        _meta(p).to_excel(writer, sheet_name="_Meta", index=False)
        checks_sorted.to_excel(writer, sheet_name="_Checks", index=False)
        befunde[befunde["Status"] != "ok"].sort_values(
            "Status", key=lambda s: s.map(status_order), kind="stable"
        ).to_excel(writer, sheet_name="_Befunde_roh", index=False)
        p.korrekturen.to_excel(writer, sheet_name="_Korrekturen", index=False)
        issues.to_excel(writer, sheet_name=AUSLESEN_BLATT, index=False)
        _at_tabelle(bl_longs).to_excel(writer, sheet_name=AT_BLATT, index=False)
        for land in LAENDER:
            _matrix_tabelle(bl_longs[land], planungsgroesse=_planungsgroesse(long, land)).to_excel(
                writer, sheet_name=f"BL_{land}"[:31], index=False
            )
        for (land, rid), sub in long[long["Ebene"] == "VR"].groupby(["Land", "Region_ID"], sort=False):
            _matrix_tabelle(sub, planungsgroesse=_planungsgroesse(long, land)).to_excel(
                writer, sheet_name=f"VR_{rid}", index=False
            )
    return long_path, xlsx_path


# --- Einstieg ---------------------------------------------------------------------------------


def baue_pipeline() -> PipelineErgebnis:
    """Extraktion → Befunde (Checks auf Rohdaten) → Korrekturen → Ableitungen → Checks (ohne Dateien zu schreiben).

    Die Befunde zeigen, wo das PDF selbst auffällig ist; jede Korrektur muss einen davon auflösen
    (`korrekturen.pruefe_befunde`). Was danach noch abweicht, steht in den Checks.
    """
    quellen = lade_seitenregister()
    raw, issues, koepfe = baue_long(quellen)
    zweit = vergleiche(raw, matrizen_aus(quellen))
    fussn = lade_fussnoten()
    issues = _mit_issues(issues, [_issue("fussnoten", msg) for msg in pruefe_verzeichnis(fussn, seiten(quellen))])
    manual_bl = {m.land for m in manuelle_matrizen() if m.ebene == "BL"}
    befunde = pruefe_alle(raw, vr_vollstaendig=vr_vollstaendig(raw, quellen), nur_bl_zeilen=manual_bl)
    unwirksam: list[str] = []
    long, korr_log = korrigiere(raw, unwirksam=unwirksam)
    issues = _mit_issues(
        issues,
        [
            _issue("regel_ohne_befund", f"{msg} → Regel prüfen oder Befund in korrekturen.csv anpassen")
            for msg in pruefe_befunde(korr_log, befunde)
        ]
        + [_issue("regel_ohne_befund", msg) for msg in unwirksam],
    )
    long = sortiere_long(leite_ab(long))
    regionen = pd.read_csv(OESG_REGIONEN_CSV)
    issues = _mit_issues(
        issues, [_issue("vollstaendigkeit", msg) for msg in pruefe_vollstaendigkeit(long, quellen, regionen)]
    )
    voll = vr_vollstaendig(long, quellen)
    checks = pruefe_alle(long, vr_vollstaendig=voll, nur_bl_zeilen=manual_bl)
    return PipelineErgebnis(
        quellen=quellen,
        raw=raw,
        long=long,
        issues=issues,
        befunde=befunde,
        checks=checks,
        korrekturen=korr_log,
        voll=voll,
        koepfe=koepfe,
        zweitlesung=zweit,
        fussnoten=fussn,
    )


def _schritt(nr: int, name: str, ok: bool | None, text: str) -> None:
    tag = {True: "ok", False: "✗ ", None: "– "}[ok]
    log.info(f" {nr} {name:<11} {tag:<3} {text}")


def audit_lauf(out_dir: Path | None = None) -> tuple[int, Path | None]:
    """Ganzer Ablauf mit einer Zeile je Schritt. Rückgabe (Exit-Code, Pfad der Audit-Mappe)."""
    out_dir = out_dir or ausgabe_dir()
    dok = lade_dokumente()
    probleme = pruefe_dateien(dok)
    if not seiten_csv().is_file():
        probleme.append(
            f"{seiten_csv().name} fehlt → erst «python -m rsg2030 seiten» (Seitenregister aus den PDFs erzeugen)"
        )
    _schritt(
        1,
        "Quellen",
        not probleme,
        f"{int(verwendet(dok).sum())} Dateien, Prüfsummen " + ("stimmen" if not probleme else "✗"),
    )
    for x in probleme:
        log.warning(f"     ✗ {x}")
    if probleme:
        log.warning("\nNICHT FREIGEGEBEN (Quellen fehlen oder wurden verändert)")
        return 1, None

    log.info("   … lese und prüfe")
    p = baue_pipeline()
    long, issues, checks, korr_log, befunde = p.long, p.issues, p.checks, p.korrekturen, p.befunde
    fehler = issues[issues["Schwere"] == "fehler"] if len(issues) else issues
    art = fehler["Art"] if len(fehler) else pd.Series(dtype=str)

    def zeige(maske) -> None:
        for _, h in fehler[maske].iterrows():
            ort = f"{h['Land']} {h['Region_ID']}".strip()
            log.warning(f"     ✗ {ort + ': ' if ort else ''}{h['Detail']}")

    # 2 Auslesen
    n_mat = long.groupby(["Land", "Region_ID"]).ngroups
    n_man = long.loc[long["Quelle"] == "manuell", ["Land", "Region_ID"]].drop_duplicates().shape[0]
    lese = art.isin(["abtippen"]) | ~art.isin(["regel_ohne_befund", "vollstaendigkeit", "fussnoten"])
    n_hinw = int((issues["Schwere"] == "hinweis").sum()) if len(issues) else 0
    _schritt(
        2,
        "Auslesen",
        not lese.any(),
        f"{n_mat} Matrizen ({n_mat - n_man} aus PDF, {n_man} manuell erfasst)"
        + (f", {n_hinw} Hinweise (Seitenzahlen/Störtext, siehe _Auslesen)" if n_hinw else ""),
    )
    zeige(lese)
    # 3 Zweitlesung: Abweichungen entscheidet ein Mensch im Blatt «Zweitlesung» der Freigabe
    zw = p.zweitlesung
    n_ges = zw.matrizen + len(zw.fehlend)
    _schritt(
        3,
        "Zweitlesung",
        True if not (zw.fehlend or len(zw.abweichungen) or len(zw.nicht_verglichen)) else None,
        f"{zw.matrizen}/{n_ges} Matrizen, {zw.verglichen} Zellen verglichen, {len(zw.abweichungen)} Abweichungen"
        + (f", {len(zw.nicht_verglichen)} nicht verglichen" if len(zw.nicht_verglichen) else "")
        + (" (Blatt «Zweitlesung» der Freigabe)" if len(zw.abweichungen) or len(zw.nicht_verglichen) else "")
        + (f" · {len(zw.unbekannt)} Hinweise (Prüfbericht)" if zw.unbekannt else "")
        + (f" · fehlt: {len(zw.fehlend)} Matrizen" if zw.fehlend else ""),
    )
    # 4 Fußnoten: jede eingeordnet; ob jede im Verzeichnis steht, prüft ein Test am PDF (tests/test_fussnoten.py)
    fussn = art == "fussnoten"
    n_einordnung = p.fussnoten["Einordnung"].value_counts()
    _schritt(
        4,
        "Fußnoten",
        not fussn.any(),
        f"{len(p.fussnoten)} im Verzeichnis: "
        + ", ".join(f"{n} {e}" for e, n in n_einordnung.items())
        + (" (Blatt «Fußnoten» der Freigabe)" if len(p.fussnoten) else ""),
    )
    zeige(fussn)
    # 5 Befunde
    n_bef = int((befunde["Status"] == "abweichung").sum())
    _schritt(
        5,
        "Befunde",
        None,
        f"{n_bef} Auffälligkeiten im PDF vor Korrekturen, "
        f"{int((befunde['Status'] == 'bekannt').sum())} bekannt (Blatt _Befunde_roh)",
    )
    # 6 Korrektur
    ohne = art == "regel_ohne_befund"
    n_regeln = korr_log["Regel_Nr"].nunique() if len(korr_log) else 0
    _schritt(
        6,
        "Korrektur",
        not ohne.any(),
        f"{n_regeln} Regeln, {len(korr_log)} Zellen" + (", jede mit Befund" if n_regeln and not ohne.any() else ""),
    )
    zeige(ohne)
    # 7 Prüfen
    n_status = checks["Status"].value_counts().to_dict()
    unvoll = art == "vollstaendigkeit"
    n_abw = sum(n_status.get(s, 0) for s in OFFEN)
    _schritt(
        7,
        "Prüfen",
        not (n_abw or unvoll.any()),
        f"{n_status.get('ok', 0)} ok, {n_status.get('bekannt', 0)} bekannt, {n_status.get('nicht_pruefbar', 0)} "
        f"nicht prüfbar, {n_status.get('abweichung', 0)} Abweichungen · "
        + ("alle 32 VR laut ÖSG" if not unvoll.any() else "VR unvollständig"),
    )
    zeige(unvoll)
    for status, wort in (("abweichung", "Abweichungen"), ("nicht_pruefbar", "nicht prüfbar ohne Grund")):
        for land, n in checks[checks["Status"] == status].groupby("Land").size().items():
            log.warning(f"     ✗ {land}: {n} {wort} (Blatt _Checks; begründen in bekannte_abweichungen.csv)")

    rc = 1 if (len(fehler) or n_abw) else 0
    # 8 Freigabe: erst wenn Auslesen und Prüfen fehlerfrei sind (sonst würde auf Fehlständen bestätigt)
    offen = 0
    fg: FreigabeStand | None = None
    if rc:
        _schritt(8, "Freigabe", None, "übersprungen – erst Fehler/Abweichungen klären")
    else:
        fg = freigabe_stand(p)  # prüft nur; Mappe nachziehen: python -m rsg2030 freigabe
        offen = fg.offen
        _schritt(
            8,
            "Freigabe",
            False if len(fg.abweichend) else (True if not (offen or fg.nicht_aktuell) else None),
            f"{zusammenfassung(fg)} bestätigt"
            + (
                f" · {fg.nicht_aktuell} Zeilen nicht in der Mappe → python -m rsg2030 freigabe"
                if fg.nicht_aktuell
                else ""
            ),
        )
        for _, r in fg.abweichend.iterrows():
            log.warning(
                f"     ✗ {r['Blatt']}: laut PDF «{r['pdf_wert']}», im Datensatz «{r['Roh']}»: {r['Wo']} · {r['Zeile']} · "
                f"{r['Fach']} (S.{r['Seite']}) – Lesefehler, Parser bzw. manuell.xlsx prüfen"
            )
        rc = 1 if len(fg.abweichend) else 0

    # 9 Ausgabe: Audit-Mappe immer (zum Nachsehen), Long-CSV nur bei fehlerfreiem Lauf
    long_path, xlsx = schreibe_ausgaben(p, out_dir, mit_long=not rc)
    _schritt(
        9,
        "Ausgabe",
        None,
        (f"{long_path.name} + " if not rc else f"{long_path.name} NICHT geschrieben · ") + f"{xlsx.name} ({out_dir})",
    )

    if rc:
        ergebnis = "NICHT FREIGEGEBEN (siehe ✗ oben)"
    elif zw.fehlend:
        ergebnis = f"NICHT FREIGEGEBEN (Zweitlesung fehlt für {len(zw.fehlend)} Matrizen)"
    elif offen:
        ergebnis = f"NICHT FREIGEGEBEN ({offen} Zeilen der Freigabe offen: freigabe.xlsx abhaken)"
    else:
        ergebnis = "FREIGEGEBEN"
    gleich = None if rc else gleiche_ab(long_path)
    bericht = schreibe_pruefbericht(p, fg, ergebnis, out_dir)
    schreibe_laufprotokoll(
        out_dir,
        "daten",
        [xlsx, bericht] if rc else [long_path, xlsx, bericht],
        {"Ergebnis": ergebnis, "Abgleich_Version": gleich},
    )
    (log.warning if ergebnis != "FREIGEGEBEN" else log.info)(f"\n{ergebnis}")
    return rc, xlsx


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 daten", description="Matrizen auslesen, korrigieren, prüfen → Long-CSV + Audit-Mappe"
    ).parse_args(argv)
    log.info(
        "RSG 2030 — Planungsmatrizen BL + VR: Quellen → Auslesen → Zweitlesung → Fußnoten → Befunde → Korrektur → Prüfen → Freigabe\n"
    )
    rc, _ = audit_lauf()
    return rc


if __name__ == "__main__":
    sys.exit(main())
