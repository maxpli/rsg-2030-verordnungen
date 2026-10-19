"""Explizite Korrekturen für Werte, die so nicht (oder widersprüchlich) im PDF stehen.

Zeilen, die ein Land nicht ausweist, die sich aber aus seinen PDF-Werten ergeben, sind keine Korrektur: siehe
`ableitungen.py` (Quelle «abgeleitet»).

Jede Regel steht mit Begründung in `eingaben/2026/korrekturen.csv`. Rohwerte aus dem PDF bleiben in der
Spalte `Roh` erhalten; korrigierte Zellen tragen `Quelle = "korrigiert"` und die Regel.

Jede Regel nennt in «Befund» den Check, der auf den ROHDATEN (vor den Korrekturen) die Auffälligkeit
zeigt, und in «Art» die Sorte: Lücke (im PDF leer) · Beschriftung (Zeile falsch benannt) ·
Widerspruch (PDF-Werte passen nicht zusammen, Entscheidung) · Folge (ergibt sich aus einer anderen
Regel) · Zellbedeutung («-»/«0» bedeuten hier «nicht angegeben», nicht «keine») · Fußnote (Wert steht nur in
einer Fußnote des PDF, nicht in der Matrix). `pruefe_befunde` verlangt, dass jede Regel mindestens eine Zelle mit
diesem Befund ändert – außer bei Art «Fußnote»: dafür gibt es keinen Check, die Begründung muss die Seite und den
Fußnotentext nennen (Befund «fussnote»).

Regeln (Spalte «Regel»):
- ``summe:a+b+…``          Summe der Zeilen a, b, … in derselben Fachspalte (überschreibt)
- ``zeilensumme``           Summe aller Fachspalten der Zeile → Spalte «gesamt» (überschreibt)
- ``zeilensumme_wenn_leer`` wie ``zeilensumme``, aber nur wenn «gesamt» im PDF leer/«x» ist
- ``umbenennen:quelle``     Zeile «quelle» ist im PDF falsch beschriftet → wird zu Zeile_ID
- ``vr_summe``              BL-Wert = Summe derselben Zelle über alle VR des Landes (überschreibt)
- ``nicht_ausgewiesen``     Werte der Zeile (bzw. der Fachspalte in «Fach») → leer (`Roh` bleibt); optionale Zeile,
                            die nicht ausgefüllt ist, oder «0», die «nicht angegeben» heißt
- ``zusatz:wert``           Fachspalte bekommt «wert» (muss leer sein) und «gesamt» der Zeile wird um «wert»
                            erhöht; in «Zeile_ID» mehrere Zeilen mit «+» möglich, fehlende Zeilen werden übergangen
- ``plus:wert``             Fachspalte + «wert» (leer zählt als 0) und «gesamt» der Zeile + «wert»; wie ``zusatz``, aber
                            auch für eine Zelle, die schon einen Wert hat; «Zeile_ID» mit «+» für mehrere Zeilen
- ``wert:wert``             leere Zelle bekommt «wert» – nur wo er sich eindeutig aus demselben Dokument ergibt (die
                            Rechnung steht in der Begründung, eine Prüfung rechnet sie nach); «gesamt» bleibt

`Rundung` je Zelle = halbe Einheit der letzten Stelle (0 für Zellen ohne Zahlwert); bei korrigierten
Werten die Summe der Rundungen der Summanden (wird von `checks.py` als Toleranz verwendet).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from rsg2030.config import korrekturen_csv
from rsg2030.matrix_extract import lese_zahl
from rsg2030.schema import MATRIX


def halbe_einheit(roh: object) -> float:
    """Halbe Einheit der letzten Stelle des Rohwerts («12,1» → 0.05, «1.288» → 0.5)."""
    if not isinstance(roh, str) or not roh:
        return 0.05
    m = re.search(r",(\d+)", roh)
    return 0.5 * 10 ** -len(m.group(1)) if m else 0.5


def rundung_je_zelle(long: pd.DataFrame) -> pd.Series:
    """Rundungstoleranz je Zelle; nur als Zahl ausgewiesene Werte sind gerundet («-» = exakt 0, «n.v.» = kein Wert).

    Einheit «Anzahl» (Ambulatorien-Standorte) ist exakt gezählt → Toleranz 0.
    """

    def zahl(r: object) -> bool:
        try:
            return isinstance(r, str) and lese_zahl(r) is not None
        except ValueError:
            return False

    tol = long["Roh"].map(lambda r: halbe_einheit(r) if zahl(r) else 0.0).where(long["Wert"].notna(), 0.0)
    return tol.where(long["Einheit"] != "Anzahl", 0.0) if "Einheit" in long else tol


LOG_SPALTEN = ["Regel_Nr", *MATRIX, "Zeile_ID", "Fach", "Wert_PDF", "Wert_neu", "Regel", "Art", "Befund", "Begruendung"]
REGEL_SPALTEN = [
    "Land",
    "Ebene",
    "Region_ID",
    "Block",
    "Abschnitt",
    "Zeile_ID",
    "Fach",
    "Regel",
    "Art",
    "Befund",
    "Begruendung",
]


def lade_regeln(path: Path | None = None) -> pd.DataFrame:
    """Korrekturregeln; fehlt die Datei (neuer Verordnungsstand), gibt es noch keine."""
    path = path or korrekturen_csv()
    if not path.is_file():
        return pd.DataFrame(columns=REGEL_SPALTEN, dtype=str)
    return pd.read_csv(path, dtype=str)


def _auswahl(df: pd.DataFrame, rule: pd.Series) -> pd.Series:
    sel = pd.Series(True, index=df.index)
    for c in MATRIX:
        if rule[c] != "*":
            sel &= df[c].astype(str) == rule[c]
    return sel


# Jede Regelart ist eine Funktion (out, in_matrix, reg, r, nr, log) → out: `out` ist die Long-Tabelle, `in_matrix`
# die Maske der Matrix `reg`, `r` die Regel (Zeile aus korrekturen.csv) mit laufender Nummer `nr`. Jede geänderte
# Zelle kommt mit `_protokollzeile` in `log`. Neue Regelart: Funktion schreiben, in `REGELN` eintragen, im Modulkopf beschreiben.
Regelfunktion = Callable[[pd.DataFrame, pd.Series, pd.Series, pd.Series, int, list[dict]], pd.DataFrame]


def _umbenennen(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    regel = r["Regel"]
    quelle = regel.removeprefix("umbenennen:")
    hit = out.index[in_matrix & (out["Zeile_ID"] == quelle)]
    if r["Fach"] != "*":
        hit = hit[out.loc[hit, "Fach"] == r["Fach"]]
    for i in hit:
        log.append(_protokollzeile(reg, r, out.loc[i, "Fach"], None, out.loc[i, "Wert"], nr))
    out.loc[hit, ["Zeile_ID", "Quelle", "Regel"]] = [r["Zeile_ID"], "korrigiert", regel]
    return out


def _nicht_ausgewiesen(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    hit = out.index[in_matrix & (out["Zeile_ID"] == r["Zeile_ID"]) & out["Wert"].notna()]
    if r["Fach"] != "*":
        hit = hit[out.loc[hit, "Fach"] == r["Fach"]]
    for i in hit:
        log.append(_protokollzeile(reg, r, out.loc[i, "Fach"], out.loc[i, "Wert"], None, nr))
    out.loc[hit, ["Wert", "Quelle", "Regel", "Rundung"]] = [float("nan"), "korrigiert", r["Regel"], 0.0]
    return out


def _zusatz(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    regel = r["Regel"]
    wert = float(regel.removeprefix("zusatz:"))
    rund = halbe_einheit(regel.removeprefix("zusatz:").replace(".", ","))
    for zeile in r["Zeile_ID"].split("+"):
        z = out[in_matrix & (out["Zeile_ID"] == zeile)]
        if z.empty:
            continue
        alt = z[z["Fach"] == r["Fach"]]
        if len(alt) and pd.notna(alt["Wert"].iloc[0]):
            raise ValueError(f"Regel {nr}: {zeile} {r['Fach']} hat schon einen Wert ({alt['Wert'].iloc[0]})")
        base = z.iloc[0].to_dict()
        base.update(Fach=r["Fach"], Wert=wert, Roh="", Quelle="korrigiert", Regel=regel, Rundung=rund)
        out = out.drop(alt.index)
        out = pd.concat([out, pd.DataFrame([base])], ignore_index=True)
        log.append(_protokollzeile(reg, {**r, "Zeile_ID": zeile}, r["Fach"], None, wert, nr))
        in_matrix = (out[MATRIX] == reg[MATRIX].values).all(axis=1)
        ges = out.index[in_matrix & (out["Zeile_ID"] == zeile) & (out["Fach"] == "gesamt")]
        for i in ges:
            neu = float(out.at[i, "Wert"]) + wert
            log.append(_protokollzeile(reg, {**r, "Zeile_ID": zeile}, "gesamt", out.at[i, "Wert"], neu, nr))
            out.loc[i, ["Wert", "Quelle", "Regel", "Rundung"]] = [
                neu,
                "korrigiert",
                regel,
                float(out.at[i, "Rundung"]) + rund,
            ]
    return out


def _summe_je_fach(teile: pd.DataFrame, r: pd.Series) -> dict[str, tuple[float, float]]:
    """Fach → (Summe der Werte, Summe der Rundungen); alle Fächer bei «*», sonst nur das der Regel."""
    agg = teile.groupby("Fach").agg(Wert=("Wert", lambda s: s.sum(min_count=1)), Rundung=("Rundung", "sum"))
    faecher = list(agg.index) if r["Fach"] == "*" else [r["Fach"]]
    return {f: (agg.at[f, "Wert"], agg.at[f, "Rundung"]) for f in faecher if f in agg.index}


def _ziele_setzen(
    out: pd.DataFrame,
    block: pd.DataFrame,
    reg: pd.Series,
    r: pd.Series,
    nr: int,
    log: list[dict],
    ziele: dict[str, tuple[float, float]],
    *,
    nur_wenn_leer: bool = False,
) -> pd.DataFrame:
    """Gemeinsamer Teil der rechnenden Regeln: Zeile `r["Zeile_ID"]` bekommt je Fach den berechneten Wert.

    Bestätigt die Rechnung den PDF-Wert, bleibt die Zelle «PDF»; fehlt die Zelle, wird sie angelegt."""
    regel = r["Regel"]
    vorlage = block[block["Zeile_ID"] == r["Zeile_ID"]]
    for fach, (wert, rundung) in ziele.items():
        if pd.isna(wert):
            continue
        hit = vorlage[vorlage["Fach"] == fach]
        alt = hit["Wert"].iloc[0] if len(hit) else None
        if nur_wenn_leer and alt is not None and pd.notna(alt):
            continue
        if alt is not None and pd.notna(alt) and abs(float(alt) - float(wert)) < 1e-9:
            continue  # Regel bestätigt den PDF-Wert – Zelle bleibt «PDF»
        if len(hit):
            out.loc[hit.index, ["Wert", "Quelle", "Regel", "Rundung"]] = [
                float(wert),
                "korrigiert",
                regel,
                float(rundung),
            ]
        else:
            base = (vorlage.iloc[0] if len(vorlage) else block.iloc[0]).to_dict()
            if not len(vorlage):
                base["Zeile_PDF_roh"] = ""
            base.update(
                Zeile_ID=r["Zeile_ID"],
                Fach=fach,
                Wert=float(wert),
                Roh="",
                Quelle="korrigiert",
                Regel=regel,
                Rundung=float(rundung),
            )
            out = pd.concat([out, pd.DataFrame([base])], ignore_index=True)
        log.append(_protokollzeile(reg, r, fach, alt, wert, nr))
    return out


def _summe(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    block = out[in_matrix]
    teile = block[block["Zeile_ID"].isin(r["Regel"].removeprefix("summe:").split("+"))]
    return _ziele_setzen(out, block, reg, r, nr, log, _summe_je_fach(teile, r))


def _vr_summe(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    vr = out[
        (out["Land"] == reg["Land"])
        & (out["Ebene"] == "VR")
        & (out["Block"] == reg["Block"])
        & (out["Abschnitt"] == reg["Abschnitt"])
        & (out["Zeile_ID"] == r["Zeile_ID"])
    ]
    return _ziele_setzen(out, out[in_matrix], reg, r, nr, log, _summe_je_fach(vr, r))


def _zeilensumme(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    block = out[in_matrix]
    row = block[(block["Zeile_ID"] == r["Zeile_ID"]) & (block["Fach"] != "gesamt")]
    ziele = {"gesamt": (row["Wert"].sum(min_count=1), row["Rundung"].sum())}
    return _ziele_setzen(out, block, reg, r, nr, log, ziele, nur_wenn_leer=r["Regel"] == "zeilensumme_wenn_leer")


def _plus(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    regel = r["Regel"]
    argument = regel.removeprefix("plus:")
    wert, rund = float(argument), halbe_einheit(argument.replace(".", ","))
    for zeile in r["Zeile_ID"].split("+"):
        for fach in (r["Fach"], "gesamt"):
            z = out[in_matrix & (out["Zeile_ID"] == zeile)]
            if z.empty:
                continue
            hit = z[z["Fach"] == fach]
            if hit.empty:
                if fach == "gesamt":
                    continue
                neu = {**z.iloc[0].to_dict(), "Fach": fach, "Wert": wert, "Roh": "", "Quelle": "korrigiert"}
                neu.update(Regel=regel, Rundung=rund)
                out = pd.concat([out, pd.DataFrame([neu])], ignore_index=True)
                in_matrix = (out[MATRIX] == reg[MATRIX].values).all(axis=1)
                log.append(_protokollzeile(reg, {**r, "Zeile_ID": zeile}, fach, None, wert, nr))
                continue
            i = hit.index[0]
            alt = out.at[i, "Wert"]
            neu_wert = (0.0 if pd.isna(alt) else float(alt)) + wert
            log.append(_protokollzeile(reg, {**r, "Zeile_ID": zeile}, fach, alt, neu_wert, nr))
            out.loc[i, ["Wert", "Quelle", "Regel", "Rundung"]] = [
                neu_wert,
                "korrigiert",
                regel,
                float(out.at[i, "Rundung"]) + rund,
            ]
    return out


def _wert(
    out: pd.DataFrame, in_matrix: pd.Series, reg: pd.Series, r: pd.Series, nr: int, log: list[dict]
) -> pd.DataFrame:
    regel = r["Regel"]
    argument = regel.removeprefix("wert:")
    wert, rund = float(argument), halbe_einheit(argument.replace(".", ","))
    zeile = out[in_matrix & (out["Zeile_ID"] == r["Zeile_ID"])]
    if zeile.empty:
        return out
    alt = zeile[zeile["Fach"] == r["Fach"]]
    if len(alt) and pd.notna(alt["Wert"].iloc[0]):
        raise ValueError(f"Regel {nr}: {r['Zeile_ID']} {r['Fach']} hat schon einen Wert ({alt['Wert'].iloc[0]})")
    log.append(_protokollzeile(reg, r, r["Fach"], None, wert, nr))
    if len(alt):
        out.loc[alt.index, ["Wert", "Quelle", "Regel", "Rundung"]] = [wert, "korrigiert", regel, rund]
        return out
    # fehlende Zelle an ihrer Stelle in der Zeile anlegen (Reihenfolge der Fachspalten der Matrix)
    rang = {f: i for i, f in enumerate(dict.fromkeys(out.loc[in_matrix, "Fach"]))}
    ziel = rang.get(r["Fach"], len(rang))
    danach = zeile[zeile["Fach"].map(rang).fillna(len(rang)) > ziel].index
    neu = {**zeile.iloc[0].to_dict(), "Fach": r["Fach"], "Wert": wert, "Roh": "", "Quelle": "korrigiert"}
    neu.update(Regel=regel, Rundung=rund)
    pos = out.index.get_loc(danach[0]) if len(danach) else out.index.get_loc(zeile.index[-1]) + 1
    return pd.concat([out.iloc[:pos], pd.DataFrame([neu]), out.iloc[pos:]], ignore_index=True)


REGELN: dict[str, Regelfunktion] = {
    "umbenennen": _umbenennen,
    "nicht_ausgewiesen": _nicht_ausgewiesen,
    "zusatz": _zusatz,
    "wert": _wert,
    "plus": _plus,
    "summe": _summe,
    "vr_summe": _vr_summe,
    "zeilensumme": _zeilensumme,
    "zeilensumme_wenn_leer": _zeilensumme,
}
_MIT_ARGUMENT = {"umbenennen", "zusatz", "summe", "wert", "plus"}
"""Regelarten der Form «art:argument»; die übrigen stehen ohne Argument."""


def regelfunktion(regel: str) -> Regelfunktion:
    """Funktion zur Regel aus Spalte «Regel»; unbekannte oder falsch geschriebene Regel → ValueError."""
    art, doppelpunkt, argument = regel.partition(":")
    if art not in REGELN or (art in _MIT_ARGUMENT) != bool(doppelpunkt and argument):
        raise ValueError(f"Unbekannte Regel: {regel}")
    return REGELN[art]


def korrigiere(
    long: pd.DataFrame, rules: pd.DataFrame | None = None, *, unwirksam: list[str] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Wendet alle Regeln an. Rückgabe: (korrigierte Long-Tabelle, Protokoll je geänderter Zelle).

    Eine unbekannte Regel bricht sofort ab (ValueError). Eine Regel, die keine Zelle ändert, ist ein Fehler
    (veraltet, oder die Matrix fehlt): ValueError, bzw. Meldung in `unwirksam`, wenn eine Liste übergeben wird
    (Pipeline sammelt alle Fehler).
    """
    rules = lade_regeln() if rules is None else rules
    funktionen = [regelfunktion(regel) for regel in rules["Regel"]]  # Schreibfehler vor dem ersten Ändern melden
    out = long.copy()
    out["Quelle"] = out["Quelle"].fillna("PDF") if "Quelle" in out else "PDF"  # «manuell» bleibt
    out["Regel"] = ""
    out["Rundung"] = rundung_je_zelle(out)
    log: list[dict] = []

    for nr, ((_, r), funktion) in enumerate(zip(rules.iterrows(), funktionen, strict=True), start=1):
        n_before = len(log)
        regions = out.loc[_auswahl(out, r), MATRIX].drop_duplicates()
        for _, reg in regions.iterrows():
            in_matrix = (out[MATRIX] == reg[MATRIX].values).all(axis=1)
            out = funktion(out, in_matrix, reg, r, nr, log)
        if len(log) == n_before:
            msg = (
                f"Regel {nr} ({r['Land']} {r['Ebene']} {r['Block']} {r['Abschnitt']} {r['Zeile_ID']} {r['Fach']} "
                f"{r['Regel']}) ändert nichts – veraltet, oder die Matrix fehlt"
            )
            if unwirksam is None:
                raise ValueError(msg)
            unwirksam.append(msg)
    return out, pd.DataFrame(log, columns=LOG_SPALTEN)


def _protokollzeile(reg: pd.Series, r: pd.Series, fach: str, alt, neu, nr: int) -> dict:
    return {
        "Regel_Nr": nr,
        **{k: reg[k] for k in MATRIX},
        "Zeile_ID": r["Zeile_ID"],
        "Fach": fach,
        "Wert_PDF": None if alt is None or pd.isna(alt) else float(alt),
        "Wert_neu": None if neu is None or pd.isna(neu) else float(neu),
        "Regel": r["Regel"],
        "Art": r.get("Art", ""),
        "Befund": r.get("Befund", ""),
        "Begruendung": r["Begruendung"],
    }


BL_GEGEN_VR = ("vr_summe_gleich_bl", "prozent_gewichtet")
"""Prüfungen, die den BL-Wert aus den VR nachrechnen: Ihr Befund steht auf BL-Ebene, die Ursache kann in einer VR liegen."""


def pruefe_befunde(log: pd.DataFrame, befunde: pd.DataFrame) -> list[str]:
    """Regeln, die keine Zelle mit dem genannten Rohbefund ändern (leere Liste = alle belegt).

    Zelle ↔ Befund: gleicher Check, Land, Block, Abschnitt, Zeile, Fach und Region – bei Prüfungen, die BL gegen
    die VR rechnen (`BL_GEGEN_VR`), genügt der Befund auf BL-Ebene (er gilt für alle VR des Landes). Eine Regel der Art
    «Folge» darf sich auf denselben Befund in einer anderen Matrix desselben Landes stützen (die Regel, aus der sie
    folgt – z. B. BL = Summe der korrigierten Regionen).
    """
    offen = befunde[befunde["Status"] != "ok"]
    keys = ["Check", "Land", "Block", "Abschnitt", "Zeile_ID", "Fach"]
    idx = set(map(tuple, offen[keys + ["Region_ID"]].astype(str).values))
    vr_idx = set(map(tuple, offen.loc[offen["Check"].isin(BL_GEGEN_VR), keys].astype(str).values))
    land_idx = set(map(tuple, offen[keys].astype(str).values))
    fehlt: list[str] = []
    for nr, g in log.groupby("Regel_Nr"):
        r = g.iloc[0]
        if r.get("Art", "") == "Fußnote":
            if (
                r["Befund"] != "fussnote"
                or not re.search(r"S\.\s*\d", r["Begruendung"])
                or "Fußnote" not in r["Begruendung"]
            ):
                fehlt.append(
                    f"Regel {nr} ({r['Land']} {r['Zeile_ID']}): Art «Fußnote» braucht Befund «fussnote» "
                    "und eine Begründung mit Seite («S.») und Fußnotentext"
                )
            continue
        belegt = any(
            (r["Befund"], z["Land"], z["Block"], z["Abschnitt"], z["Zeile_ID"], z["Fach"], str(z["Region_ID"])) in idx
            or (r["Befund"], z["Land"], z["Block"], z["Abschnitt"], z["Zeile_ID"], z["Fach"]) in vr_idx
            or (
                r.get("Art", "") == "Folge"
                and (r["Befund"], z["Land"], z["Block"], z["Abschnitt"], z["Zeile_ID"], z["Fach"]) in land_idx
            )
            for _, z in g.astype(str).iterrows()
        )
        if not belegt:
            fehlt.append(f"Regel {nr} ({r['Land']} {r['Zeile_ID']} {r['Regel']}): kein Rohbefund «{r['Befund']}»")
    return fehlt
