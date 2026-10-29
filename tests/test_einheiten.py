"""Kleine, schnelle Tests ohne PDF-Zugriff."""

from __future__ import annotations

import conftest  # noqa: F401  (Pfade)
import pandas as pd
import pytest

from rsg2030.korrekturen import halbe_einheit, korrigiere
from rsg2030.matrix_extract import _GLUED_PART, kompakt, lese_zahl


@pytest.mark.parametrize(
    "raw, wert",
    [
        ("12,1", 12.1),
        ("1.604,2", 1604.2),
        ("3.739,0", 3739.0),
        ("1.288", 1288.0),
        ("99,5%", 99.5),
        ("100,00%", 100.0),
        ("x(7)", None),
        ("-", None),
        ("n.v.", None),
        ("-(8)", None),
        ("2,0(6)", 2.0),
        ("0", 0.0),
    ],
)
def test_lese_zahl(raw, wert):
    assert lese_zahl(raw) == wert


def test_geklebte_prozente():
    assert _GLUED_PART.findall("100,00%71,05%") == ["100,00%", "71,05%"]
    assert _GLUED_PART.findall("-(9)100,00%") == ["-(9)", "100,00%"]


def test_compact_label():
    assert kompakt("Ä A V E n i e d e r g e l a s se n e") == "äaveniedergelassene"
    assert kompakt("in selbständigen") == "inselbstständigen"


@pytest.mark.parametrize("roh, tol", [("12,1", 0.05), ("4,10", 0.005), ("1.288", 0.5), ("7", 0.5), ("", 0.05)])
def test_halbe_einheit(roh, tol):
    assert halbe_einheit(roh) == pytest.approx(tol)


def _mini(rows):
    base = dict(
        Land="X",
        Ebene="BL",
        Region_ID="X",
        Region_Name="",
        Block="haupt",
        Abschnitt="PLAN",
        Jahr=2030,
        Einheit="ÄAVE",
        Zeile_PDF_roh="",
        PDF="x.pdf",
        Seite=1,
    )
    return pd.DataFrame([{**base, "Zeile_ID": z, "Fach": f, "Wert": w, "Roh": r} for z, f, w, r in rows])


def _rule(**kw):
    d = dict(Land="X", Ebene="*", Region_ID="*", Block="haupt", Abschnitt="PLAN", Fach="*", Begruendung="t")
    return pd.DataFrame([{**d, **kw}])


def test_korrektur_summe_und_rundung():
    df = _mini([("spitalsambulant", "AM", 1.0, "1"), ("extramural", "AM", 2.0, "2"), ("insgesamt", "AM", None, "-")])
    out, log = korrigiere(df, _rule(Zeile_ID="insgesamt", Regel="summe:spitalsambulant+extramural"))
    z = out[(out.Zeile_ID == "insgesamt") & (out.Fach == "AM")].iloc[0]
    assert (z.Wert, z.Quelle, z.Roh, z.Rundung) == (3.0, "korrigiert", "-", 1.0)
    assert len(log) == 1


def test_korrektur_zeilensumme_wenn_leer_ueberschreibt_nicht():
    df = _mini([("p", "AM", 1.0, "1,0"), ("p", "IM", 2.0, "2,0"), ("p", "gesamt", 5.0, "5,0")])
    with pytest.raises(ValueError, match="ändert nichts"):
        korrigiere(df, _rule(Zeile_ID="p", Fach="gesamt", Regel="zeilensumme_wenn_leer"))


def test_korrektur_veraltete_regel_wirft():
    with pytest.raises(ValueError):
        korrigiere(_mini([("a", "AM", 1.0, "1")]), _rule(Land="Y", Zeile_ID="a", Regel="zeilensumme"))


@pytest.mark.parametrize("regel", ["summe", "summe:", "zeilensume", "zeilensumme:a", "umbenennen", "vr_summe:x"])
def test_korrektur_unbekannte_regel_wirft_vor_dem_aendern(regel):
    """Schreibfehler in korrekturen.csv brechen sofort ab – auch wenn die Regel keine Matrix trifft."""
    with pytest.raises(ValueError, match="Unbekannte Regel"):
        korrigiere(_mini([("a", "AM", 1.0, "1")]), _rule(Land="Y", Zeile_ID="a", Regel=regel))


def test_manuell_xlsx_roundtrip(tmp_path):
    """Text bleibt Text («12,0» behält die Nachkommastelle); als Zahl getippte Werte → österr. Format."""
    import openpyxl

    from rsg2030.manuell import ManuelleMatrix, lese_manuell, schreibe_manuell

    m = ManuelleMatrix("Test BL", "Test", "BL", "Test", "", "test.pdf", 1)
    df = pd.DataFrame(
        [
            ["IST", "2022", "haupt", "insgesamt", "ÄAVE insgesamt", "12,0", "-", None, "n.v.", "Q"],
            ["PLAN", "2030", "haupt", "insgesamt", "ÄAVE insgesamt", None, None, None, None, "Q"],
        ],
        columns=["Abschnitt", "Jahr", "Block", "Zeile_ID", "Zeile", "AM", "AN", "IM", "gesamt", "Quelle"],
        dtype=object,
    )
    path = tmp_path / "manuell.xlsx"
    schreibe_manuell({m.blatt: df}, path)

    wb = openpyxl.load_workbook(path)
    wb[m.blatt]["H3"] = 9.2  # IM, PLAN: in Excel als Zahl eingegeben
    wb.save(path)

    back = lese_manuell(m, path)
    assert back is not None
    assert back.loc[0, ["AM", "AN", "IM", "gesamt"]].tolist() == ["12,0", "-", None, "n.v."]
    assert back.loc[1, "IM"] == "9,2"


def test_kopfzeile_mit_verklebtem_gesamt():
    """Bgld VR 12: «SON/IDB(5)gesamt» ohne Leerzeichen – Kopfzeile muss trotzdem erkannt werden."""
    from rsg2030.matrix_extract import _kopfspalten, _PdfZeile

    faecher = ["AM(4)", "AN", "KIJU", "CH", "IM", "GGH", "NEU", "PSY", "DER", "AU", "HNO", "SON/IDB(5)gesamt"]
    words = [{"text": t, "x0": 100 + 30 * i, "x1": 120 + 30 * i, "top": 116} for i, t in enumerate(faecher)]
    cols = _kopfspalten(_PdfZeile(116, words))
    assert cols is not None and [c for c, _, _ in cols][-2:] == ["SON/IDB", "gesamt"]
    assert [t for _, _, t in cols][-2:] == ["SON/IDB(5)", "gesamt"]  # Text im PDF, für die Freigabe
    assert cols[-2][1] < cols[-1][1]


@pytest.mark.parametrize(
    "a, b, gleich",
    [
        ("12,1", "12,1", True),
        ("2,0(6)", "2,0", True),
        ("100%", "100", True),
        ("-", "-", True),
        ("x(7)", "x", True),
        ("n.v.", "-", False),
        ("0,0", "-", False),
        ("12,1", "12,2", False),
        ("", "-", False),
    ],
)
def test_roh_gleich(a, b, gleich):
    from rsg2030.freigabe import roh_gleich

    assert roh_gleich(a, b) is gleich


def _slst(region: str, ebene: str, stellen: str, pct: str) -> list[dict]:
    from rsg2030.korrekturen import halbe_einheit
    from rsg2030.matrix_extract import lese_zahl

    base = {"Land": "X", "Ebene": ebene, "Region_ID": region, "Block": "haupt", "Abschnitt": "PLAN", "Fach": "IM"}
    return [
        {**base, "Zeile_ID": z, "Einheit": e, "Roh": r, "Wert": lese_zahl(r), "Rundung": halbe_einheit(r)}
        for z, e, r in (
            ("slst_gemeinsam", "Stellen", stellen),
            ("slst_gemeinsam_max_vaep_prozent", "Prozent", pct),
        )
    ]


@pytest.mark.parametrize("vr2_pct, status", [("50", "ok"), ("100", "abweichung")])
def test_prozent_gewichtet(vr2_pct, status):
    """BL 75 % = (10 × 100 % + 10 × 50 %) / 20; ein falsch gelesener VR-Wert (100 statt 50) fällt auf."""
    from rsg2030.checks import pruefe_prozent_gewichtet

    long = pd.DataFrame(_slst("X", "BL", "20", "75") + _slst("1", "VR", "10", "100") + _slst("2", "VR", "10", vr2_pct))
    (r,) = pruefe_prozent_gewichtet(long, vollstaendig={"X"})
    assert r["Status"] == status and r["Soll"] == pytest.approx(75 if status == "ok" else 100)


def _leer_df(rows, block="haupt"):
    df = _mini(rows)
    return df.assign(Block=block, Einheit="ÄAVE")


def test_leere_summenzelle_gesamt_und_insgesamt():
    """gesamt leer bei befüllter Zeile und insgesamt leer bei befüllten Teilen → Befund; nur «-» (0) → kein Befund."""
    from rsg2030.checks import pruefe_leere_summenzelle

    df = _leer_df(
        [
            ("spitalsambulant", "AM", 1.0, "1,0"),
            ("spitalsambulant", "gesamt", 1.0, "1,0"),
            ("extramural", "AM", 2.0, "2,0"),
            ("extramural", "gesamt", 2.0, "2,0"),
            ("pve", "AM", 0.5, "0,5"),
            ("insgesamt", "AM", None, ""),
            ("ist_null", "AM", 0.0, "-"),
        ]
    )
    befunde = {(r["Zeile_ID"], r["Fach"]) for r in pruefe_leere_summenzelle(df)}
    assert befunde == {("pve", "gesamt"), ("insgesamt", "AM"), ("insgesamt", "gesamt")}


def test_leere_summenzelle_eine_teilzeile_genuegt():
    """insgesamt «n.v.», obwohl nur spitalsambulant einen Wert hat (extramural «n.v.») → Befund."""
    from rsg2030.checks import pruefe_leere_summenzelle

    df = _leer_df(
        [
            ("spitalsambulant", "SON/IDB", 8.3, "8,3"),
            ("extramural", "SON/IDB", None, "n.v."),
            ("extramural", "AM", 2.0, "2,0"),
            ("insgesamt", "SON/IDB", None, "n.v."),
            ("insgesamt", "AM", 2.0, "2,0"),
        ]
    )
    assert {(r["Zeile_ID"], r["Fach"]) for r in pruefe_leere_summenzelle(df)} == {("insgesamt", "SON/IDB")}


def test_leere_summenzelle_sve_block_ohne_insgesamt():
    """SVE-Planung: im Block «haupt» fehlt insgesamt bewusst, wenn es einen Äquivalente-Block gibt."""
    from rsg2030.checks import pruefe_leere_summenzelle

    teile = [("spitalsambulant", "AM", 1.0, "1,0"), ("extramural", "AM", 2.0, "2,0")]
    assert pruefe_leere_summenzelle(_leer_df(teile))  # ohne Äquivalente-Block: insgesamt fehlt
    beide = pd.concat([_leer_df(teile), _leer_df(teile + [("insgesamt", "AM", 3.0, "3,0")], "aequivalent")])
    assert pruefe_leere_summenzelle(beide) == []


def test_zeile_zuordnen():
    """Eine nur vorläufig erkannte Zeile (Wien VR 92) darf nach den Korrekturen nicht übrig bleiben."""
    from rsg2030.checks import pruefe_zuordnen

    df = _leer_df([("insgesamt_als_extramural", "AM", 1.0, "1,0"), ("insgesamt_als_extramural", "gesamt", 3.0, "3")])
    (r,) = pruefe_zuordnen(df)
    assert r["Status"] == "abweichung" and r["Fach"] == "gesamt" and r["Wert"] == 3.0
    assert pruefe_zuordnen(df.assign(Zeile_ID="insgesamt")) == []


def test_anzahl_exakt_ohne_rundung():
    from rsg2030.korrekturen import rundung_je_zelle

    df = _mini([("a", "AM", 7.0, "7"), ("b", "AM", 7.0, "7")]).assign(Einheit=["Anzahl", "Stellen"])
    assert rundung_je_zelle(df).tolist() == [0.0, 0.5]


def test_korrektur_braucht_rohbefund():
    from rsg2030.korrekturen import pruefe_befunde

    log = pd.DataFrame(
        [
            {
                "Regel_Nr": 1,
                "Land": "X",
                "Ebene": "VR",
                "Region_ID": "1",
                "Block": "haupt",
                "Abschnitt": "PLAN",
                "Zeile_ID": "insgesamt",
                "Fach": "AM",
                "Regel": "summe:a+b",
                "Befund": "leere_summenzelle",
            }
        ]
    )
    befund = {
        "Check": "leere_summenzelle",
        "Land": "X",
        "Region_ID": "1",
        "Block": "haupt",
        "Abschnitt": "PLAN",
        "Zeile_ID": "insgesamt",
        "Fach": "AM",
        "Status": "abweichung",
    }
    assert pruefe_befunde(log, pd.DataFrame([befund])) == []
    assert pruefe_befunde(log, pd.DataFrame([{**befund, "Fach": "IM"}]))  # anderer Befund → Fehler
    vr_bl = {**befund, "Check": "vr_summe_gleich_bl", "Region_ID": "X"}  # Σ VR = BL gilt für alle VR
    assert pruefe_befunde(log.assign(Befund="vr_summe_gleich_bl"), pd.DataFrame([vr_bl])) == []
    # «Folge» darf sich auf den Befund einer anderen Matrix desselben Landes stützen (BL = Summe korrigierter VR)
    bl = log.assign(Ebene="BL", Region_ID="X")
    assert pruefe_befunde(bl, pd.DataFrame([befund]))
    assert pruefe_befunde(bl.assign(Art="Folge"), pd.DataFrame([befund])) == []


def test_prozent_befund_auf_bl_ebene_genuegt_fuer_vr_korrektur():
    """prozent_gewichtet rechnet das BL-% aus den VR: Die Korrektur eines VR-% stützt sich auf den BL-Befund."""
    from rsg2030.korrekturen import pruefe_befunde

    log = pd.DataFrame(
        [
            {
                "Regel_Nr": 1,
                "Land": "X",
                "Ebene": "VR",
                "Region_ID": "1",
                "Block": "haupt",
                "Abschnitt": "PLAN",
                "Zeile_ID": "slst_zus_svs_max_vaep_prozent",
                "Fach": "IM",
                "Regel": "wert:100",
                "Befund": "prozent_gewichtet",
            }
        ]
    )
    befund = {
        "Check": "prozent_gewichtet",
        "Land": "X",
        "Region_ID": "X",
        "Block": "haupt",
        "Abschnitt": "PLAN",
        "Zeile_ID": "slst_zus_svs_max_vaep_prozent",
        "Fach": "IM",
        "Status": "nicht_pruefbar",
    }
    assert pruefe_befunde(log, pd.DataFrame([befund])) == []


def test_fussnote_ohne_befund_nur_mit_seite_und_text():
    from rsg2030.korrekturen import pruefe_befunde

    zeile = {
        "Regel_Nr": 1,
        "Land": "X",
        "Ebene": "BL",
        "Region_ID": "X",
        "Block": "haupt",
        "Abschnitt": "IST",
        "Zeile_ID": "insgesamt",
        "Fach": "KFO",
        "Regel": "zusatz:1.5",
        "Art": "Fußnote",
        "Befund": "fussnote",
    }
    keine = pd.DataFrame(columns=["Check", "Land", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach", "Status"])
    ok = pd.DataFrame([{**zeile, "Begruendung": "PDF S.10, Fußnote zu «ZMK*»: zusätzlich KFO 1,5 ÄAVE"}])
    assert pruefe_befunde(ok, keine) == []
    assert pruefe_befunde(ok.assign(Begruendung="Fußnote: zusätzlich KFO"), keine)  # ohne Seite → Fehler


def test_zusatz_legt_fach_an_und_erhoeht_gesamt():
    from rsg2030.korrekturen import REGEL_SPALTEN, korrigiere

    long = _mini(
        [
            ("insgesamt", "ZMK", 10.0, "10,0"),
            ("insgesamt", "gesamt", 10.0, "10,0"),
            ("niedergelassen", "ZMK", 8.0, "8,0"),
            ("niedergelassen", "gesamt", 8.0, "8,0"),
        ]
    )
    regel = pd.DataFrame(
        [
            dict(
                zip(
                    REGEL_SPALTEN,
                    [
                        *[long.iloc[0][c] for c in ("Land", "Ebene", "Region_ID", "Block")],
                        "*",
                        "insgesamt+niedergelassen+extramural",
                        "KFO",
                        "zusatz:1.5",
                        "Fußnote",
                        "fussnote",
                        "PDF S.1, Fußnote",
                    ],
                )
            )
        ]
    )
    out, log = korrigiere(long, regel)
    w = out.set_index(["Zeile_ID", "Fach"])["Wert"]
    assert w[("insgesamt", "KFO")] == 1.5 and w[("insgesamt", "gesamt")] == 11.5
    assert w[("niedergelassen", "KFO")] == 1.5 and w[("niedergelassen", "gesamt")] == 9.5
    assert len(log) == 4  # 2 neue KFO-Zellen + 2 gesamt; fehlende Zeile extramural übergangen


def test_wert_fuellt_leere_zelle_an_ihrer_stelle():
    """wert:x legt die fehlende Zelle zwischen ihre Nachbarn (Reihenfolge der Fachspalten) und lässt gesamt stehen."""
    long = _mini(
        [
            ("slst", "AM", 2.5, "2,5"),
            ("slst", "IM", 1.0, "1,0"),
            ("slst", "ORTR", 1.0, "1,0"),
            ("slst_max_vaep_prozent", "AM", 100.0, "100,0"),
            ("slst_max_vaep_prozent", "ORTR", 100.0, "100,0"),
            ("slst_max_vaep_prozent", "gesamt", None, ""),
        ]
    ).assign(Einheit="Prozent")
    out, log = korrigiere(long, _rule(Zeile_ID="slst_max_vaep_prozent", Fach="IM", Regel="wert:100"))
    z = out[out.Zeile_ID == "slst_max_vaep_prozent"]
    assert list(z.Fach) == ["AM", "IM", "ORTR", "gesamt"]
    im = z[z.Fach == "IM"].iloc[0]
    assert (im.Wert, im.Roh, im.Quelle, im.Regel) == (100.0, "", "korrigiert", "wert:100")
    assert pd.isna(z[z.Fach == "gesamt"].Wert.iloc[0]) and len(log) == 1
    with pytest.raises(ValueError, match="hat schon einen Wert"):
        korrigiere(long, _rule(Zeile_ID="slst_max_vaep_prozent", Fach="AM", Regel="wert:50"))


def test_prozent_strich_unter_stellen_ist_null():
    """«-» in der %-Zeile: unter Stellen > 0 → 0 %; ohne Stellen und in «gesamt» → leer."""
    from rsg2030.matrix_extract import prozent_strich_null

    long = _mini(
        [
            ("slst_gemeinsam", "KJP", 5.0, "5"),
            ("slst_gemeinsam", "CH", 0.0, "-"),
            ("slst_gemeinsam", "gesamt", 5.0, "5"),
            ("slst_gemeinsam_max_vaep_prozent", "KJP", None, "-"),
            ("slst_gemeinsam_max_vaep_prozent", "CH", None, "-"),
            ("slst_gemeinsam_max_vaep_prozent", "gesamt", None, "-"),
        ]
    )
    w = prozent_strich_null(long).set_index(["Zeile_ID", "Fach"])["Wert"]
    assert w[("slst_gemeinsam_max_vaep_prozent", "KJP")] == 0.0
    assert pd.isna(w[("slst_gemeinsam_max_vaep_prozent", "CH")])
    assert pd.isna(w[("slst_gemeinsam_max_vaep_prozent", "gesamt")])


@pytest.mark.parametrize("gesamt, status", [("95", "ok"), ("0", "abweichung")])
def test_prozent_gesamt_waagrecht(gesamt, status):
    """gesamt-% = mit den Stellen gewichtetes Mittel der Fach-%: 3 × 100 % + 1 × 80 % → 95 %; eine «0» fällt auf."""
    from rsg2030.checks import pruefe_prozent_gesamt

    long = _mini(
        [
            ("slst", "AM", 3.0, "3"),
            ("slst", "IM", 1.0, "1"),
            ("slst", "gesamt", 4.0, "4"),
            ("slst_max_vaep_prozent", "AM", 100.0, "100"),
            ("slst_max_vaep_prozent", "IM", 80.0, "80"),
            ("slst_max_vaep_prozent", "gesamt", float(gesamt), gesamt),
        ]
    )
    (r,) = pruefe_prozent_gesamt(long)
    assert r["Status"] == status and r["Soll"] == pytest.approx(95)


def test_prozent_bl_fehlt_bei_stellen_nicht_pruefbar():
    """Fehlt das BL-% bei Stellen > 0 (Kärnten S.97), wird das gemeldet – nicht still übersprungen."""
    from rsg2030.checks import pruefe_prozent_gewichtet

    def zeilen(ebene, region, stellen, pct):
        z = [("slst_zus_svs", "AM", stellen, "x")] + (
            [("slst_zus_svs_max_vaep_prozent", "AM", pct, "x")] if pct else []
        )
        return _mini(z).assign(Ebene=ebene, Region_ID=region)

    long = pd.concat([zeilen("BL", "X", 10.0, None), zeilen("VR", "1", 5.0, 100.0), zeilen("VR", "2", 5.0, 100.0)])
    (r,) = pruefe_prozent_gewichtet(long, vollstaendig={"X"})
    assert r["Status"] == "nicht_pruefbar" and r["Detail"] == "% fehlt bei Stellen > 0: BL"
    # fehlt das % auch in der VR (OÖ URO), steht in diesem Fach gar kein % – trotzdem gemeldet
    uro = pd.concat([zeilen("BL", "X", 1.5, None), zeilen("VR", "1", 1.5, None)]).assign(Fach="URO")
    (r,) = [x for x in pruefe_prozent_gewichtet(pd.concat([long, uro]), vollstaendig={"X"}) if x["Fach"] == "URO"]
    assert r["Status"] == "nicht_pruefbar" and r["Detail"] == "% fehlt bei Stellen > 0: BL, VR 1"


def test_gesamt_prozent_abgeleitet_nur_aus_vollstaendiger_zeile():
    """Leeres gesamt-% («-») = mit den Stellen gewichtetes Mittel; fehlt ein Fach-%, bleibt es leer. Die Prüfung
    prozent_gesamt rechnet abgeleitete Werte nicht nach (es wäre dieselbe Rechnung)."""
    from rsg2030.ableitungen import leite_prozent_gesamt_ab
    from rsg2030.checks import pruefe_prozent_gesamt

    def matrix(region, im_pct):
        return _mini(
            [
                ("slst", "AM", 3.0, "3"),
                ("slst", "IM", 1.0, "1"),
                ("slst_max_vaep_prozent", "AM", 100.0, "100"),
                *([("slst_max_vaep_prozent", "IM", im_pct, str(int(im_pct)))] if im_pct is not None else []),
                ("slst_max_vaep_prozent", "gesamt", None, "-"),
            ]
        ).assign(Region_ID=region, Quelle="PDF")

    out = leite_prozent_gesamt_ab(pd.concat([matrix("X", 80.0), matrix("Y", None)]))
    ges = out[(out.Zeile_ID == "slst_max_vaep_prozent") & (out.Fach == "gesamt")].set_index("Region_ID")
    assert (ges.at["X", "Wert"], ges.at["X", "Roh"], ges.at["X", "Quelle"]) == (95.0, "-", "abgeleitet")
    assert pd.isna(ges.at["Y", "Wert"])
    assert pruefe_prozent_gesamt(out[out.Region_ID == "X"]) == []


def test_einheit_sve_laut_beschriftung():
    """«SVE spitalsambulant» ist in SVE gezählt, nicht in ÄAVE – entschieden an der Beschriftung, nicht am Land."""
    from rsg2030.matrix_extract import einheit_laut_beschriftung

    assert einheit_laut_beschriftung("ÄAVE", "SVE spitalsambulant") == "SVE"
    assert einheit_laut_beschriftung("ÄAVE", "ÄAVE-Ä spitalsambulant") == "ÄAVE"
    assert einheit_laut_beschriftung("Stellen", "SVS-Sachleistungsstellen") == "Stellen"


def test_nicht_pruefbar_braucht_grund():
    """Eine nicht prüfbare Zelle wird wie eine Abweichung erst mit Eintrag in bekannte_abweichungen.csv «bekannt»."""
    from rsg2030.checks import markiere_bekannte

    zeile = dict(Check="prozent_gewichtet", Land="X", Region_ID="X", Block="haupt", Abschnitt="PLAN", Fach="gesamt")
    checks = pd.DataFrame(
        [
            {**zeile, "Zeile_ID": "a_max_vaep_prozent", "Status": "nicht_pruefbar"},
            {**zeile, "Zeile_ID": "b_max_vaep_prozent", "Status": "nicht_pruefbar"},
        ]
    )
    known = pd.DataFrame([{**zeile, "Zeile_ID": "a_max_vaep_prozent", "Grund": "nur in der BL-Matrix"}])
    assert list(markiere_bekannte(checks, known)["Status"]) == ["bekannt", "nicht_pruefbar"]


def _ist(rows, **kw):
    df = _mini(rows).assign(Abschnitt="IST", Jahr=2023, Quelle="PDF", **kw)
    return df.assign(Rundung=[halbe_einheit(r) if r not in ("", "-") else 0.0 for r in df["Roh"]])


def test_ableitung_extramural():
    """IST extramural = niedergelassen + selbst. Amb. + Kassenamb.; leere Teile zählen nicht, direkt hinter den Teilen."""
    from rsg2030.ableitungen import leite_ab

    df = _ist(
        [
            ("spitalsambulant", "AM", 1.0, "1,0"),
            ("niedergelassen", "AM", 10.0, "10,0"),
            ("niedergelassen", "IM", 4.0, "4,0"),
            ("selbst_amb", "AM", 0.0, "-"),
            ("selbst_amb", "IM", None, "n.v."),
            ("kassen_amb", "AM", 2.5, "2,5"),
            ("kassen_amb", "IM", None, ""),
            ("insgesamt", "AM", 13.5, "13,5"),
        ]
    )
    out = leite_ab(df)
    neu = out[out["Quelle"] == "abgeleitet"]
    assert dict(zip(neu["Fach"], neu["Wert"])) == {"AM": 12.5, "IM": 4.0}
    assert (neu["Zeile_ID"] == "extramural").all() and (neu["Roh"] == "").all()
    assert neu["Rundung"].tolist() == [0.1, 0.05]  # Summe der Rundungen der Teile mit Wert
    assert list(out["Zeile_ID"]).index("extramural") == 7  # hinter kassen_amb, vor insgesamt
    assert len(leite_ab(out)) == len(out)  # Zeile vorhanden → nichts mehr abzuleiten


def test_ableitung_nicht_wo_pdf_die_zeile_hat():
    from rsg2030.ableitungen import leite_ab

    df = _ist(
        [
            ("niedergelassen", "AM", 10.0, "10,0"),
            ("selbst_amb", "AM", 1.0, "1,0"),
            ("kassen_amb", "AM", 2.0, "2,0"),
            ("extramural", "AM", 13.0, "13,0"),
        ]
    )
    assert leite_ab(df).equals(df.reset_index(drop=True))


@pytest.mark.parametrize("gesamt, status", [("13,0", "ok"), ("15,0", "abweichung")])
def test_pruefung_extramural(gesamt, status):
    from rsg2030.checks import pruefe_summenzeilen

    df = _ist(
        [
            ("niedergelassen", "AM", 10.0, "10,0"),
            ("selbst_amb", "AM", 1.0, "1,0"),
            ("kassen_amb", "AM", 2.0, "2,0"),
            ("extramural", "AM", float(gesamt.replace(",", ".")), gesamt),
        ]
    )
    (r,) = pruefe_summenzeilen(df)
    assert (r["Check"], r["Status"]) == ("teile_extramural", status)


@pytest.mark.parametrize("faktor, status", [("2,50", "ok"), ("2,80", "abweichung")])
def test_pruefung_faktor_aequivalente(faktor, status):
    """SVE 4,0 × Faktor = ÄAVE-Ä 10,0; Toleranz aus den Rundungen aller drei Werte."""
    from rsg2030.checks import pruefe_faktor

    haupt = _ist([("spitalsambulant", "AM", 4.0, "4,0")])
    aeq = _ist(
        [
            ("spitalsambulant", "AM", 10.0, "10,0"),
            ("umr_spitalsambulant", "AM", float(faktor.replace(",", ".")), faktor),
        ],
        Block="aequivalent",
    )
    (r,) = pruefe_faktor(pd.concat([haupt, aeq], ignore_index=True))
    assert (r["Check"], r["Status"]) == ("faktor_aequivalente", status)


def test_faktor_ohne_faktor_gleich_in_beiden_bloecken():
    """ÄAVE-Zeilen ohne Faktor («-»): ÄAVE-Ä = haupt (Faktor 1), auch «gesamt»; fehlt der Wert in einem Block, fällt es
    auf (Kärnten VR 22 KIJU). SVE ohne Faktor wird nicht umgerechnet und bleibt ungeprüft (RAD: kein Faktor laut Vorlage)."""
    from rsg2030.checks import pruefe_faktor

    haupt = _ist(
        [
            ("niedergelassen", "AM", 9.4, "9,4"),
            ("niedergelassen", "KIJU", 6.3, "6,3"),
            ("niedergelassen", "gesamt", 15.7, "15,7"),
            ("spitalsambulant", "RAD", 22.0, "22,0"),
        ]
    )
    haupt.loc[haupt["Zeile_ID"] == "spitalsambulant", "Einheit"] = "SVE"
    aeq = _ist(
        [
            ("niedergelassen", "AM", 9.4, "9,4"),
            ("niedergelassen", "gesamt", 9.4, "9,4"),
            ("spitalsambulant", "RAD", None, "n.v."),
        ],
        Block="aequivalent",
    )
    status = {r["Fach"]: r["Status"] for r in pruefe_faktor(pd.concat([haupt, aeq], ignore_index=True))}
    assert status == {"AM": "ok", "KIJU": "abweichung", "gesamt": "abweichung"}


def _faktor_matrix(ebene, region, sve, faktor, aeq, abschnitt="IST"):
    """SVE spitalsambulant (Block haupt) und ÄAVE-Ä in `abschnitt`, der Faktor steht im IST."""
    haupt = _ist([("spitalsambulant", "CH", sve, "x")]).assign(Einheit="SVE", Abschnitt=abschnitt)
    a = _ist([("spitalsambulant", "CH", aeq, "x")], Block="aequivalent").assign(Abschnitt=abschnitt)
    f = _ist([("umr_spitalsambulant", "CH", faktor, "x")], Block="aequivalent")
    return pd.concat([haupt, a, f]).assign(Ebene=ebene, Region_ID=region, Rundung=0.005)


def test_faktor_bl_ist_summe_der_regionen():
    """Haben alle Regionen eigene Faktoren, wird das BL außerhalb des Abschnitts seines Faktors nicht mit dem BL-Faktor
    gerechnet (BL = Σ VR umgerechnet; Kärnten PLAN CH: 10,2 × 3,06 + 4,9 × 1,81 = 40,04 statt 15,1 × 2,67 = 40,3)."""
    from rsg2030.checks import pruefe_faktor

    long = pd.concat(
        [
            _faktor_matrix("BL", "X", 15.1, 2.67, 40.04, "PLAN"),
            _faktor_matrix("VR", "1", 10.2, 3.06, 31.21, "PLAN"),
            _faktor_matrix("VR", "2", 4.9, 1.81, 8.87, "PLAN"),
        ]
    )
    assert {(r["Ebene"], r["Status"]) for r in pruefe_faktor(long)} == {("VR", "ok")}


@pytest.mark.parametrize("bl_faktor, status", [(2.67, "ok"), (2.80, "abweichung")])
def test_faktor_bl_in_seinem_abschnitt(bl_faktor, status):
    """Im Abschnitt, in dem der BL-Faktor steht, ist er das Verhältnis der Landeswerte (Tabellenband S.234) – dort wird
    das BL auch dann mit ihm geprüft, wenn alle Regionen eigene Faktoren haben (13,0 × 2,67 = 34,71)."""
    from rsg2030.checks import pruefe_faktor

    long = pd.concat(
        [
            _faktor_matrix("BL", "X", 13.0, bl_faktor, 34.71),
            _faktor_matrix("VR", "1", 8.0, 3.06, 24.48),
            _faktor_matrix("VR", "2", 5.0, 2.05, 10.25),
        ]
    )
    bl = [r["Status"] for r in pruefe_faktor(long) if r["Ebene"] == "BL"]
    assert bl == [status]


def test_plus_addiert_auch_zu_vorhandenem_wert():
    """plus:6.3 – leere Zelle wird 6,3, vorhandene 4,7 wird 11,0; «gesamt» beider Zeilen + 6,3."""
    long = _mini(
        [
            ("niedergelassen", "AM", 9.4, "9,4"),
            ("niedergelassen", "gesamt", 9.4, "9,4"),
            ("insgesamt", "KIJU", 4.7, "4,7"),
            ("insgesamt", "gesamt", 14.1, "14,1"),
        ]
    )
    out, log = korrigiere(long, _rule(Zeile_ID="niedergelassen+insgesamt", Fach="KIJU", Regel="plus:6.3"))
    w = out.set_index(["Zeile_ID", "Fach"])["Wert"]
    assert w[("niedergelassen", "KIJU")] == pytest.approx(6.3) and w[("niedergelassen", "gesamt")] == pytest.approx(
        15.7
    )
    assert w[("insgesamt", "KIJU")] == pytest.approx(11.0) and w[("insgesamt", "gesamt")] == pytest.approx(20.4)
    assert len(log) == 4


def test_unbekannte_spalte_in_kopfzeile():
    """Ein Spaltenkopf, den specs.py nicht kennt, fällt auf; Fußnotenzeichen («AM (3, 13)», «*») nicht."""
    from rsg2030.matrix_extract import _kopfspalten, _PdfZeile, _unbekannte_koepfe

    texte = [
        "IST",
        "AM",
        "(3,",
        "13)",
        "AN",
        "KIJU",
        "KJP",
        "CH",
        "XYZ",
        "IM",
        "GGH",
        "NEU",
        "PSY",
        "*",
        "DER",
        "gesamt",
    ]
    zeile = _PdfZeile(0, [{"text": t, "x0": 10.0 * i, "x1": 10.0 * i + 8, "top": 0} for i, t in enumerate(texte)])
    cols = _kopfspalten(zeile)
    assert cols is not None
    assert _unbekannte_koepfe(zeile, cols) == ["XYZ"]
