"""Tabelle Stellen: derselbe Zuschnitt wie bei den ÄAVE, Vollständigkeit, Handrechnungen.

Die Sollwerte stehen bewusst als Literale aus den Verordnungen da, nicht aus dem Code abgeleitet. Was jede Prüfung
belegt und was nicht: docs/PRUEFUNG.md, «Wer prüft was».
"""

from __future__ import annotations

import pandas as pd
import pytest
from conftest import pruefe_ausgabe

from oesg_methodik.faecher import MATRIXSPALTEN, OESG_ANALYSEKERN, ZAE, teile
from oesg_methodik.stellen_eingang import IST_ZEILEN, PLAN_ZEILEN, SPALTEN, TEILMENGEN, pruefe
from rsg2030.analyse_eingang import lade_matrix_long, stellen_eingang
from rsg2030.schema import matrix_long
from rsg2030.stellen import ohne_anteil

# Spalten der Matrix ohne Richtwert: Sie gehören in keinen Zuschnitt, dürfen aber beim Vergleich mit «gesamt»
# nicht fehlen – sonst fiele still weg, was in ihnen steht (METHODIK R4; docs/DATEN.md, Fallstrick «nicht summieren»).
OHNE_RICHTWERT = ("AN", "LAB", "NCH", "NUK", "PAT", "PMR", "RAD", "SON/IDB", "STR")
# PUL steckt schon in IM, KFO in ZMK: Eine Summe über alle Richtwert-Fächer zählte sie doppelt (METHODIK R4).
DOPPELT = ("PUL", "KFO")


def test_zuschnitt_gleich_wie_bei_den_aave():
    """Der Kern der Tabelle: Ein Fach besteht in einer Stellen-Zeile aus genau denselben Matrixspalten wie in der
    ÄAVE-Zeile `extramural`. Sonst verglichen Auswertungen ÄAVE und Stellen über verschieden geschnittene Fächer."""
    for zeile in IST_ZEILEN + PLAN_ZEILEN:
        for fach in OESG_ANALYSEKERN:
            assert teile(fach, zeile) == teile(fach, "extramural"), f"{zeile} {fach}"


def test_keine_zae_in_den_stellen():
    """ZAE sind spitalsambulant (Vorlage (Tabellenband S.239), Fußnote (5)), Sachleistungsstellen bilden den
    extramuralen Bereich ab (Tabellenband S.232) – in keiner Stellen-Zeile gehört SON/IDB zu AM."""
    for zeile in IST_ZEILEN + PLAN_ZEILEN:
        assert ZAE not in teile("AM", zeile), zeile


def test_vertrag_weist_falsches_zurueck():
    """Der Vertrag lässt nicht durch, was die ÖSG-Vorlage nicht kennt."""
    gut = pd.DataFrame(
        [{c: v for c, v in zip(SPALTEN, ["RSG 2030", "Wien", "BL", "Wien", "PLAN", 2030, "slst_gemeinsam", "AM",
                                         10.0, "AM", 8.0, 80.0])}]
    )  # fmt: skip
    pruefe(gut)
    for feld, wert, text in [
        ("Zeile_ID", "wahl", "unbekannte Werte"),  # keine Stellen-Zeile
        ("Fach", "SON/IDB", "unbekannte Werte"),  # keine Richtwert-Zeile
        ("Abschnitt", "IST", "nur im PLAN"),  # slst_* gibt es nur im PLAN
    ]:
        with pytest.raises(ValueError, match=text):
            pruefe(gut.assign(**{feld: wert}))
    # Maximalanteil bei einer Zeile, die in der Vorlage keinen hat
    eva = gut.assign(Zeile_ID="slst_eva")
    with pytest.raises(ValueError, match="haben in der ÖSG-Vorlage keinen"):
        pruefe(eva)
    pruefe(eva.assign(Max_VAEP_Stellen=None, Max_VAEP_Prozent=None))


def test_teilmengen_sind_benannt():
    """`slst_eva` ist eine Teilmenge von `slst_gemeinsam` («- davon in EVA» in der Vorlage) – wer summiert, muss das
    wissen, deshalb steht es im Vertrag und nicht nur in der Doku."""
    assert TEILMENGEN == {"slst_eva": "slst_gemeinsam"}


@pytest.fixture(scope="module")
def stellen() -> pd.DataFrame:
    return stellen_eingang()


def _zelle(stellen: pd.DataFrame, land, ebene, rid, abschnitt, zeile, fach) -> pd.Series:
    """Eine Zelle der Tabelle – der Schlüssel ist eindeutig (`stellen_eingang.SCHLUESSEL`)."""
    z = stellen[
        (stellen["Land"] == land)
        & (stellen["Ebene"] == ebene)
        & (stellen["Region_ID"] == rid)
        & (stellen["Abschnitt"] == abschnitt)
        & (stellen["Zeile_ID"] == zeile)
        & (stellen["Fach"] == fach)
    ]
    assert len(z) == 1, f"{land} {ebene} {rid} {abschnitt} {zeile} {fach}: {len(z)} Zeilen"
    return z.iloc[0]


@pytest.mark.slow
def test_jede_stelle_hat_einen_maximalanteil(stellen):
    """Keine Zeile mit Stellen > 0, für die der Maximalanteil nur einen Teil abdeckt. Käme eine dazu, bliebe der
    Anteil leer und der Lauf meldete es – dieser Test erzwingt, dass ein Mensch hinsieht."""
    offen = ohne_anteil(stellen)
    assert offen.empty, offen[["Land", "Ebene", "Region_ID", "Zeile_ID", "Fach", "Stellen"]].to_string()


@pytest.mark.slow
def test_handrechnung_ooe_kfo(stellen):
    """OÖ, PLAN, gemeinsame Sachleistungsstellen, ZMK: 480,3 gedruckt + 32 aus der Fußnote zu «ZMK*» (Anlage S.10),
    davon höchstens 480,3 × 79,1 % + 32 × 100 % vertragsärztlich. Prozentsätze werden nie gemittelt."""
    z = _zelle(stellen, "OÖ", "BL", "OÖ", "PLAN", "slst_gemeinsam", "ZMK")
    assert z["Stellen"] == pytest.approx(480.3 + 32)
    assert z["Max_VAEP_Stellen"] == pytest.approx(480.3 * 0.791 + 32 * 1.0)
    assert z["Max_VAEP_Prozent"] == pytest.approx((480.3 * 0.791 + 32) / 512.3 * 100)
    assert z["Zuschnitt"] == "ZMK + KFO (KFO nicht in der Tabelle, per Korrekturregel)"


@pytest.mark.slow
def test_tiroler_son_idb_stellen_bleiben_draussen(stellen):
    """Tirol druckt im PLAN 8,05 Sachleistungsstellen in SON/IDB (Anlage S.1, Fußnote (7): 4,8 AM + 1 KIJU +
    2,25 ORTR durch L-ZK). Sie sind spitalsambulant und gehören nicht zu AM – AM ist dort die Spalte AM allein."""
    lang = lade_matrix_long()
    m = matrix_long(lang, "Tirol", "BL")
    gedruckt = m[(m["Abschnitt"] == "PLAN") & (m["Zeile_ID"] == "slst_gemeinsam")].set_index("Fach")["Wert"]
    assert gedruckt["SON/IDB"] == pytest.approx(8.05)
    am = _zelle(stellen, "Tirol", "BL", "Tirol", "PLAN", "slst_gemeinsam", "AM")
    assert am["Stellen"] == pytest.approx(gedruckt["AM"])


@pytest.mark.slow
def test_wien_gesamtzeile_ist_die_summe_ihrer_teile(stellen):
    """Wien druckt als einziges Land eine Gesamtzeile. Dass sie `slst_gemeinsam` + die drei `slst_zus_…` ist, belegt,
    dass die PLAN-Zeilen summierbar sind – anders als die IST-Planstellen je Träger (Tabellenband S.231/232)."""
    w = stellen[(stellen["Land"] == "Wien") & (stellen["Ebene"] == "BL")]
    p = w.pivot_table(index="Fach", columns="Zeile_ID", values="Stellen")
    teile_zeilen = ["slst_gemeinsam", "slst_zus_oegk", "slst_zus_svs", "slst_zus_bvaeb"]
    assert p["slst_gesamt"].round(6).equals(p[teile_zeilen].sum(axis=1).round(6))


@pytest.fixture(scope="module")
def rundung() -> pd.Series:
    """Rundung je Rohzelle. Toleranz wie in der Pipeline: Σ Rundung der Teile + Rundung des Ganzen (checks.py) –
    die Länder drucken verschieden genau (Wien ganze Stellen, die übrigen eine Nachkommastelle)."""
    lang = lade_matrix_long()
    i = ["Land", "Ebene", "Region_ID", "Abschnitt", "Zeile_ID", "Fach"]
    return lang.assign(Region_ID=lang["Region_ID"].astype(str)).groupby(i)["Rundung"].first()


def _tol_zelle(rundung: pd.Series, land, ebene, rid, abschnitt, zeile, fach) -> float:
    """Toleranz einer zugeschnittenen Zelle: Σ Rundung der Matrixspalten, aus denen sie entsteht."""
    return sum(float(rundung.get((land, ebene, str(rid), abschnitt, zeile, s), 0.0)) for s in teile(fach, zeile))


@pytest.mark.slow
def test_vollstaendig_gegen_die_gedruckte_spalte_gesamt(stellen, rundung):
    """Nichts fällt still weg: Die Fächer des Zuschnitts (ohne die doppelt gezählten PUL und KFO) plus die Spalten
    ohne Richtwert ergeben die gedruckte Spalte «gesamt» jeder Stellen-Zeile."""
    lang = lade_matrix_long()
    s = stellen[~stellen["Fach"].isin(DOPPELT)]
    abweichungen = []
    for (land, ebene, rid), g in s.groupby(["Land", "Ebene", "Region_ID"], sort=False):
        m = matrix_long(lang, land, ebene, str(rid))
        for (abschnitt, zeile), zellen in g.groupby(["Abschnitt", "Zeile_ID"], sort=False):
            roh = m[(m["Abschnitt"] == abschnitt) & (m["Zeile_ID"] == zeile)].set_index("Fach")["Wert"]
            if "gesamt" not in roh.index or pd.isna(roh["gesamt"]):
                continue
            rest = sum(float(roh[c]) for c in OHNE_RICHTWERT if c in roh.index and pd.notna(roh[c]))
            summe = round(zellen["Stellen"].sum() + rest, 6)
            rund = m[(m["Abschnitt"] == abschnitt) & (m["Zeile_ID"] == zeile)].set_index("Fach")["Rundung"]
            tol = float(rund.drop("gesamt", errors="ignore").sum()) + float(rund.get("gesamt", 0.0)) + 1e-9
            if abs(summe - float(roh["gesamt"])) > tol:
                abweichungen.append(
                    f"{land} {ebene} {rid} {abschnitt} {zeile}: {summe} statt {roh['gesamt']} (Toleranz {tol:.2f})"
                )
    assert not abweichungen, "\n".join(abweichungen[:15])


@pytest.mark.slow
def test_versorgungsregionen_summieren_sich_zum_bundesland(stellen, rundung):
    """Je Stellen-Zeile und Fach: Σ der VR = Bundesland. Gilt für Stellen wie für ÄAVE; Prozentsätze werden dabei
    nicht summiert (sie stehen in eigenen Spalten)."""
    idx = ["Land", "Abschnitt", "Zeile_ID", "Fach"]
    bl = stellen[stellen["Ebene"] == "BL"].set_index(idx)["Stellen"]
    vr = stellen[stellen["Ebene"] == "VR"].groupby(idx)["Stellen"].sum()
    gemeinsam = bl.index.intersection(vr.index)
    # 9 Länder × bis zu 10 Stellen-Zeilen × 17 Fächer, soweit das Land die Zeile und das Fach hat
    assert len(gemeinsam) > 1000, f"zu wenige vergleichbare Zellen: {len(gemeinsam)}"
    assert set(stellen["Land"]) == set(bl.loc[gemeinsam].index.get_level_values("Land")), "ein Land fehlt"
    vr_regionen = stellen[stellen["Ebene"] == "VR"].groupby(idx)["Region_ID"].apply(list)
    abweichungen = []
    for schluessel in gemeinsam:
        land, abschnitt, zeile, fach = schluessel
        tol = _tol_zelle(rundung, land, "BL", land, abschnitt, zeile, fach) + sum(
            _tol_zelle(rundung, land, "VR", r, abschnitt, zeile, fach) for r in vr_regionen[schluessel]
        )
        d = abs(float(bl.loc[schluessel]) - float(vr.loc[schluessel]))
        if d > tol + 1e-9:
            abweichungen.append(f"{land} {abschnitt} {zeile} {fach}: BL {bl[schluessel]} ≠ Σ VR {vr[schluessel]}")
    assert not abweichungen, "\n".join(abweichungen[:15])


@pytest.mark.slow
def test_nur_matrixspalten_des_zuschnitts(stellen):
    """Jede Stellenzahl kommt aus Spalten, die der ÖSG-Zuschnitt kennt – nie aus einer Spalte ohne Richtwert."""
    genannt = {teil for text in stellen["Zuschnitt"] for teil in text.split(" (")[0].split(" + ")}
    assert genannt <= MATRIXSPALTEN, sorted(genannt - MATRIXSPALTEN)


@pytest.mark.slow
def test_stellen_csv_aktuell(stellen):
    """Frisch gerechnet = erwartete Prüfsumme der veröffentlichten Version, Zeichen für Zeichen."""
    from rsg2030.stellen import CSV_FORMAT, stellen_csv

    pfad = stellen_csv()
    pruefe_ausgabe(pfad.name, stellen.to_csv(**CSV_FORMAT), pfad)
