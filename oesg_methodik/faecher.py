"""Fach-Zuschnitt: Spalten der RSG-Planungsmatrix → Zeilen der ÖSG-Planungsrichtwerte (docs/METHODIK.md, R4 und R5).

Die Richtwerttabelle (ÖSG 2023 Textband S.39) schneidet manche Fächer anders zu als die Spalten der RSG-Planungsmatrix
(Vorlage: ÖSG 2023 Tabellenband, Anhang 9, S.239). Für den Vergleich mit einem Richtwert werden die Spalten so
zusammengezählt, wie der Richtwert sie enthält – `ZUSCHNITT`, je Eintrag mit Beleg. Die Spalten heißen wie in der
Vorlage, ohne Fußnotenzeichen.

Der Zuschnitt gilt **einheitenneutral**: Er sagt, welche Matrixspalten ein Fach bilden, nicht was darin steht. Dieselbe
Funktion schneidet deshalb ÄAVE und Stellen zu (`summe_im_zuschnitt`); die einzige Ausnahme regelt `teile` selbst,
indem es die ZAE nur in `ZAE_ZEILEN` mitnimmt. So bedeutet ein Fach in beiden Tabellen dasselbe.
"""

from __future__ import annotations

import math

import pandas as pd

ZAE = "ZAE"
"""ÄAVE der Zentralen Aufnahme- und Erstversorgungseinheiten, soweit getrennt von AM ausgewiesen. In der
RSG-Planungsmatrix stehen sie in SON/IDB, Zeile spitalsambulant: Vorlage (Tabellenband S.239), Fußnote (5) «spitalsambulant = ZAE».
Der Datensatz liefert sie unter diesem Namen (R5)."""
ZAE_QUELLE = ("spitalsambulant", "SON/IDB")
"""Zeile und Spalte der RSG-Planungsmatrix, in der die ZAE stehen (Vorlage (Tabellenband S.239), Fußnote (5))."""
ZAE_ZEILEN = ("spitalsambulant", "insgesamt")
"""ÄAVE-Zeilen, in denen die ZAE stecken: ZAE sind spitalsambulant (Fußnote (5)), «insgesamt» enthält spitalsambulant.
In «extramural» und «pve» gibt es keine ZAE; dort ist AM nur die Spalte AM (R5)."""

ZUSCHNITT: dict[str, tuple[str, ...]] = {
    # ÖSG-Zeile: (Hauptspalte, weitere Spalten). Reihenfolge wie in der Richtwerttabelle, Textband S.39.
    # Textband S.39, Legende **: «Im Bereich der AM inkl. ZAE (in RSG-PM: SON/IDB) und EVA in der Funktion von
    # Akutordinationen». EVA steht in AM («davon in Akut-Ordinationen EVA», Vorlage Fußnote (4)).
    "AM": ("AM", ZAE),
    "KIJU": ("KIJU",),
    "KJP": ("KJP",),
    # Vorlage (Tabellenband S.239), Fußnote (2) an KJC und PCH: «zugeordnet zu CH»; Tabellenband S.232: «ÄAVE für PCH sind unter der
    # CH subsummiert». Die Richtwerttabelle hat für KJC und PCH keinen Richtwert («*»).
    "CH": ("CH", "KJC", "PCH"),
    # Textband S.39: «Innere Medizin (IM)» mit Unterzeile «- davon Pulmologie (PUL)»; in der Matrix getrennte Spalten.
    "IM": ("IM", "PUL"),
    "PUL": ("PUL",),
    "GGH": ("GGH",),
    "NEU": ("NEU",),
    "PSY": ("PSY",),
    "DER": ("DER",),
    "AU": ("AU",),
    "HNO": ("HNO",),
    "URO": ("URO",),
    # Textband S.39, Fußnote 2: «Summe aus UC, OR und den im spitalsambulanten Bereich dem Fachbereich ORTR zugeordneten
    # ÄAVE» – in der RSG-2030-Matrix ist das die Spalte ORTR.
    "ORTR": ("ORTR",),
    "MKG": ("MKG",),
    # Textband S.39: «Zahn-, Mund- und Kieferheilkunde (ZMK)» mit Unterzeile «- davon mit kieferorthopädischem
    # Schwerpunkt». Wo KFO eine eigene Spalte hat, gehört sie zu ZMK dazu; sonst ist sie in ZMK enthalten.
    "ZMK": ("ZMK", "KFO"),
    "KFO": ("KFO",),
}

OESG_ANALYSEKERN: tuple[str, ...] = tuple(ZUSCHNITT)
"""Fächer mit Richtwert, für die die Kennzahlen gerechnet werden (Namen der Richtwert-Zeilen)."""

MATRIXSPALTEN: frozenset[str] = frozenset(s for teile in ZUSCHNITT.values() for s in teile if s != ZAE)
"""Spalten der Zeile «insgesamt», aus denen die Kennzahlen entstehen (ZAE kommt aus SON/IDB spitalsambulant)."""


def _wert(row: pd.Series, spalte: str) -> float | None:
    if spalte not in row.index:
        return None
    v = row[spalte]
    return None if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v) else float(v)


def teile(fach: str, zeile: str = "insgesamt") -> tuple[str, ...]:
    """Spalten, aus denen `fach` in der Zeile `zeile` entsteht: `ZUSCHNITT`, ZAE nur in `ZAE_ZEILEN`.

    Gilt für jede Einheit, nicht nur für ÄAVE: Der Zuschnitt sagt, welche Matrixspalten ein Fach bilden, unabhängig
    davon, was in den Spalten steht. Für eine Stellen-Zeile (`planstellen_…`, `slst_…`) fällt die ZAE von selbst weg,
    weil die Zeile nicht in `ZAE_ZEILEN` steht – und das ist richtig: Sachleistungsstellen bilden den extramuralen
    Bereich ab (Tabellenband S.232), ZAE sind spitalsambulant (Vorlage (Tabellenband S.239), Fußnote (5))."""
    return tuple(s for s in ZUSCHNITT[fach] if s != ZAE or zeile in ZAE_ZEILEN)


def summe_im_zuschnitt(row: pd.Series, fach: str, zeile: str = "insgesamt") -> float | None:
    """Wert eines Fachs im ÖSG-Zuschnitt aus einer Matrixzeile (Spalten = Fachspalten, dazu `ZAE`): Summe der Spalten
    laut `teile`. Einheitenneutral – ÄAVE, Stellen oder anderes, je nachdem, was in `row` steht.

    Fehlt die Hauptspalte, gibt es keinen Wert (z. B. KFO, wo es keine eigene Spalte hat) – außer ein anderer
    Teil ist > 0: Burgenland VR 11/12 drucken AM spitalsambulant leer, die ZAE aber in SON/IDB (AM = 0 + ZAE)."""
    haupt, *weitere = teile(fach, zeile)
    h = _wert(row, haupt)
    if h is None and not any((_wert(row, s) or 0) > 0 for s in weitere):
        return None
    h = h or 0.0
    # gerundet: die Teile haben höchstens drei Nachkommastellen, ohne Runden blieben Gleitkomma-Reste (187.89999999999998)
    return round(h + sum(w for s in weitere if (w := _wert(row, s)) is not None), 6)


def zuschnitt(row: pd.Series, fach: str, zeile: str = "insgesamt") -> str:
    """Wie der Wert entstanden ist, z. B. «AM + ZAE», «ZMK (KFO nicht getrennt ausgewiesen)». Genannt werden die Spalten
    mit einem Wert > 0 (die Hauptspalte immer) und die, die in der Matrix fehlen oder leer sind. ZAE mit 0 bzw. «-»
    zählen ebenso als nicht getrennt ausgewiesen: Ob es keine gibt oder sie in einer Fachspalte stecken (Wien: «aus
    den verschiedenen Fächern (AM, IM)»), sagt die Matrix nicht (docs/METHODIK.md, R5)."""
    haupt, *weitere = teile(fach, zeile)
    mit = [haupt] + [s for s in weitere if (_wert(row, s) or 0) > 0]
    ohne = [s for s in weitere if _wert(row, s) is None or (s == ZAE and _wert(row, s) == 0)]
    return " + ".join(mit) + (f" ({', '.join(ohne)} nicht getrennt ausgewiesen)" if ohne else "")
