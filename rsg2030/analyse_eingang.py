"""RSG-2030-Long-CSV → Tabellen für die Versorgungsdichte und Analysen (die Schnittstelle nach außen).

Die Analyse liest nur `RSG_2030_Planungsmatrizen.csv`, nicht die Excel-Mappe. Je Bundesland gibt
`bl_tabellen` die BL-Matrix in breiter Form (eine Zeile je Abschnitt × Zeile, Spalten = Fächer), dazu die Spalte
`ZAE` (SON/IDB spitalsambulant, in den Zeilen spitalsambulant und insgesamt), damit `oesg_methodik.faecher.summe_im_zuschnitt`
jede ÄAVE-Zeile nach ÖSG zuschneidet (AM = AM + ZAE nur, wo ZAE hingehören; docs/METHODIK.md R4, R5, R10).

Maßgeblicher Block (SVE-Planung → ÄAVE-Äquivalente): `schema.bl_long`, dieselbe Regel wie in der
Audit-Mappe.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oesg_methodik import BUNDESLAENDER
from oesg_methodik.eingang import PVE_FAECHER, SACHLEISTUNG, ZEILEN, pruefe
from oesg_methodik.faecher import OESG_ANALYSEKERN, ZAE, ZAE_QUELLE, ZAE_ZEILEN, summe_im_zuschnitt, teile, zuschnitt
from oesg_methodik.stellen_eingang import OHNE_PROZENT
from oesg_methodik.stellen_eingang import ZEILEN as STELLEN_ZEILEN
from oesg_methodik.stellen_eingang import pruefe as stellen_pruefe
from rsg2030.config import LONG_DATEI, ausgabe_dir
from rsg2030.matrix_extract import PROZENT_SUFFIX
from rsg2030.schema import BLOCK_AEQ, bl_long, matrix_long

PLAN_JAHR = 2030
ABSCHNITTE = ("IST", "PLAN")
_KEYS = ["Abschnitt", "Zeile_ID"]


def lade_matrix_long(path: Path | None = None) -> pd.DataFrame:
    path = path or (ausgabe_dir() / LONG_DATEI)
    if not path.is_file():
        raise FileNotFoundError(f"Long-CSV fehlt: {path} → python -m rsg2030 daten")
    return pd.read_csv(path, dtype={"Region_ID": str})


def _breit(sub: pd.DataFrame) -> pd.DataFrame:
    """Long-Ausschnitt einer Matrix → breite Tabelle (Spalten Abschnitt, Jahr, Zeile_ID, <Fächer>, ZAE).

    `ZAE` = SON/IDB der Zeile spitalsambulant desselben Abschnitts, in den Zeilen spitalsambulant und insgesamt
    (Vorlage Fußnote (5) «spitalsambulant = ZAE»). So schneidet `oesg_methodik.faecher.summe_im_zuschnitt` AM für jede dieser
    Zeilen nach ÖSG zu (AM + ZAE, METHODIK R5); die Fachspalten bleiben, wie gedruckt."""
    anders = sub[sub["Zeile_ID"].isin(ZEILEN) & (sub["Einheit"] != "ÄAVE")]
    if len(anders):
        # SVE statt ÄAVE hieße: falscher Block (schema.bl_long), die Dichte wäre nicht vergleichbar (METHODIK R6)
        a = anders.iloc[0]
        raise ValueError(f"{a['Land']} {a['Region_ID']} {a['Abschnitt']} {a['Zeile_ID']}: Einheit {a['Einheit']}")
    g = sub.groupby([*_KEYS, "Fach"], sort=False)["Wert"].first()  # je Zelle genau ein Wert
    wide = g.unstack("Fach").reindex(sub[_KEYS].drop_duplicates().itertuples(index=False, name=None))
    wide.index.names = _KEYS
    wide[ZAE] = float("nan")
    zeile, spalte = ZAE_QUELLE
    if spalte in wide.columns:
        for abschnitt in wide.index.get_level_values("Abschnitt").unique():
            if (abschnitt, zeile) in wide.index:
                for z in ZAE_ZEILEN:
                    if (abschnitt, z) in wide.index:
                        wide.loc[(abschnitt, z), ZAE] = wide.loc[(abschnitt, zeile), spalte]
    jahr = sub.groupby(_KEYS, sort=False)["Jahr"].first()
    return wide.join(jahr).reset_index()


def bl_tabellen(long: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Land → breite BL-Matrix (Spalten Abschnitt, Jahr, Zeile_ID, <Fächer>)."""
    return {land: _breit(bl_long(long, land)) for land in BUNDESLAENDER}


def vr_tabellen(long: pd.DataFrame) -> dict[tuple[str, str], pd.DataFrame]:
    """(Land, VR) → breite VR-Matrix, gleiche Block-Regel wie beim BL (SVE-Länder: ÄAVE-Äquivalente)."""
    out: dict[tuple[str, str], pd.DataFrame] = {}
    vr = long[long["Ebene"] == "VR"]
    for (land, rid), _ in vr.groupby(["Land", "Region_ID"], sort=False):
        sub = matrix_long(long, land, "VR", rid)
        bl_aeq = (bl_long(long, land)["Block"] == BLOCK_AEQ).any()
        if bl_aeq != (sub["Block"] == BLOCK_AEQ).any():
            raise ValueError(
                f"{land} VR {rid}: Block-Regel anders als beim BL (Äquivalente-Block fehlt bzw. zusätzlich)"
            )
        out[(land, str(rid))] = _breit(sub)
    return out


def _zuschnitt_text(block: pd.Series, fach: str, zeile: str, nur_regel: frozenset[str]) -> str:
    """Wie der Wert entstanden ist (`faecher.zuschnitt`), dazu der Vermerk für Spalten, die nicht in der Tabelle des
    PDF stehen und nur per Korrekturregel dazukommen (OÖ: KFO aus der Fußnote zu ZMK).

    Beide Eingangstabellen bauen diesen Text mit **derselben** Funktion: Nur so ist der `Zuschnitt` einer Stellen-Zeile
    zeichengleich mit dem der zugehörigen ÄAVE-Zeile, und nur dann bedeutet ein Fach in beiden Tabellen dasselbe
    (Test: `tests/test_stellen.py`)."""
    text = zuschnitt(block, fach, zeile)
    vermerk = [s for s in teile(fach, zeile) if s in nur_regel and f" {s}" in f" {text}"]
    return text + "".join(
        " (nicht in der Tabelle, per Korrekturregel)"
        if s == fach
        else f" ({s} nicht in der Tabelle, per Korrekturregel)"
        for s in vermerk
    )


def _aave_zeilen(df: pd.DataFrame, ist_jahr: int, nur_regel: frozenset[str] = frozenset(), **schluessel) -> list[dict]:
    """ÄAVE je ÄAVE-Zeile (`eingang.ZEILEN`, ohne Wahlärzt:innen) und Richtwert-Fach aus einer breiten Matrix,
    zugeschnitten nach `oesg_methodik.faecher.teile` (AM mit der Spalte `ZAE` nur in `ZAE_ZEILEN`, siehe `_breit`);
    pve nur in `PVE_FAECHER`. `nur_regel`: Spalten, die in der Tabelle des PDF fehlen und nur per Korrekturregel
    dazukommen (OÖ: KFO aus der Fußnote) – steht im Zuschnitt dabei."""
    rows: list[dict] = []
    df = df[df["Zeile_ID"].isin(ZEILEN) & df["Abschnitt"].isin(ABSCHNITTE)]
    # Reihenfolge: IST vor PLAN, darin die Zeilen wie in der Vorlage
    ordnung = {**{a: i for i, a in enumerate(ABSCHNITTE)}, **{z: i for i, z in enumerate(ZEILEN)}}
    df = df.sort_values(["Abschnitt", "Zeile_ID"], key=lambda s: s.map(ordnung), kind="stable")
    for _, block in df.iterrows():
        abschnitt, zeile = str(block["Abschnitt"]), str(block["Zeile_ID"])
        jahr = ist_jahr if abschnitt == "IST" else PLAN_JAHR
        for fach in PVE_FAECHER if zeile == "pve" else OESG_ANALYSEKERN:
            aave = summe_im_zuschnitt(block, fach, zeile)
            if aave is None:
                continue
            text = _zuschnitt_text(block, fach, zeile, nur_regel)
            rows.append(
                {
                    **schluessel,
                    "Jahr": jahr,
                    "Abschnitt": abschnitt,
                    "Zeile_ID": zeile,
                    "Fachrichtung": fach,
                    "AAVE": aave,
                    "Zuschnitt": text,
                }
            )
    return rows


def ist_jahre(long: pd.DataFrame) -> dict[str, int]:
    """IST-Jahr je Land (Jahr der BL-Zeile «insgesamt», IST, maßgeblicher Block)."""
    out: dict[str, int] = {}
    for land in BUNDESLAENDER:
        sub = bl_long(long, land)
        j = sub.loc[(sub["Abschnitt"] == "IST") & (sub["Zeile_ID"] == "insgesamt"), "Jahr"].dropna()
        out[land] = int(j.iloc[0])
    return out


DATENSATZ = "RSG 2030"


def _eingang_zeilen(
    df: pd.DataFrame,
    ist_jahr: int,
    *,
    land: str,
    ebene: str,
    region_id: str,
    nur_regel: frozenset[str] = frozenset(),
) -> list[dict]:
    """Basis Sachleistung (ÄAVE-Zeilen `eingang.ZEILEN`, IST und PLAN) einer breiten Matrix."""
    kopf = {"Datensatz": DATENSATZ, "Land": land, "Ebene": ebene, "Region_ID": region_id}
    return [
        {
            **kopf,
            "Abschnitt": r["Abschnitt"],
            "Jahr": r["Jahr"],
            "Zeile_ID": r["Zeile_ID"],
            "Fach": r["Fachrichtung"],
            "Basis": SACHLEISTUNG,
            "AAVE": r["AAVE"],
            "Zuschnitt": r["Zuschnitt"],
        }
        for r in _aave_zeilen(df, ist_jahr, nur_regel)
    ]


def _stellen_zeilen(df: pd.DataFrame, ist_jahr: int, nur_regel: frozenset[str], **kopf) -> list[dict]:
    """Stellen je Stellen-Zeile (`stellen_eingang.ZEILEN`) und Richtwert-Fach aus einer breiten Matrix.

    Zugeschnitten wird mit derselben Funktion wie die ÄAVE (`faecher.summe_im_zuschnitt`); die ZAE fallen dabei von
    selbst weg, weil eine Stellen-Zeile nicht in `ZAE_ZEILEN` steht. Der Maximalanteil vertragsärztlicher Planstellen
    steht je Matrixspalte in einer eigenen Zeile (`<zeile>_max_vaep_prozent`): gerechnet wird Stellen × Prozent **je
    Spalte**, erst danach summiert. Prozentsätze werden nie gemittelt.

    `Max_VAEP_Prozent` bleibt leer, wenn für einen Teil der Stellen kein Prozentsatz gedruckt ist – ein Anteil, der
    nur einen Teil der Zeile abdeckt, wäre irreführend. Dass das heute nirgends vorkommt, hält ein Test fest; die
    Rohdatenprüfung `checks.pruefe_prozent_gewichtet` meldet solche Zellen schon beim Auslesen."""
    rows: list[dict] = []
    nach_zeile = {str(r["Zeile_ID"]): r for _, r in df.iterrows() if str(r["Abschnitt"]) == "PLAN"}
    for _, block in df.iterrows():
        abschnitt, zeile = str(block["Abschnitt"]), str(block["Zeile_ID"])
        if zeile not in STELLEN_ZEILEN or abschnitt not in ABSCHNITTE:
            continue
        prozente = nach_zeile.get(zeile + PROZENT_SUFFIX) if zeile not in OHNE_PROZENT else None
        jahr = ist_jahr if abschnitt == "IST" else PLAN_JAHR
        for fach in OESG_ANALYSEKERN:
            stellen = summe_im_zuschnitt(block, fach, zeile)
            if stellen is None:
                continue
            max_stellen, basis = 0.0, 0.0
            for spalte in teile(fach, zeile):
                wert = block.get(spalte)
                anteil = None if prozente is None else prozente.get(spalte)
                if pd.notna(wert) and anteil is not None and pd.notna(anteil):
                    max_stellen += float(wert) * float(anteil) / 100
                    basis += float(wert)
            # abgedeckt: Für jede Stelle dieses Fachs ist ein Prozentsatz gedruckt. Sonst bleiben beide Felder leer –
            # ein Anteil, der nur einen Teil der Zeile abdeckt, wäre irreführend.
            abgedeckt = prozente is not None and abs(basis - stellen) < 1e-9
            rows.append(
                {
                    **kopf,
                    "Abschnitt": abschnitt,
                    "Jahr": jahr,
                    "Zeile_ID": zeile,
                    "Fach": fach,
                    "Stellen": stellen,
                    "Zuschnitt": _zuschnitt_text(block, fach, zeile, nur_regel),
                    "Max_VAEP_Stellen": round(max_stellen, 6) if abgedeckt else None,
                    # bei 0 Stellen gibt es keinen Anteil (0 von 0), wohl aber die 0 oben
                    "Max_VAEP_Prozent": round(max_stellen / stellen * 100, 6) if abgedeckt and stellen > 0 else None,
                }
            )
    return rows


def stellen_eingang(long: pd.DataFrame | None = None) -> pd.DataFrame:
    """Stellen-Eingang für `oesg_methodik.stellen_eingang`: alle BL und VR, Stellen-Zeilen im ÖSG-Zuschnitt.

    Dieselben Fächer wie `aave_eingang` und derselbe `Zuschnitt`-Text – sonst verglichen Auswertungen ÄAVE und Stellen
    über verschieden geschnittene Fächer (docs/METHODIK.md, «Stellen»)."""
    long = lade_matrix_long() if long is None else long
    ist_years = ist_jahre(long)
    nur_regel = _nur_per_regel(long)
    rows: list[dict] = []
    for land, df in bl_tabellen(long).items():
        k = nur_regel.get((land, "BL", land), frozenset())
        rows += _stellen_zeilen(df, ist_years[land], k, Datensatz=DATENSATZ, Land=land, Ebene="BL", Region_ID=land)
    for (land, vr), df in vr_tabellen(long).items():
        k = nur_regel.get((land, "VR", vr), frozenset())
        rows += _stellen_zeilen(df, ist_years[land], k, Datensatz=DATENSATZ, Land=land, Ebene="VR", Region_ID=vr)
    return stellen_pruefe(pd.DataFrame(rows))


def _nur_per_regel(long: pd.DataFrame) -> dict[tuple[str, str, str], frozenset[str]]:
    """(Land, Ebene, Region_ID) → Fachspalten ohne eine Zelle aus dem PDF bzw. der Abschrift, aber mit Werten aus einer
    Korrekturregel: Die Spalte steht nicht in der Tabelle (OÖ: KFO nur in der Fußnote zu ZMK)."""
    out: dict[tuple[str, str, str], frozenset[str]] = {}
    for (land, ebene, rid), g in long.groupby(["Land", "Ebene", "Region_ID"]):
        gelesen = set(g.loc[g["Quelle"].isin(["PDF", "manuell"]), "Fach"])
        regel = set(g.loc[g["Quelle"] == "korrigiert", "Fach"]) - gelesen
        if regel:
            out[(land, ebene, str(rid))] = frozenset(regel)
    return out


def aave_eingang(long: pd.DataFrame | None = None) -> pd.DataFrame:
    """ÄAVE-Eingang für `oesg_methodik.eingang`: alle BL und VR, ÄAVE-Zeilen `eingang.ZEILEN`, nur Basis Sachleistung.

    Keine Basis inkl. Wahlärzt:innen: PLAN-ÄAVE enthalten nach ÖSG keine Wahlärzt:innen (Tabellenband S.232), und im IST
    weisen nur 6 von 9 BL und 14 von 32 VR sie aus – kein Vergleich zwischen Ländern und kein IST → PLAN möglich
    (docs/METHODIK.md, R1). Die Zeile `wahl` bleibt in der Long-CSV."""
    long = lade_matrix_long() if long is None else long
    ist_years = ist_jahre(long)
    nur_regel = _nur_per_regel(long)
    rows: list[dict] = []
    for land, df in bl_tabellen(long).items():
        k = nur_regel.get((land, "BL", land), frozenset())
        rows += _eingang_zeilen(df, ist_years[land], land=land, ebene="BL", region_id=land, nur_regel=k)
    for (land, vr), df in vr_tabellen(long).items():
        k = nur_regel.get((land, "VR", vr), frozenset())
        rows += _eingang_zeilen(df, ist_years[land], land=land, ebene="VR", region_id=vr, nur_regel=k)
    return pruefe(pd.DataFrame(rows))
