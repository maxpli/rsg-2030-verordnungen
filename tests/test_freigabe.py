"""Freigabe-Mappe: Bestätigungen bleiben, solange sich der bestätigte Inhalt nicht ändert; ein abweichender Wert laut PDF
ist ein Lesefehler. Ohne Quelldateien."""

from __future__ import annotations

import pandas as pd

from rsg2030.freigabe import BLAETTER, abgleichen, lese, schreibe

ZWEITLESUNG = next(b for b in BLAETTER if b.name == "Zweitlesung")


def _zellen(werte: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Wo": "X · haupt · IST",
                "Zeile": "ÄAVE insgesamt",
                "Fach": f,
                "PDF": "x.pdf",
                "Seite": 1,
                "Roh": roh,
                "Schluessel": f"X|{f}",
                "Inhalt": roh,
            }
            for f, roh in werte.items()
        ]
    )


def test_bestaetigung_bleibt_und_verfaellt():
    neu, st = abgleichen(_zellen({"AM": "1,0", "IM": "2,0"}), None, ZWEITLESUNG)
    assert (st.gesamt, st.bestaetigt, st.neu) == (2, 0, 2)
    neu["bestaetigt"] = "ja"
    # gleicher Inhalt → Haken bleiben; IM anders gelesen → Bestätigung verfällt; KJP neu; AM bleibt
    neu2, st2 = abgleichen(_zellen({"AM": "1,0", "IM": "2,5", "KJP": "-"}), neu, ZWEITLESUNG)
    assert list(neu2["bestaetigt"]) == ["ja", "", ""]
    assert (st2.bestaetigt, st2.verfallen, st2.neu, st2.entfallen, st2.offen) == (1, 1, 1, 0, 2)


def test_anderer_wert_laut_pdf_ist_lesefehler():
    neu, _ = abgleichen(_zellen({"AM": "1,0", "IM": "2,0"}), None, ZWEITLESUNG)
    neu["bestaetigt"] = "ja"
    neu["pdf_wert"] = ["1,00", "2,1"]  # 1,00 = 1,0 (numerisch gleich) → kein Fehler; 2,1 ≠ 2,0 → Lesefehler
    _, st = abgleichen(_zellen({"AM": "1,0", "IM": "2,0"}), neu, ZWEITLESUNG)
    assert list(st.abweichend["Fach"]) == ["IM"]


def test_mappe_hin_und_zurueck(tmp_path):
    """Schreiben und Lesen verlieren nichts, was der Abgleich braucht (Schlüssel, Prüfstand, Eingaben)."""
    blaetter = {}
    for b in BLAETTER:
        df = (
            _zellen({"AM": "1,0"})
            if b.mit_pdf_wert
            else pd.DataFrame([{f: "1" for _, f, _ in b.spalten} | {"Schluessel": "k", "Inhalt": "i"}])
        )
        blaetter[b.name], _ = abgleichen(df, None, b)
        blaetter[b.name]["bestaetigt"] = "ja"
    pfad = tmp_path / "freigabe.xlsx"
    schreibe(blaetter, pfad)
    zurueck = lese(pfad)
    for b in BLAETTER:
        _, st = abgleichen(
            blaetter[b.name].drop(columns=["bestaetigt", "pdf_wert", "Anmerkung", "Pruefstand"]), zurueck[b.name], b
        )
        assert (st.bestaetigt, st.verfallen, st.neu) == (1, 0, 0), b.name


def test_blaetter_folgen_den_regeln():
    """Nur, was keine Maschine unabhängig prüfen kann (PRUEFUNG.md, «Wer prüft was»); keine Zufallsauswahl."""
    assert [b.name for b in BLAETTER] == [
        "Zweitlesung",
        "Bildseiten",
        "Spalten",
        "Zeilen",
        "Fußnoten",
        "Entscheidungen",
    ]


def test_roh_gleich():
    from rsg2030.freigabe import roh_gleich

    assert roh_gleich("2,0", "2,00") and roh_gleich("-", "–") and roh_gleich("-(7)", "-") and roh_gleich("n.v", "n.v.")
    assert not roh_gleich("1,2", "12") and not roh_gleich("-", "") and not roh_gleich("-", "n.v.")
    # leer im PDF, so wie man es einträgt: «leer» = «(leer)» = leere Zelle, aber nicht «-» (= 0)
    assert roh_gleich("leer", "") and roh_gleich("Leer", "(leer)") and not roh_gleich("leer", "-")


def test_vorlage_zeilen():
    """Beschriftungen wie in der ÖSG-Vorlage braucht kein Mensch; Platzhalter so, wie die Länder sie drucken."""
    from rsg2030.vorlage import zeile_wie_vorlage

    assert zeile_wie_vorlage("IST", "SVE spitalsambulant", "spitalsambulant")
    assert zeile_wie_vorlage("IST", "ÄAVE spitalsambulant", "spitalsambulant")
    assert zeile_wie_vorlage("PLAN", "PLAN ÄAVE insgesamt 20xx", "insgesamt")
    assert zeile_wie_vorlage("IST", "- davon in VGF (Gruppenpraxen, PVE, Ambulatorien) gesamt", "vgf")
    assert zeile_wie_vorlage(
        "PLAN", "- davon maximal als vertragsärztliche Planstellen in %", "slst_zus_svs_max_vaep_prozent"
    )
    assert not zeile_wie_vorlage("IST", "ÄAVE spitalsambulant", "insgesamt")  # andere Zeile_ID
    assert not zeile_wie_vorlage(
        "PLAN", "Umrechnungsfaktor für ÄrztInnen spitalsambulant", "umr_spitalsambulant"
    )  # Abschnitt
    assert not zeile_wie_vorlage("IST", "IST ÄAVE gesamt extramural", "insgesamt")


def test_vorlage_koepfe():
    from rsg2030.vorlage import kopf_wie_vorlage

    for kopf, fach in [
        ("AM(4)", "AM"),
        ("KJP (7)", "KJP"),
        ("ORTR3)", "ORTR"),
        ("AM(3,", "AM"),
        ("SON/IDB(5)", "SON/IDB"),
    ]:
        assert kopf_wie_vorlage(kopf, fach), kopf
    assert kopf_wie_vorlage("AM/PV", "AM") and kopf_wie_vorlage("ZMK*", "ZMK") and kopf_wie_vorlage("gesamt", "gesamt")
    assert (
        not kopf_wie_vorlage("SON", "SON/IDB")
        and not kopf_wie_vorlage("ZM", "ZMK")
        and not kopf_wie_vorlage("KIN", "KIJU")
    )


def test_fussnoten_ueberfliegen_je_land():
    """Was keine Zahl ändern kann, eine Zeile je Land; ändert sich eine Fußnote darin, ist die Zeile wieder offen."""
    from rsg2030.freigabe import fussnoten_blatt

    def fn(land, text, einordnung, rang, seite=1):
        return dict(
            Land=land,
            Ebene="BL",
            Region_ID=land,
            Seite=seite,
            Zeichen="(1)",
            Text=text,
            Einordnung=einordnung,
            Verweis="",
            Anmerkung="",
            _rang=rang,
        )

    df = pd.DataFrame(
        [
            fn("Wien", "ZMK einschließlich KFO", "betrifft Werte", 0),
            fn("Wien", "Hinweis A", "Hinweis", 2),
            fn("Wien", "Hinweis A", "Hinweis", 2, seite=2),
            fn("Wien", "davon UC", "Teilmenge", 2),
            fn("Tirol", "Hinweis A", "Hinweis", 2),
        ]
    )
    blatt = fussnoten_blatt(df)
    assert list(blatt["Laender"]) == ["Wien", "Wien", "Tirol"]
    assert blatt["Pruefen"].iloc[0].startswith("genau") and blatt["Vorkommen"].iloc[1].startswith("2 verschiedene")
    vorher = blatt.set_index("Schluessel")["Inhalt"]
    df.loc[3, "Text"] = "davon UC, zusätzlich 3 ÄAVE"
    nachher = fussnoten_blatt(df).set_index("Schluessel")["Inhalt"]
    assert (vorher != nachher).tolist() == [False, True, False]


def test_spalten_anders_als_vorlage():
    """Eine Spalte, die die Vorlage nicht hat (KFO), oder eine, die fehlt (STR), ist ein Urteil – auch wenn der Kopf
    so heißt wie seine Fachspalte."""
    from rsg2030.vorlage import SPALTEN_VORLAGE, spalten_abweichung

    assert spalten_abweichung(set(SPALTEN_VORLAGE)) == ""
    assert spalten_abweichung((set(SPALTEN_VORLAGE) - {"STR", "MKG"}) | {"KFO"}) == "zusätzlich: KFO · fehlt: MKG, STR"


def test_beschriftung_an_der_seite_mit_jahr():
    """In der Zweitlesung steht die Beschriftung wie gedruckt; Listen über alle Matrizen schreiben das Jahr als 20xx."""
    from rsg2030.freigabe import _beschriftung

    assert _beschriftung("insgesamt", "PLAN ÄAVE insgesamt 2030 (2)", mit_jahr=True) == "PLAN ÄAVE insgesamt 2030"
    assert _beschriftung("insgesamt", "PLAN ÄAVE insgesamt 2030 (2)") == "PLAN ÄAVE insgesamt 20xx"


def test_prozentzeile_nennt_ihre_stellenzeile():
    """«… in %» allein sagt nicht, ob gemeinsame, ÖGK-, SVS- oder BVAEB-Stellen gemeint sind."""
    from rsg2030.freigabe import _mit_bezug

    matrix = ("OÖ", "VR", "44", "haupt", "PLAN")
    bezug: dict[tuple[str, ...], str] = {(*matrix, "slst_zus_svs"): "zusätzliche SVS-Sachleistungsstellen"}
    text = "- davon maximal als vertragsärztliche Planstellen in %"
    assert _mit_bezug(text, (*matrix, "slst_zus_svs_max_vaep_prozent"), bezug) == (
        f"{text} – zu: «zusätzliche SVS-Sachleistungsstellen»"
    )
    assert _mit_bezug("ÄAVE spitalsambulant", (*matrix, "spitalsambulant"), bezug) == "ÄAVE spitalsambulant"
