"""`oesg_methodik`: Vertrag des ÄAVE-Eingangs und VD-Rechnung, ohne Quelldateien.

VD = ÄAVE / Bevölkerung × 100.000
Lage = unter / im / über dem Soll-Intervall (auf der Grenze = im)
Position im Soll-Intervall = (VD − VDmin) / (VDmax − VDmin)
ÄAVE-Abstand = (VD − nächste Grenze) × Bevölkerung / 100.000, 0 im Soll-Intervall
"""

from __future__ import annotations

import conftest  # noqa: F401  (Pfade)
import pandas as pd
import pytest

from oesg_methodik import eingang as e
from oesg_methodik.dichte import aave_abstand_intervall, kennzahlen, lage_im_intervall
from oesg_methodik.richtwerte import lade_richtwerte, richtwerte_fuer_vd

RICHTWERTE = pd.DataFrame(
    [{"Fachrichtung": "IM", "VDmin": 14.4, "VDmax": 26.8}, {"Fachrichtung": "AM", "VDmin": 34.9, "VDmax": 64.8}]
)
KENNZAHLEN = ["VDmin", "VDmax", "Lage_im_Intervall", "Position_im_Intervall", "AAVE_Abstand_Intervall"]


def _zeile(**w) -> dict:
    return {
        "Datensatz": "Test",
        "Land": "X",
        "Ebene": "BL",
        "Region_ID": "X",
        "Abschnitt": "IST",
        "Jahr": 2022,
        "Zeile_ID": e.INSGESAMT,
        "Fach": "IM",
        "Basis": e.SACHLEISTUNG,
        "AAVE": 50.0,
        "Zuschnitt": "IM",
        **w,
    }


def test_kennzahlen_synthetisch():
    """Je ein Fall im, unter und über dem Soll-Intervall, von Hand gerechnet."""
    aave = pd.DataFrame([_zeile(), _zeile(Abschnitt="PLAN", Jahr=2030, AAVE=36.0), _zeile(Fach="AM", AAVE=175.0)])
    bev = pd.DataFrame(
        [
            {"Land": "X", "Ebene": "BL", "Region_ID": "X", "Abschnitt": "IST", "Jahr": 2022, "Bevoelkerung": 250_000.0},
            {
                "Land": "X",
                "Ebene": "BL",
                "Region_ID": "X",
                "Abschnitt": "PLAN",
                "Jahr": 2030,
                "Bevoelkerung": 300_000.0,
            },
        ]
    )
    k = kennzahlen(aave, bev, RICHTWERTE)
    assert k["VD"].tolist() == pytest.approx([20.0, 12.0, 70.0])
    assert k["Lage_im_Intervall"].tolist() == ["im", "unter", "über"]
    assert k["Position_im_Intervall"].tolist() == pytest.approx(
        [(20.0 - 14.4) / (26.8 - 14.4), (12.0 - 14.4) / (26.8 - 14.4), (70.0 - 34.9) / (64.8 - 34.9)]
    )
    # unter: (12 − 14,4) × 300.000 / 100.000 = −7,2 ÄAVE bis VDmin; über: (70 − 64,8) × 2,5 = +13 ÄAVE über VDmax
    assert k["AAVE_Abstand_Intervall"].tolist() == pytest.approx([0.0, -7.2, 13.0])
    assert k["Fach"].tolist() == ["IM", "IM", "AM"]  # Reihenfolge wie Eingang


def test_intervall_nur_insgesamt():
    """R10: Für Teilzeilen hat der ÖSG keinen Richtwert – VD ja, Soll-Intervall und Kennzahlen dazu nein."""
    aave = pd.DataFrame([_zeile(), _zeile(Zeile_ID="spitalsambulant", AAVE=5.0), _zeile(Zeile_ID="extramural")])
    bev = pd.DataFrame([{**{c: _zeile()[c] for c in e.REGION}, "Bevoelkerung": 250_000.0}])
    k = kennzahlen(aave, bev, RICHTWERTE)
    assert k["VD"].tolist() == pytest.approx([20.0, 2.0, 20.0])
    for spalte in KENNZAHLEN:
        assert k[spalte].notna().tolist() == [True, False, False], spalte


def test_lage_und_abstand_an_den_grenzen():
    """Auf einer Grenze liegt die VD im Soll-Intervall (Abstand 0); knapp daneben nicht. Ohne Intervall: leer."""
    vd = pd.Series([14.4, 14.39, 26.8, 26.81, 20.0, 20.0])
    vdmin = pd.Series([14.4] * 5 + [float("nan")])
    vdmax = pd.Series([26.8] * 5 + [float("nan")])
    assert lage_im_intervall(vd, vdmin, vdmax).tolist() == ["im", "unter", "im", "über", "im", None]
    abstand = aave_abstand_intervall(vd, vdmin, vdmax, pd.Series([100_000.0] * 6))
    assert abstand.iloc[:5].tolist() == pytest.approx([0.0, -0.01, 0.0, 0.01, 0.0])
    assert pd.isna(abstand.iloc[5])


def test_soll_intervall_ist_mitte_plus_minus_30_prozent():
    """METHODIK R3: Der ÖSG legt ± 30 % um einen Mittelwert 2030 (Methodenband S.19, Schritt 5) und druckt nur die
    gerundeten Grenzen (Textband S.39). Jedes Intervall passt dazu: Es gibt einen Mittelwert, aus dem beide Grenzen
    gerundet entstehen. Genau ± 30 % sind die gedruckten Grenzen aber nicht (KJP: rund ± 27 %) – deshalb setzen die
    Kennzahlen nur an VDmin und VDmax an. Schlägt an, wenn eine neue ÖSG-Fassung die Intervalle anders bildet."""
    r = richtwerte_fuer_vd(lade_richtwerte())
    assert len(r) == 17
    for _, z in r.iterrows():
        von = max((z["VDmin"] - 0.05) / 0.7, (z["VDmax"] - 0.05) / 1.3)
        bis = min((z["VDmin"] + 0.05) / 0.7, (z["VDmax"] + 0.05) / 1.3)
        assert von <= bis, (z["Fachrichtung"], von, bis)
    kjp = r.set_index("Fachrichtung").loc["KJP"]
    assert kjp["VDmin"] / ((kjp["VDmin"] + kjp["VDmax"]) / 2) - 1 == pytest.approx(-0.273, abs=0.001)
    # VD2021 ist nicht die Mitte (METHODIK R3): AM 48,7 × 0,7 = 34,1, gedruckt ist VDmin 34,9
    am = r.set_index("Fachrichtung").loc["AM"]
    assert round(am["VD2021"] * 0.7, 1) == 34.1 != am["VDmin"]


def test_kennzahlen_ohne_bevoelkerung_bricht_ab():
    with pytest.raises(ValueError, match="Keine Bevölkerung"):
        kennzahlen(pd.DataFrame([_zeile()]), pd.DataFrame(columns=[*e.REGION, "Bevoelkerung"]), RICHTWERTE)


@pytest.mark.parametrize(
    "zeile, meldung",
    [
        (_zeile(Fach="OR"), "unbekannte Werte in Fach"),
        (_zeile(Basis="inkl_Wahl"), "unbekannte Werte in Basis"),  # gibt es für RSG 2030 nicht (R1)
        (_zeile(Ebene="AT"), "unbekannte Werte in Ebene"),  # keine Österreich-Ebene (METHODIK, Österreich)
        (_zeile(AAVE=float("nan")), "leere ÄAVE"),
        (_zeile(Zeile_ID="wahl"), "unbekannte Werte in Zeile_ID"),  # Wahlärzt:innen nicht in der Dichte (R1)
        (_zeile(Zeile_ID="pve", Fach="IM"), "pve nur für"),  # PVE nur AM und KIJU (Tabellenband S.231)
    ],
)
def test_eingang_vertrag(zeile, meldung):
    with pytest.raises(ValueError, match=meldung):
        e.pruefe(pd.DataFrame([zeile]))


def test_eingang_schluessel_doppelt():
    with pytest.raises(ValueError, match="doppelt"):
        e.pruefe(pd.DataFrame([_zeile(), _zeile(AAVE=1.0)]))


def test_zuschnitt_nach_oesg():
    """R4/R5: AM + ZAE, CH + KJC + PCH, IM + PUL, ZMK + KFO; KFO nur, wo es eine eigene Spalte hat."""
    from oesg_methodik.faecher import ZAE, summe_im_zuschnitt, zuschnitt

    z = pd.Series(
        {"AM": 100.0, ZAE: 8.3, "CH": 10.0, "KJC": 0.0, "PCH": 0.0, "IM": 20.0, "PUL": 2.0, "ZMK": 30.0, "KFO": 4.0}
    )
    assert (
        summe_im_zuschnitt(z, "AM"),
        summe_im_zuschnitt(z, "CH"),
        summe_im_zuschnitt(z, "IM"),
        summe_im_zuschnitt(z, "ZMK"),
    ) == (
        108.3,
        10.0,
        22.0,
        34.0,
    )
    assert summe_im_zuschnitt(z, "KFO") == 4.0
    assert (zuschnitt(z, "AM"), zuschnitt(z, "CH"), zuschnitt(z, "ZMK")) == ("AM + ZAE", "CH", "ZMK + KFO")
    ohne = pd.Series({"AM": 100.0, ZAE: float("nan"), "ZMK": 30.0})  # Wien, Vorarlberg: KFO in ZMK
    assert summe_im_zuschnitt(ohne, "KFO") is None and summe_im_zuschnitt(ohne, "ZMK") == 30.0
    assert zuschnitt(ohne, "ZMK") == "ZMK (KFO nicht getrennt ausgewiesen)"
    assert zuschnitt(ohne, "AM") == "AM (ZAE nicht getrennt ausgewiesen)"
    # ZAE «-» bzw. 0 (Wien): nicht getrennt ausgewiesen – ob in einer Fachspalte oder gar nicht, sagt die Matrix nicht
    assert zuschnitt(pd.Series({"AM": 100.0, ZAE: 0.0}), "AM") == "AM (ZAE nicht getrennt ausgewiesen)"


def test_zae_nur_spitalsambulant():
    """R10: ZAE sind spitalsambulant (Vorlage (Tabellenband S.239), Fußnote (5)) – in extramural und pve ist AM nur die Spalte AM."""
    from oesg_methodik.faecher import ZAE, summe_im_zuschnitt, zuschnitt

    z = pd.Series({"AM": 100.0, ZAE: 8.3})
    assert (
        summe_im_zuschnitt(z, "AM", "spitalsambulant") == 108.3 and zuschnitt(z, "AM", "spitalsambulant") == "AM + ZAE"
    )
    for zeile in ("extramural", "pve"):
        assert summe_im_zuschnitt(z, "AM", zeile) == 100.0 and zuschnitt(z, "AM", zeile) == "AM"
    # Burgenland VR 11/12: AM spitalsambulant leer gedruckt, ZAE in SON/IDB → AM = 0 + ZAE
    leer = pd.Series({"AM": float("nan"), ZAE: 2.35})
    assert summe_im_zuschnitt(leer, "AM", "spitalsambulant") == 2.35
    assert summe_im_zuschnitt(pd.Series({"AM": float("nan"), ZAE: 0.0}), "AM", "spitalsambulant") is None
