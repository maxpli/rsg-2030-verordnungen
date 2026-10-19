"""Bevölkerungsdaten für BL und Versorgungsregionen (VR), Stichtag immer 1.1.

Quellen (alle CC BY 4.0, Register `rsg2030/quellen/quellen.csv`):

- IST: Statistik Austria Open Data, «Bevölkerungsstand zu Jahresbeginn» je Jahr
  (`OGD_bevstandjbab2002_BevStand_<Jahr>.csv`, je Gemeinde, Alter und Geschlecht). Bezirk = die ersten drei
  Stellen der Gemeindekennziffer (Wien: Gemeindebezirke); BL = Summe der Bezirke. 1.1.2021 ergibt genau die
  ÖSG-Wohnbevölkerung 2021 (8.932.664).
- PLAN 2030, BL: Statistik Austria Open Data, «Bevölkerung zum Jahresanfang», Bevölkerungsprognose 2025,
  Hauptszenario (`OGD_bevjahresanf_PR_BEVJA_10.csv`, je Bundesland, 5-Jahres-Altersgruppe und Geschlecht),
  Summe über Alter und Geschlecht.
- PLAN 2030, VR: BL-Wert × Anteil der VR am Land laut ÖROK-Prognose 2021 (`OeROK_Prognose_2021.ods`) –
  Vorgehen laut ÖSG-Methodenband 2025 (BL-Prognose «unter Heranziehung der aktuellen ÖROK-Prognose
  auf kleinräumige Gliederungsebenen hinunter projiziert»). Die VR summieren sich exakt zum BL-Wert.

Bevölkerungszahlen werden als float geführt, damit die Kennzahlen-CSV Zeichen für Zeichen gleich bleibt.

Bezirk → VR: ÖSG-Liste (`referenz/oesg_regionen.csv`), Übergabe als DataFrame `regionen`.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

import pandas as pd

from oesg_methodik import BUNDESLAENDER, LAND_KURZ
from oesg_methodik.pfade import OESG_REGIONEN_CSV, statistik_austria_dir

OEROK_ODS_NAME = "OeROK_Prognose_2021.ods"
PROGNOSE_CSV_NAME = "OGD_bevjahresanf_PR_BEVJA_10.csv"
# Szenario-Spalten tragen den Prognose-Jahrgang im Namen: F-S25V1 = Hauptszenario der Prognose 2025
HAUPTSZENARIO_RE = re.compile(r"F-S(\d{2})V1")
# Open-Data-Code des Bundeslands (C-B00-0) → Projekt-Kürzel
PROGNOSE_LAND = {
    "B00-1": "Burgenland",
    "B00-2": "Kärnten",
    "B00-3": "NÖ",
    "B00-4": "OÖ",
    "B00-5": "Salzburg",
    "B00-6": "Steiermark",
    "B00-7": "Tirol",
    "B00-8": "Vorarlberg",
    "B00-9": "Wien",
}


def _kurz(name: str) -> str:
    name = str(name).strip()
    return LAND_KURZ.get(name, name)


def _bevstand_csv(jahr: int) -> Path:
    return statistik_austria_dir() / f"OGD_bevstandjbab2002_BevStand_{jahr}.csv"


def _prognose_csv() -> Path:
    return statistik_austria_dir() / PROGNOSE_CSV_NAME


# --- IST --------------------------------------------------------------------------------------


def _bezirke_jahr(jahr: int) -> pd.Series:
    """Bevölkerung am 1.1.`jahr` je Bezirk (Index Bezirkskennziffer), Summe über Gemeinden, Alter, Geschlecht."""
    return _bezirke_lesen(_bevstand_csv(jahr), jahr)


@cache
def _bezirke_lesen(path: Path, jahr: int) -> pd.Series:
    if not path.is_file():
        raise FileNotFoundError(
            f"Bevölkerung zu Jahresbeginn {jahr} fehlt: {path} (im Register? python -m rsg2030 download)"
        )
    d = pd.read_csv(path, sep=";", usecols=["C-A10-0", "C-GRGEMAKT-0", "F-ISIS-1"], dtype={"C-GRGEMAKT-0": str})
    if set(d["C-A10-0"]) != {f"A10-{jahr}"}:
        raise ValueError(f"{path.name}: enthält andere Jahre als {jahr}: {sorted(set(d['C-A10-0']))[:3]}")
    bezirk = d["C-GRGEMAKT-0"].str.removeprefix("GRGEMAKT-").str[:3].astype(int)
    return d.groupby(bezirk)["F-ISIS-1"].sum().astype(float)


def bevoelkerung_bezirke(jahre: tuple[int, ...]) -> pd.DataFrame:
    """IST je Bezirk (Stand 1.1.): Spalten Bezirk, Name, Jahr, Bevoelkerung."""
    namen = lade_regionen().drop_duplicates("Bezirk").set_index("Bezirk")["Bezirk_Name"]
    teile = [
        pd.DataFrame({"Bezirk": s.index, "Jahr": jahr, "Bevoelkerung": s.values})
        for jahr in jahre
        for s in [_bezirke_jahr(jahr)]
    ]
    out = pd.concat(teile, ignore_index=True)
    out.insert(1, "Name", out["Bezirk"].map(namen))
    return out


def _mit_region(bez: pd.DataFrame, regionen: pd.DataFrame) -> pd.DataFrame:
    zuord = regionen.drop_duplicates("Bezirk").set_index("Bezirk")[["VR", "VR_Name", "Bundesland"]]
    out = bez.join(zuord, on="Bezirk")
    fehlt = out.loc[out["VR"].isna(), "Bezirk"].unique()
    if len(fehlt):
        raise ValueError(f"Bezirke ohne Versorgungsregion laut ÖSG-Liste: {sorted(fehlt)}")
    out["Land"] = out["Bundesland"].map(_kurz)
    out["VR"] = out["VR"].astype(int).astype(str)
    return out


def lade_regionen() -> pd.DataFrame:
    """Bezirk → Versorgungsregion laut ÖSG (`pfade.OESG_REGIONEN_CSV`)."""
    return pd.read_csv(OESG_REGIONEN_CSV)


def bevoelkerung_bl_ist(jahre: tuple[int, ...], regionen: pd.DataFrame) -> pd.DataFrame:
    """IST je BL (1.1.) als Summe der Bezirke: Land, Jahr, Bevoelkerung."""
    bez = _mit_region(bevoelkerung_bezirke(jahre), regionen)
    return bez.groupby(["Land", "Jahr"], as_index=False)["Bevoelkerung"].sum()


# --- PLAN: Bundesländer -----------------------------------------------------------------------


def _hauptszenario() -> tuple[str, int]:
    """(Spalte des Hauptszenarios, Prognose-Jahrgang) aus dem Kopf der Prognose-Datei.

    Welcher Jahrgang gilt, legt das Register fest (Prüfsumme); der Code nimmt das Hauptszenario dieser Datei und meldet
    den Jahrgang, statt ihn fest einzubauen (docs/METHODIK.md, R7)."""
    path = _prognose_csv()
    if not path.is_file():
        raise FileNotFoundError(f"Bevölkerungsprognose fehlt: {path} (python -m rsg2030 download)")
    spalten = [c for c in pd.read_csv(path, sep=";", nrows=0).columns if HAUPTSZENARIO_RE.fullmatch(c)]
    if len(spalten) != 1:
        raise ValueError(f"{path.name}: genau eine Hauptszenario-Spalte (F-S..V1) erwartet, gefunden {spalten}")
    m = HAUPTSZENARIO_RE.fullmatch(spalten[0])
    assert m is not None
    return spalten[0], 2000 + int(m.group(1))


def prognose_jahrgang() -> int:
    """Jahrgang der verwendeten Bevölkerungsprognose (z. B. 2025)."""
    return _hauptszenario()[1]


def _prognose_bl(jahr: int) -> tuple[tuple[str, float], ...]:
    """Bevölkerung am 1.1.`jahr` je BL laut Hauptszenario: Summe über die 5-Jahres-Altersgruppen und beide
    Geschlechter. Kontrolle: je Land genau 20 Altersgruppen × 2 Geschlechter."""
    return _prognose_bl_lesen(_prognose_csv(), jahr)


@cache
def _prognose_bl_lesen(path: Path, jahr: int) -> tuple[tuple[str, float], ...]:
    spalte, _ = _hauptszenario()
    d = pd.read_csv(path, sep=";", usecols=["C-B00-0", "C-A10-0", "C-GALT5J99-0", "C-C11-0", spalte])
    d = d[(d["C-A10-0"] == f"A10-{jahr}") & d["C-B00-0"].isin(PROGNOSE_LAND)]
    zellen = d.groupby("C-B00-0").size()
    if len(zellen) != 9 or (zellen != 40).any():
        raise ValueError(f"{path.name}: {jahr} nicht je Land 20 Altersgruppen × 2 Geschlechter: {zellen.to_dict()}")
    summe = d.groupby("C-B00-0")[spalte].sum().astype(float)
    werte = {PROGNOSE_LAND[c]: v for c, v in summe.items()}
    return tuple((land, werte[land]) for land in BUNDESLAENDER)


def bevoelkerung_prognose(jahr: int = 2030) -> pd.DataFrame:
    """Bevölkerung am 1.1.`jahr` je BL laut Bevölkerungsprognose 2025 (Hauptszenario)."""
    return pd.DataFrame([{"Land": land, "Jahr": jahr, "Bevoelkerung": v} for land, v in _prognose_bl(jahr)])


def bevoelkerung_bl(
    land: str,
    jahr: int,
    *,
    ist: pd.DataFrame,
    prognose_2030: pd.DataFrame,
) -> float:
    """IST-Jahr aus `ist` (Stand 1.1., `bevoelkerung_bl_ist`), 2030 aus `prognose_2030` (`bevoelkerung_prognose`)."""
    if jahr == 2030:
        sub = prognose_2030[prognose_2030["Land"] == land]
        if sub.empty:
            raise ValueError(f"Keine Prognose-Bevölkerung für {land} 2030")
        return float(sub.iloc[0]["Bevoelkerung"])
    sub = ist[(ist["Land"] == land) & (ist["Jahr"] == jahr)]
    if sub.empty:
        raise ValueError(f"Keine IST-Bevölkerung für {land} {jahr}")
    return float(sub.iloc[0]["Bevoelkerung"])


# --- PLAN: Versorgungsregionen ----------------------------------------------------------------


def _oerok_roh() -> pd.DataFrame:
    """ÖROK-Prognose 2021, Bevölkerung zu Jahresanfang je Bezirk (Prognoseregionen zusammengefasst)."""
    return _oerok_lesen(statistik_austria_dir() / OEROK_ODS_NAME)


@cache
def _oerok_lesen(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"ÖROK-Prognose fehlt: {path}")
    d = pd.read_excel(path, sheet_name="Bev_Insg_", engine="odf", header=None)
    jahre: dict[int, int] = {}
    for i, v in d.iloc[3].items():  # Jahresspalten; dahinter folgen Indexspalten mit denselben Jahren
        if pd.notna(v) and int(v) not in jahre.values():
            jahre[i] = int(v)
    i0 = d.index[d[0].astype(str).str.startswith("Bezirke")][0]
    r = d.iloc[i0 + 1 :].copy()
    r = r[pd.to_numeric(r[0], errors="coerce").notna()]
    # Kennzahl = Bezirk × 10 + Teilregion; Gesamtzeile je Bezirk endet auf 0 (Teilregionen nicht doppelt zählen)
    r = r[r[0].astype(int) % 10 == 0]
    out = pd.DataFrame({"Bezirk": (r[0].astype(int) // 10).values})
    for i, y in jahre.items():
        out[y] = r[i].astype(float).values
    return out


def _oerok_anteile(jahr: int, regionen: pd.DataFrame) -> pd.DataFrame:
    """Anteil je VR an ihrem Land laut ÖROK. ÖROK führt «Eisenstadt-Umgebung / Rust» unter einer
    Kennzahl (102); beide Bezirke liegen in VR 11 – die Zuordnung über die VR ist daher eindeutig."""
    o = _oerok_roh()[["Bezirk", jahr]].rename(columns={jahr: "Bevoelkerung"})
    o = _mit_region(o, regionen)
    vr = o.groupby(["Land", "VR"], as_index=False)["Bevoelkerung"].sum()
    vr["Anteil"] = vr["Bevoelkerung"] / vr.groupby("Land")["Bevoelkerung"].transform("sum")
    return vr[["Land", "VR", "Anteil"]]


def bevoelkerung_vr(
    regionen: pd.DataFrame,
    *,
    ist_jahre: dict[str, int],
    plan_jahr: int = 2030,
) -> pd.DataFrame:
    """Bevölkerung je VR: IST (Summe der Bezirke im IST-Jahr des Landes) und PLAN (BL-Prognose × ÖROK-Anteil).

    Spalten: Land, VR, VR_Name, Abschnitt, Jahr, Bevoelkerung. Die VR eines Landes summieren sich exakt
    zum BL-Wert (IST wie PLAN).
    """
    namen = regionen.drop_duplicates("VR").assign(VR=lambda d: d["VR"].astype(str)).set_index("VR")["VR_Name"]
    bez = _mit_region(bevoelkerung_bezirke(tuple(sorted(set(ist_jahre.values())))), regionen)
    ist = (
        bez[bez["Jahr"] == bez["Land"].map(ist_jahre)]
        .groupby(["Land", "VR", "Jahr"], as_index=False)["Bevoelkerung"]
        .sum()
        .assign(Abschnitt="IST")
    )

    anteil = _oerok_anteile(plan_jahr, regionen)
    bl = bevoelkerung_prognose(plan_jahr).set_index("Land")["Bevoelkerung"]
    plan = anteil.assign(Jahr=plan_jahr, Abschnitt="PLAN", Bevoelkerung=anteil["Anteil"] * anteil["Land"].map(bl))

    out = pd.concat([ist, plan[ist.columns]], ignore_index=True)
    out["VR_Name"] = out["VR"].map(namen)
    return (
        out[["Land", "VR", "VR_Name", "Abschnitt", "Jahr", "Bevoelkerung"]]
        .sort_values(["Abschnitt", "VR"])
        .reset_index(drop=True)
    )


# --- Zuordnung zum ÄAVE-Eingang ---------------------------------------------------------------


def bevoelkerung_fuer(aave: pd.DataFrame, regionen: pd.DataFrame) -> pd.DataFrame:
    """Bevölkerung zu jeder Region des ÄAVE-Eingangs (`eingang.REGION` + Bevoelkerung).

    BL: IST = Summe der Bezirke am 1.1. des Jahres, PLAN = Prognose 2025 am 1.1. des Planjahres.
    VR: IST = Summe ihrer Bezirke im IST-Jahr ihres Landes, PLAN = BL-Prognose × ÖROK-Anteil (R7).
    """
    keys = aave[["Land", "Ebene", "Region_ID", "Abschnitt", "Jahr"]].drop_duplicates()
    teile: list[pd.DataFrame] = []
    bl = keys[keys["Ebene"] == "BL"]
    ist = bl[bl["Abschnitt"] == "IST"]
    if len(ist):
        p = bevoelkerung_bl_ist(tuple(sorted(set(ist["Jahr"]))), regionen)
        teile.append(ist.merge(p, on=["Land", "Jahr"], how="left"))
    plan = bl[bl["Abschnitt"] == "PLAN"]
    for jahr in sorted(set(plan["Jahr"])):
        p = bevoelkerung_prognose(int(jahr))
        teile.append(plan[plan["Jahr"] == jahr].merge(p, on=["Land", "Jahr"], how="left"))
    vr = keys[keys["Ebene"] == "VR"]
    if len(vr):
        ist_jahre = vr[vr["Abschnitt"] == "IST"].drop_duplicates("Land").set_index("Land")["Jahr"].astype(int).to_dict()
        plan_jahre = set(vr.loc[vr["Abschnitt"] == "PLAN", "Jahr"])
        if len(plan_jahre) > 1:
            raise ValueError(f"VR: mehrere Planjahre {sorted(plan_jahre)}")
        p = bevoelkerung_vr(regionen, ist_jahre=ist_jahre, plan_jahr=int(plan_jahre.pop()) if plan_jahre else 2030)
        p = p.rename(columns={"VR": "Region_ID"}).drop(columns="VR_Name")
        teile.append(vr.merge(p, on=["Land", "Region_ID", "Abschnitt", "Jahr"], how="left"))
    return pd.concat(teile, ignore_index=True)
