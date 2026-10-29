"""Tabelle Versorgungsdichte: Handrechnungen, Vollständigkeit, Teilzeilen und erwartete Prüfsumme.

Die Sollwerte sind bewusst als Literale aus den Quellen notiert (PDF-Seite, Statistik Austria, ÖSG-Textband S.39),
nicht aus dem Code abgeleitet:
    VD = ÄAVE / Bevölkerung × 100.000
    Position im Soll-Intervall = (VD − VDmin) / (VDmax − VDmin)
    ÄAVE-Abstand = (VD − nächste Grenze) × Bevölkerung / 100.000, 0 im Soll-Intervall
"""

from __future__ import annotations

import re

import pandas as pd
import pytest
from conftest import pruefe_ausgabe

pytestmark = pytest.mark.slow  # liest Planungsmatrizen und Bevölkerungsdateien (~20 s)

# Versorgungsdichte-Soll-Intervalle des ÖSG (VDmin, VDmax), Textband S.39
AM, IM, KIJU, CH, ZMK, KFO = (34.9, 64.8), (14.4, 26.8), (4.2, 7.9), (4.5, 8.4), (28.3, 52.6), (2.8, 5.1)

# (Ebene, Region, Abschnitt, Fach, ÄAVE laut PDF, Bevölkerung, Intervall, Herkunft)
FAELLE = [
    ("BL", "NÖ", "IST", "AM", 808.8, 1_718_373, AM, "NÖ Anlage S.1, IST ÄAVE insgesamt 2023; Bev. 1.1.2023"),
    # AM laut ÖSG inkl. ZAE (Textband S.39, Legende **): AM 827,7 + SON/IDB spitalsambulant 44,6 (Fußnote (5)
    # «spitalsambulant = ZAE»); im IST stehen die spitalsambulanten AM-ÄAVE noch in AM, SON/IDB = 0,0
    ("BL", "NÖ", "PLAN", "AM", 827.7 + 44.6, 1_742_943, AM, "NÖ Anlage S.1, PLAN 2030 AM + ZAE; Prognose 2025 HS"),
    # IM laut ÖSG inkl. Pulmologie: IM 192,6 + PUL 32,4
    ("BL", "NÖ", "IST", "IM", 192.6 + 32.4, 1_718_373, IM, "NÖ Anlage S.1, IM + PUL"),
    # Kärnten plant in SVE → ÄAVE-Äquivalente-Block
    ("BL", "Kärnten", "IST", "AM", 251.9, 564_513, AM, "Ktn Anhang S.97, ÄAVE insgesamt 2022 (Äquivalente)"),
    # Wien PLAN insgesamt ist im PDF leer → korrekturen.csv: spitalsambulant 15 + niedergelassen 854
    ("BL", "Wien", "PLAN", "AM", 15 + 854, 2_101_123, AM, "Wien Anlage S.33, PLAN spital + niedergelassen"),
    ("BL", "Wien", "IST", "AM", 748.0, 1_931_593, AM, "Wien Anlage S.33, IST ÄAVE insgesamt 2022"),
    ("VR", "74", "IST", "AM", 22.4, 48_854, AM, "Tirol Anlage S.9 (Osttirol), IST 2023; Bev. Bezirk Lienz"),
    ("VR", "21", "IST", "AM", 152.1, 341_578, AM, "Ktn Anhang S.99 (Bildseite, manuell), Äquivalente 2022"),
    # Je Land mindestens ein Fall. ÄAVE vom Seitenbild abgelesen, Bevölkerung mit eigenem Skript direkt aus den
    # Open-Data-Dateien (Summe aller Gemeinden des Landes bzw. Prognose 2025, Hauptszenario) – unabhängig vom Code.
    (
        "BL",
        "Burgenland",
        "IST",
        "AM",
        172.1,
        297_583,
        AM,
        "Bgld Anlage 1 S.1 (Bildseite), Äquivalente insgesamt 2022",
    ),
    # OÖ: ZMK ohne KFO; KFO 38,2 nur in der Fußnote zu «ZMK*» (S.10) → ZMK nach ÖSG = ZMK + KFO (METHODIK R4)
    ("BL", "OÖ", "IST", "ZMK", 534.6 + 38.2, 1_505_140, ZMK, "OÖ Anlage S.9, ZMK* 534,6 + KFO 38,2 (Fußnote S.10)"),
    # KFO gegen die Unterzeile «- davon mit kieferorthopädischem Schwerpunkt» (Textband S.39)
    ("BL", "OÖ", "IST", "KFO", 38.2, 1_505_140, KFO, "OÖ Fußnote S.10: «zusätzlich KFO: IST 2022 und Plan 2030: 38,2»"),
    # Salzburg: ZAE stehen in SON/IDB spitalsambulant (Fußnote (7) «spitalsambulant = ZAE») → AM 277,8 + 17,4
    (
        "BL",
        "Salzburg",
        "PLAN",
        "AM",
        277.8 + 17.4,
        573_797,
        AM,
        "Sbg Anlage S.1, PLAN 2030 AM + SON/IDB spitalsambulant",
    ),
    ("BL", "Salzburg", "PLAN", "IM", 104.7 + 20.5, 573_797, IM, "Sbg Anlage S.1, PLAN 2030 IM 104,7 + PUL 20,5"),
    # Steiermark plant in SVE → Äquivalente-Block; CH laut ÖSG inkl. KJC und PCH (beide 0 ÄAVE, «zugeordnet zu CH»)
    (
        "BL",
        "Steiermark",
        "IST",
        "CH",
        89.3 + 0 + 0,
        1_252_922,
        CH,
        "Stmk Anlage 1 S.1, ÄAVE insgesamt 2022 (Äquivalente)",
    ),
    ("BL", "Vorarlberg", "IST", "KIJU", 31.6, 406_395, KIJU, "Vbg Anlage S.1, IST ÄAVE insgesamt 2023; Bev. 1.1.2023"),
    # Wien PLAN insgesamt im PDF leer → spitalsambulant «-» (0) + niedergelassen 174 (korrekturen.csv);
    # Bevölkerung = Wien 1.1.2030 × ÖROK-Anteil VR 93 2030 (408.817 / 2.025.796; gerundet → Toleranz 1e-6)
    ("VR", "93", "PLAN", "AM", 0 + 174, 2_101_123 * 408_817.2 / 2_025_796.1, AM, "Wien Anlage S.36 (VR 93)"),
]


# Teilzeilen (METHODIK R10): (Ebene, Region, Abschnitt, Zeile_ID, Fach, ÄAVE laut PDF, Bevölkerung, Zuschnitt, Herkunft).
# Kein Soll-Intervall: VDmin, VDmax, Lage, Position und ÄAVE-Abstand leer.
TEILZEILEN = [
    # NÖ: im IST stehen die spitalsambulanten AM-ÄAVE in AM (44,1; SON/IDB 0,0), im PLAN in SON/IDB (AM 0,0 + 44,6)
    ("BL", "NÖ", "IST", "spitalsambulant", "AM", 44.1, 1_718_373, "AM (ZAE nicht getrennt ausgewiesen)", "NÖ S.1"),
    ("BL", "NÖ", "PLAN", "spitalsambulant", "AM", 0.0 + 44.6, 1_742_943, "AM + ZAE", "NÖ S.1, SON/IDB = ZAE"),
    # extramural ohne ZAE: PLAN gedruckt 827,7; IST = insgesamt 808,8 − spitalsambulant 44,1 (im PDF nicht gedruckt)
    ("BL", "NÖ", "PLAN", "extramural", "AM", 827.7, 1_742_943, "AM", "NÖ S.1, PLAN extramural"),
    ("BL", "NÖ", "IST", "extramural", "AM", 808.8 - 44.1, 1_718_373, "AM", "NÖ S.1, insgesamt − spitalsambulant"),
    # Steiermark plant in SVE → Äquivalente-Block, IM inkl. PUL: 175,2 + 3,6
    (
        "BL",
        "Steiermark",
        "IST",
        "spitalsambulant",
        "IM",
        175.2 + 3.6,
        1_252_922,
        "IM + PUL",
        "Stmk Anlage 1 S.1, Äquivalente",
    ),
    # OÖ ZMK extramural IST = niedergelassen 455,5 + selbst. Amb. 0,0 + Kassenamb. 79,1, dazu KFO 38,2 (Fußnote S.10)
    (
        "BL",
        "OÖ",
        "IST",
        "extramural",
        "ZMK",
        455.5 + 0.0 + 79.1 + 38.2,
        1_505_140,
        "ZMK + KFO (KFO nicht in der Tabelle, per Korrekturregel)",
        "OÖ Anlage S.9 und Fußnote S.10",
    ),
    ("BL", "Wien", "PLAN", "pve", "AM", 247.0, 2_101_123, "AM", "Wien Anlage S.33, «zumindest» in PVE"),
    ("BL", "Wien", "PLAN", "pve", "KIJU", 46.0, 2_101_123, "KIJU", "Wien Anlage S.33"),
    # Tirol IST: PVE «-» = 0 – eine Zeile mit VD 0, keine Lücke (Bev. 1.1.2023, Summe der Tiroler Gemeinden)
    ("BL", "Tirol", "IST", "pve", "AM", 0.0, 771_304, "AM", "Tirol Anlage S.1"),
]


@pytest.fixture(scope="module")
def kennz():
    from rsg2030.versorgungsdichte import baue_versorgungsdichte

    return baue_versorgungsdichte()


def _eine(k, ebene, region, abschnitt, zeile, fach):
    z = k[
        (k["Ebene"] == ebene)
        & (k["Region_ID"] == region)
        & (k["Abschnitt"] == abschnitt)
        & (k["Zeile_ID"] == zeile)
        & (k["Fach"] == fach)
    ]
    assert len(z) == 1, (ebene, region, abschnitt, zeile, fach)
    return z.iloc[0]


@pytest.mark.parametrize("ebene, region, abschnitt, fach, aave, bev, intervall, herkunft", FAELLE)
def test_handrechnung(kennz, ebene, region, abschnitt, fach, aave, bev, intervall, herkunft):
    z = _eine(kennz, ebene, region, abschnitt, "insgesamt", fach)
    vd = aave / bev * 100_000
    assert z["AAVE"] == pytest.approx(aave), herkunft
    assert z["Bevoelkerung"] == pytest.approx(bev, rel=1e-6), herkunft
    assert z["VD"] == pytest.approx(vd, rel=1e-6), herkunft
    assert (z["VDmin"], z["VDmax"]) == intervall
    assert z["Position_im_Intervall"] == pytest.approx((vd - intervall[0]) / (intervall[1] - intervall[0]), rel=1e-6)
    grenze = min(max(vd, intervall[0]), intervall[1])
    assert z["AAVE_Abstand_Intervall"] == pytest.approx((vd - grenze) * bev / 100_000, abs=1e-6), herkunft
    lage = "unter" if vd < intervall[0] else "über" if vd > intervall[1] else "im"
    assert z["Lage_im_Intervall"] == lage, herkunft


@pytest.mark.parametrize("ebene, region, abschnitt, zeile, fach, aave, bev, text, herkunft", TEILZEILEN)
def test_handrechnung_teilzeile(kennz, ebene, region, abschnitt, zeile, fach, aave, bev, text, herkunft):
    z = _eine(kennz, ebene, region, abschnitt, zeile, fach)
    assert z["AAVE"] == pytest.approx(aave), herkunft
    assert z["Bevoelkerung"] == pytest.approx(bev, rel=1e-6), herkunft
    assert z["VD"] == pytest.approx(aave / bev * 100_000, rel=1e-6), herkunft
    assert z["Zuschnitt"] == text, herkunft
    assert z[["VDmin", "VDmax", "Lage_im_Intervall", "Position_im_Intervall", "AAVE_Abstand_Intervall"]].isna().all(), (
        herkunft
    )


# Beispiele in docs/DATEN.md, «Vergleich mit dem Soll-Intervall: welche Zahl für welche Aussage» (PLAN 2030, insgesamt):
# (Ebene, Region, Fach, VD, Lage, Position, ÄAVE-Abstand) – gerundet wie in der Doku
BEISPIELE = [
    ("BL", "OÖ", "IM", 13.5, "unter", -0.07, -13.5),
    ("VR", "66", "KJP", 0.52, "unter", -0.46, -0.26),  # Westliche Obersteiermark
    ("BL", "Tirol", "KJP", 1.41, "über", 1.01, 0.04),
    ("BL", "Wien", "IM", 33.1, "über", 1.51, 131.9),
]


@pytest.mark.parametrize("ebene, region, fach, vd, lage, position, aave", BEISPIELE)
def test_beispiele_in_daten_md(kennz, ebene, region, fach, vd, lage, position, aave):
    """Die Beispielwerte der Doku stehen so in der Tabelle; ändert sich eine Version, fällt das hier auf."""
    z = _eine(kennz, ebene, region, "PLAN", "insgesamt", fach)
    nachkommastellen = len(str(vd).split(".")[1])
    assert round(z["VD"], nachkommastellen) == vd
    assert z["Lage_im_Intervall"] == lage
    assert round(z["Position_im_Intervall"], 2) == position
    assert round(z["AAVE_Abstand_Intervall"], len(str(aave).split(".")[1])) == aave


def test_lage_position_abstand_stimmig(kennz):
    """Die drei Kennzahlen setzen an denselben gedruckten Grenzen an und widersprechen sich nie:
    unter ⇔ Position < 0 ⇔ ÄAVE-Abstand < 0; im ⇔ 0 ≤ Position ≤ 1 ⇔ ÄAVE-Abstand = 0; über ⇔ > 1 ⇔ > 0."""
    k = kennz[kennz["Zeile_ID"] == "insgesamt"]
    pos, abst, lage = k["Position_im_Intervall"], k["AAVE_Abstand_Intervall"], k["Lage_im_Intervall"]
    assert ((lage == "unter") == (pos < 0)).all() and ((lage == "unter") == (abst < 0)).all()
    assert ((lage == "über") == (pos > 1)).all() and ((lage == "über") == (abst > 0)).all()
    assert ((lage == "im") == (abst == 0)).all()
    assert set(lage) == {"unter", "im", "über"}


def test_zae_bei_leerer_am_zelle(kennz):
    """Burgenland VR 12 PLAN: AM spitalsambulant leer gedruckt, ZAE 5,99 in SON/IDB (Anlage 1 S.8) → AM = ZAE."""
    z = _eine(kennz, "VR", "12", "PLAN", "spitalsambulant", "AM")
    assert z["AAVE"] == pytest.approx(5.99) and z["Zuschnitt"] == "AM + ZAE"


def test_teile_ergeben_insgesamt(kennz):
    """spitalsambulant + extramural = insgesamt je Region, Abschnitt und Fach, auch im ÖSG-Zuschnitt (METHODIK R10).
    Toleranz = Rundung der gedruckten Zellen, aus denen die drei Werte entstehen (Wien ganzzahlig: bis ±1)."""
    from oesg_methodik.faecher import ZAE, ZAE_QUELLE, teile
    from rsg2030.analyse_eingang import lade_matrix_long
    from rsg2030.schema import matrix_long

    long = lade_matrix_long()
    k = kennz.set_index(["Ebene", "Region_ID", "Abschnitt", "Fach", "Zeile_ID"])["AAVE"].unstack()
    geprueft = 0
    for (ebene, rid, abschnitt, fach), r in k.iterrows():
        land = kennz.loc[kennz["Region_ID"] == rid, "Land"].iloc[0]
        m = matrix_long(long, land, ebene, rid)
        m = m[m["Abschnitt"] == abschnitt]
        rundung = 0.0
        for zeile in ("spitalsambulant", "extramural", "insgesamt"):
            spalten = [s for s in teile(fach, zeile) if s != ZAE]
            rundung += m.loc[(m["Zeile_ID"] == zeile) & m["Fach"].isin(spalten), "Rundung"].fillna(0).sum()
        if fach == "AM":
            zz, zs = ZAE_QUELLE
            rundung += 2 * m.loc[(m["Zeile_ID"] == zz) & (m["Fach"] == zs), "Rundung"].fillna(0).sum()
        summe = (0 if pd.isna(r["spitalsambulant"]) else r["spitalsambulant"]) + r["extramural"]
        assert abs(summe - r["insgesamt"]) <= rundung + 1e-9, (ebene, rid, abschnitt, fach, summe, r["insgesamt"])
        geprueft += 1
    assert geprueft == (kennz["Zeile_ID"] == "insgesamt").sum()


def test_teilzeilen_vollstaendig(kennz):
    """Zu jeder Zeile «insgesamt» gibt es extramural; spitalsambulant fehlt nur, wo die Matrix die Zelle leer druckt.
    pve nur AM und KIJU, Bevölkerung je Region und Abschnitt in allen Zeilen gleich, Soll-Intervall nur bei insgesamt."""
    schluessel = ["Ebene", "Region_ID", "Abschnitt", "Fach"]
    insg = kennz[kennz["Zeile_ID"] == "insgesamt"].set_index(schluessel).index
    extra = kennz[kennz["Zeile_ID"] == "extramural"].set_index(schluessel).index
    assert insg.sort_values().equals(extra.sort_values())
    assert set(kennz.loc[kennz["Zeile_ID"] == "pve", "Fach"]) == {"AM", "KIJU"}
    assert (kennz.groupby(["Ebene", "Region_ID", "Abschnitt"])["Bevoelkerung"].nunique() == 1).all()
    teil = kennz[kennz["Zeile_ID"] != "insgesamt"]
    assert (
        teil[["VDmin", "VDmax", "Lage_im_Intervall", "Position_im_Intervall", "AAVE_Abstand_Intervall"]]
        .isna()
        .all()
        .all()
    )


def test_vollstaendig(kennz):
    """9 BL und 32 VR, je IST und PLAN; 17 Fächer (KFO nur, wo es eine eigene Spalte hat); nur Basis Sachleistung."""
    k = kennz[kennz["Zeile_ID"] == "insgesamt"]
    assert k.loc[k["Ebene"] == "BL", "Region_ID"].nunique() == 9
    assert k.loc[k["Ebene"] == "VR", "Region_ID"].nunique() == 32
    assert set(k["Abschnitt"]) == {"IST", "PLAN"} and set(k["Basis"]) == {"Sachleistung"}
    assert k["Fach"].nunique() == 17 and k["VD"].notna().all() and k["VDmin"].notna().all()


def test_zuschnitt(kennz):
    """Spalte «Zuschnitt» sagt je Zeile, welche Spalten der Matrix eingehen (METHODIK R4, R5)."""
    k = kennz[kennz["Zeile_ID"] == "insgesamt"]
    bl = k[k["Ebene"] == "BL"].set_index(["Land", "Abschnitt", "Fach"])["Zuschnitt"]
    assert bl[("NÖ", "PLAN", "AM")] == "AM + ZAE" and bl[("NÖ", "IST", "AM")] == "AM (ZAE nicht getrennt ausgewiesen)"
    assert bl[("Wien", "PLAN", "AM")] == "AM (ZAE nicht getrennt ausgewiesen)"  # SON/IDB «-», Fußnote: ZAE offen
    assert bl[("OÖ", "IST", "ZMK")] == "ZMK + KFO (KFO nicht in der Tabelle, per Korrekturregel)"
    assert bl[("Wien", "IST", "ZMK")] == "ZMK (KFO nicht getrennt ausgewiesen)"
    assert bl[("Kärnten", "IST", "AM")] == "AM (ZAE nicht getrennt ausgewiesen)"
    assert not {"Wien", "Vorarlberg"} & set(k.loc[k["Fach"] == "KFO", "Land"])  # KFO in ZMK enthalten


def test_spalten_in_daten_md(kennz):
    """Jede Spalte der Tabelle steht in der Spaltentabelle von docs/DATEN.md, und dort steht keine, die es nicht gibt."""
    from conftest import ROOT

    text = (ROOT / "docs" / "DATEN.md").read_text(encoding="utf-8")
    abschnitt = text.split("## `RSG_2030_Versorgungsdichte.csv`")[1].split("\n## ")[0]
    erste_zellen = [z.split("|")[1] for z in abschnitt.splitlines() if z.startswith("| `")]
    beschrieben = {name for zelle in erste_zellen for name in re.findall(r"`([^`]+)`", zelle)}
    assert beschrieben == set(kennz.columns)


def test_ist_jahr_je_land(kennz):
    """IST-Jahre sind gemischt (2022/2023): jedes Land nutzt Bevölkerung und Jahr seiner eigenen Matrix."""
    ist = kennz[kennz["Abschnitt"] == "IST"].drop_duplicates("Land").set_index("Land")["Jahr"].to_dict()
    assert ist["NÖ"] == 2023 and ist["Wien"] == 2022 and ist["Kärnten"] == 2022
    assert set(kennz.loc[kennz["Abschnitt"] == "PLAN", "Jahr"]) == {2030}


def test_versorgungsdichte_csv_aktuell(kennz):
    """Frisch gerechnet = erwartete Prüfsumme der veröffentlichten Version, Zeichen für Zeichen."""
    from rsg2030.versorgungsdichte import CSV_FORMAT, versorgungsdichte_csv

    pfad = versorgungsdichte_csv()
    pruefe_ausgabe(pfad.name, kennz.to_csv(**CSV_FORMAT), pfad)
