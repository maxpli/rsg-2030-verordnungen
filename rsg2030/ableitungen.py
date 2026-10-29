"""Abgeleitete Zeilen: Werte, die nicht im PDF stehen, sich aber eindeutig aus PDF-Zeilen derselben Matrix ergeben.

Anders als eine Korrektur (`korrekturen.py`) ändert eine Ableitung keinen Wert aus dem PDF: Sie ergänzt eine Zeile,
die ein Land nicht ausweist, andere Länder aber schon – damit dieselbe Größe überall unter derselben `Zeile_ID` steht.
Abgeleitete Zellen tragen `Quelle = "abgeleitet"` und die Rechnung in `Regel`; `Roh` bleibt, was gedruckt war (leer
oder «-»). Ihre Rundung ist die Unsicherheit der Rechnung aus gerundeten Werten. Steht der Wert im PDF, bleibt er
unverändert, und eine Prüfung in `checks.py` vergleicht ihn mit derselben Rechnung; abgeleitete Werte prüft sie nicht
(sie wären nur die eigene Rechnung).

Heute zwei Ableitungen:

- IST `extramural` (ohne Spitalsambulanzen): niedergelassen mit Kassenvertrag + selbständige
  Ambulatorien mit Kassenvertrag + Kassenambulatorien. Im PLAN weisen alle Länder die Zeile aus, im IST nur Wien.
  Je Fach die Summe der Teile mit Wert; leere Teilzellen (schraffiert, «n.v.», «x») zählen nicht – dieselbe Regel wie
  die Prüfung «Teile = insgesamt». Ohne einen einzigen Teil mit Wert bleibt das Fach leer.
- PLAN gesamt-% der Zeilen «- davon maximal als vertragsärztliche Planstellen in %»: das mit den Stellen gewichtete
  Mittel der Fach-% derselben Zeile (`leite_prozent_gesamt_ab`). Nur wo jedes Fach mit Stellen ein % hat – sonst wäre
  das Mittel nicht aussagefähig.
"""

from __future__ import annotations

import math

import pandas as pd

from rsg2030.korrekturen import halbe_einheit
from rsg2030.matrix_extract import PROZENT_SUFFIX
from rsg2030.schema import GESAMT, MATRIX

ABGELEITET = "abgeleitet"

# (Abschnitt, abgeleitete Zeile, Teilzeilen, Begründung – erscheint so in der Freigabe-Mappe)
ABLEITUNGEN: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "IST",
        "extramural",
        ("niedergelassen", "selbst_amb", "kassen_amb"),
        "Im PLAN weisen alle Länder «ÄAVE niedergelassene ÄrztInnen und in selbstständigen Ambulatorien (mit "
        "Kassenvertrag und kasseneigene) gesamt» aus, im IST nur Wien. Die drei Teilzeilen stehen im IST überall; ihre "
        "Summe ist dieselbe Größe (in Wien geprüft: Teile = extramural). Leere Teilzellen zählen nicht.",
    ),
)


PROZENT_GESAMT_REGEL = "gewichtetes_mittel:fachspalten"
PROZENT_GESAMT_BEGRUENDUNG = (
    "Das gesamt-% einer Zeile «- davon maximal als vertragsärztliche Planstellen in %» ist der Anteil aller Stellen der "
    "Zeile, der höchstens als Kassenpraxis besetzt werden darf: das mit den Stellen gewichtete Mittel der Fach-% "
    "(jedes gedruckte gesamt-% rechnet so, Prüfung prozent_gesamt). Die ÖSG-Vorlage sieht das Feld vor (Tabellenband "
    "S.239), viele Länder füllen es nicht aus. Abgeleitet nur, wo jedes Fach mit Stellen ein % hat."
)
"""Erscheint so in der Freigabe-Mappe (Blatt «Entscheidungen»)."""


def gewichtetes_mittel(w: pd.Series, p: pd.Series, w_roh: pd.Series, p_roh: pd.Series) -> tuple[float, float]:
    """Mit den Stellen `w` gewichtetes Mittel der % `p` und seine Unsicherheit aus den gerundeten Werten: gewichtete
    Rundung der % und Einfluss der gerundeten Stellenzahlen (|p_i − p̄|·½ULP(w_i)/Σw)."""
    W = w.sum()
    mittel = float((w * p).sum() / W)
    rundung = float((w * p_roh.map(halbe_einheit)).sum() / W) + float(
        ((p - mittel).abs() * w_roh.map(halbe_einheit)).sum() / W
    )
    return mittel, rundung


def leite_prozent_gesamt_ab(long: pd.DataFrame) -> pd.DataFrame:
    """Leeres gesamt-% einer %-Zeile = mit den Stellen gewichtetes Mittel der Fach-%, auf eine Nachkommastelle; nur wo
    jedes Fach mit Stellen > 0 ein % hat. Eine fehlende Zelle kommt ans Ende ihrer Zeile."""
    df = long.reset_index(drop=True)
    pos = pd.Series(range(len(df)), index=df.index, dtype=float)
    neu: list[dict] = []
    neu_pos: list[float] = []
    for _, m in df[df["Zeile_ID"].str.endswith(PROZENT_SUFFIX) | df["Fach"].ne(GESAMT)].groupby(MATRIX, sort=False):
        for zeile in [z for z in dict.fromkeys(m["Zeile_ID"]) if z.endswith(PROZENT_SUFFIX)]:
            pz = m[m["Zeile_ID"] == zeile]
            ges = pz[pz["Fach"] == GESAMT]
            if len(ges) and pd.notna(ges["Wert"].iloc[0]):
                continue  # gedruckt: prüft prozent_gesamt
            st = m[(m["Zeile_ID"] == zeile.removesuffix(PROZENT_SUFFIX)) & (m["Fach"] != GESAMT)].set_index("Fach")
            w = st["Wert"][st["Wert"].fillna(0) > 0]
            pf = pz[pz["Fach"] != GESAMT].set_index("Fach")
            p = pf["Wert"].reindex(w.index)
            if w.empty or p.isna().any():
                continue
            mittel, rundung = gewichtetes_mittel(w, p, st["Roh"].reindex(w.index), pf["Roh"].reindex(w.index))
            # Rundung: Unsicherheit der Rechnung + Rundung auf eine Nachkommastelle, aufgerundet auf 0,01
            werte = {
                "Wert": round(mittel, 1),
                "Rundung": math.ceil(round((rundung + 0.05) * 100, 6)) / 100,
                "Quelle": ABGELEITET,
            }
            werte["Regel"] = PROZENT_GESAMT_REGEL
            if len(ges):
                df.loc[ges.index[0], list(werte)] = list(werte.values())
            else:
                neu.append({**pz.iloc[-1].to_dict(), "Fach": GESAMT, "Roh": "", **werte})
                neu_pos.append(pos[pz.index[-1]] + 0.5)
    if not neu:
        return df
    alle = pd.concat([df, pd.DataFrame(neu)], ignore_index=True)
    reihenfolge = pd.concat([pos, pd.Series(neu_pos)], ignore_index=True)
    return alle.loc[reihenfolge.sort_values(kind="stable").index].reset_index(drop=True)


def leite_ab(long: pd.DataFrame) -> pd.DataFrame:
    """Long-Tabelle mit den abgeleiteten Zeilen (je direkt hinter der letzten Teilzeile ihrer Matrix) und den
    abgeleiteten gesamt-%."""
    return leite_prozent_gesamt_ab(_leite_zeilen_ab(long))


def _leite_zeilen_ab(long: pd.DataFrame) -> pd.DataFrame:
    df = long.reset_index(drop=True)
    pos = pd.Series(range(len(df)), index=df.index, dtype=float)
    neu: list[dict] = []
    neu_pos: list[float] = []
    for keys, g in df.groupby(MATRIX, sort=False, dropna=False):
        abschnitt = dict(zip(MATRIX, keys))["Abschnitt"]
        for ab, ziel, teile, _ in ABLEITUNGEN:
            zeilen = set(g["Zeile_ID"])
            if abschnitt != ab or ziel in zeilen or not set(teile) <= zeilen:
                continue
            t = g[g["Zeile_ID"].isin(teile)]
            # direkt vor die erste Zeile nach der letzten Teilzeile – nicht ans Matrixende, wohin per Korrektur
            # angehängte Zellen (z. B. OÖ KFO aus der Fußnote) die letzte Teilzelle sonst rücken würden
            beginn = max(pos[t.index[t["Zeile_ID"] == z]].min() for z in teile)
            danach = pos[g.index[(pos[g.index] > beginn) & ~g["Zeile_ID"].isin(teile)]]
            hinter = danach.min() - 0.9 if len(danach) else pos[t.index].max()
            faecher = list(dict.fromkeys(t["Fach"]))  # «gesamt» zuletzt, auch wenn Teilzellen angehängt wurden (OÖ KFO)
            for k, fach in enumerate([f for f in faecher if f != GESAMT] + [f for f in faecher if f == GESAMT]):
                f = t[(t["Fach"] == fach) & t["Wert"].notna()]
                if f.empty:
                    continue
                zeile = f.iloc[-1].to_dict()
                zeile.update(
                    Zeile_ID=ziel,
                    Zeile_PDF_roh="",
                    Wert=float(f["Wert"].sum()),
                    Roh="",
                    Rundung=float(f["Rundung"].sum()),
                    Quelle=ABGELEITET,
                    Regel="summe:" + "+".join(teile),
                )
                neu.append(zeile)
                neu_pos.append(hinter + 0.5 + k / 1000)
    if not neu:
        return df
    alle = pd.concat([df, pd.DataFrame(neu)], ignore_index=True)
    reihenfolge = pd.concat([pos, pd.Series(neu_pos)], ignore_index=True)
    return alle.loc[reihenfolge.sort_values(kind="stable").index].reset_index(drop=True)
