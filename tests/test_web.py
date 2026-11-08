"""Webseite (docs/WEB.md, «Wer prüft was»): Kacheln, Fächer, Vorbehalte, Farben und data.json gegen die Tabelle.

Die schnellen Tests brauchen keine Quelldateien. Der langsame rechnet die Tabelle Versorgungsdichte frisch und
vergleicht jede Zelle von data.json mit ihr.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pandas as pd
import pytest
from conftest import ROOT

from oesg_methodik import LAND_KURZ
from oesg_methodik.bevoelkerung import lade_regionen
from oesg_methodik.faecher import ZAE, ZAE_QUELLE, ZUSCHNITT
from oesg_methodik.richtwerte import lade_richtwerte
from rsg2030.analyse_eingang import lade_matrix_long
from rsg2030.darstellung import KEIN_WERT, VORBEHALTE, Zelle, platzhalter, satz, vorbehalte
from rsg2030.korrekturen import REGEL_SPALTEN, lade_regeln
from rsg2030.quellen import OGD_HOST
from rsg2030.schema import matrix_long
from rsg2030.web import WERT, baue_daten

WEB = ROOT / "web"
META = {"datei": "test.csv", "version": "test", "sha256": "0" * 64, "commit": "0" * 40, "repo": "https://example.org"}


def kacheln() -> pd.DataFrame:
    return pd.read_csv(WEB / "kacheln.csv", dtype=str)


def faecher() -> pd.DataFrame:
    return pd.read_csv(WEB / "faecher.csv", dtype=str)


# --- Kacheln und Fächer ---------------------------------------------------------------------------------------------


def test_kacheln_genau_die_regionen_der_oesg_gliederung():
    reg, k = lade_regionen(), kacheln()
    assert set(k.loc[k["Ebene"] == "VR", "Region_ID"]) == set(reg["VR"].astype(str))
    assert set(k.loc[k["Ebene"] == "BL", "Region_ID"]) == {LAND_KURZ.get(b, b) for b in reg["Bundesland"]}
    assert not k.duplicated(["Ebene", "Region_ID"]).any(), "Region mit zwei Kacheln"
    assert not k.duplicated(["Ebene", "Spalte", "Zeile"]).any(), "zwei Kacheln auf demselben Feld"
    vr = k[k["Ebene"] == "VR"]
    assert (vr["Beschriftung"] == vr["Region_ID"]).all(), "VR-Kacheln tragen die Nummer der Region"


def test_faecher_genau_die_richtwertzeilen_mit_soll_intervall():
    rw = lade_richtwerte()
    mit_intervall = set(rw.loc[rw["VDmin"].notna() & rw["VDmax"].notna(), "Fachrichtung"])
    f = faecher()
    assert list(f["Fach"]) == list(dict.fromkeys(f["Fach"])), "Fach doppelt in web/faecher.csv"
    assert set(f["Fach"]) == mit_intervall
    assert f["Name"].notna().all()


def test_teil_von_wie_im_oesg_zuschnitt():
    """«Teil von» in web/faecher.csv = Unterzeile laut Richtwerttabelle: PUL in IM, KFO in ZMK (METHODIK R4)."""
    f = faecher().dropna(subset=["Teil_von"])
    assert dict(zip(f["Fach"], f["Teil_von"])) == {"PUL": "IM", "KFO": "ZMK"}
    for fach, teil_von in zip(f["Fach"], f["Teil_von"]):
        assert fach in ZUSCHNITT[teil_von], f"{fach} steckt laut ZUSCHNITT nicht in {teil_von}"


# --- Vorbehalte -----------------------------------------------------------------------------------------------------


def fallstricke_in_daten_md() -> set[int]:
    text = (ROOT / "docs" / "DATEN.md").read_text(encoding="utf-8")
    abschnitt = text.split("\n## Fallstricke", 1)[1].split("\n## ", 1)[0]
    return {int(n) for n in re.findall(r"^(\d+)\. \*\*", abschnitt, flags=re.M)}


def test_jeder_vorbehalt_nennt_einen_fallstrick_den_es_gibt():
    """Jeder Vorbehalt verweist auf einen Fallstrick, den docs/DATEN.md wirklich hat."""
    vorhanden = fallstricke_in_daten_md()
    for kennung, v in VORBEHALTE.items():
        assert v.fallstrick in vorhanden, f"Vorbehalt «{kennung}» nennt Fallstrick {v.fallstrick}, den es nicht gibt"


def test_die_texte_stehen_nur_in_python():
    """Die Texte dürfen nicht noch einmal in app.js stehen – sonst laufen Dashboard und Seiten auseinander."""
    js = (WEB / "app.js").read_text(encoding="utf-8")
    for kennung, v in VORBEHALTE.items():
        anfang = v.text.split("<b>", 1)[-1].split("</b>", 1)[0][:20]
        assert anfang not in js, f"Vorbehalt «{kennung}» steht auch in app.js"
    assert "Bis zur Untergrenze fehlen" not in js, "der Satz in Worten steht auch in app.js"


def test_jeder_vorbehalt_bekommt_die_argumente_seiner_platzhalter():
    """Zu jedem Platzhalter im Text gibt es ein Argument – sonst stünde «{0}» auf der Seite."""
    daten = baue(kleine_tabelle())
    for schluessel, liste in daten["vorbehalte"].items():
        for kennung, *args in liste:
            erwartet = platzhalter(VORBEHALTE[kennung].text)
            assert erwartet == set(range(len(args))), f"{schluessel}: «{kennung}» braucht {erwartet}, hat {args}"
            assert all(a for a in args), f"{schluessel}: «{kennung}» mit leerem Argument"


def test_jede_zelle_ohne_wert_hat_grund_und_quelle():
    """Auch ohne Wert muss die Darstellung sagen, woran es liegt, und in die Quelle springen können."""
    daten = baue(kleine_tabelle())
    faecher = [str(f["id"]) for f in daten["faecher"]]
    for r in daten["regionen"]:
        for abschnitt in ("IST", "PLAN"):
            for fach in faecher:
                schluessel = f"{r['id']}|{abschnitt}|{fach}"
                if schluessel in daten["werte"]:
                    continue
                grund = daten["kein_wert"].get(schluessel)
                assert grund, f"{schluessel}: kein Wert und kein Grund"
                kennung, *args = grund
                assert set(range(len(args))) == platzhalter(KEIN_WERT[kennung]), f"{schluessel}: {kennung} {args}"
                assert f"{r['id']}|{abschnitt}" in daten["matrizen"], f"{schluessel}: keine Matrix mit PDF und Seite"


def test_satz_in_worten():
    """Der Satz nennt den ÄAVE-Abstand ohne Vorzeichen und sagt, in welche Richtung er fehlt."""
    assert "im Soll-Intervall" in satz(Zelle("im", 0.0, "PSY", 2030), "PLAN 2030")
    assert 'Bis zur Untergrenze fehlen <b class="num">3,4</b>' in satz(Zelle("unter", -3.4, "PSY", 2030), "PLAN")
    assert '<b class="num">2,5</b> ÄAVE über der Obergrenze' in satz(Zelle("über", 2.5, "PSY", 2030), "PLAN")
    assert "kein Wert" in satz(None, "IST 2022")


def test_kfo_vorbehalt_trennt_korrekturregel_von_nicht_getrennt():
    """Oberösterreich (Fußnote, Korrekturregel) und Wien/Vorarlberg (in ZMK enthalten) sind zwei Befunde."""

    def fuer(land: str, land_name: str, zuschnitt: str) -> dict[str, tuple[str, ...]]:
        return dict(
            vorbehalte(
                fach="ZMK",
                teil_von=None,
                abschnitt="PLAN",
                ebene="BL",
                land=land,
                land_name=land_name,
                block="haupt",
                zelle=Zelle("im", 0.0, zuschnitt, 2030),
                am_ist=None,
                am_plan=None,
                ist_jahr=2022,
            )
        )

    ooe = fuer("OÖ", "Oberösterreich", "ZMK + KFO (KFO nicht in der Tabelle, per Korrekturregel)")
    wien = fuer("Wien", "Wien", "ZMK (KFO nicht getrennt ausgewiesen)")
    assert "kfo_korrekturregel" in ooe and "kfo_nicht_getrennt" not in ooe
    assert "kfo_nicht_getrennt" in wien and "kfo_korrekturregel" not in wien


# --- Farben ---------------------------------------------------------------------------------------------------------

STUFEN = ["u3", "u2", "u1", "in", "o1", "o2", "o3"]
"""Farbstufen in der Reihenfolge der Skala; Nachbarn müssen sich unterscheiden (docs/WEB.md, «Darstellungsregeln»)."""

MIN_DELTA_E = 8
"""Mindestabstand ΔE (OKLab × 100) zweier Nachbarstufen, auch bei Protanopie und Deuteranopie."""

# Simulation der Farbsehschwäche nach Machado, Oliveira, Fernandes (2009), Schweregrad 1,0, auf linearem RGB
MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
}


def linear(hexfarbe: str) -> list[float]:
    s = [int(hexfarbe[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in s]


def oklab(rgb: list[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    lms = [
        (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3),
        (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3),
        (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3),
    ]
    l_, m, s = lms
    return (
        0.2104542553 * l_ + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l_ - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l_ + 0.7827717662 * m - 0.8086757660 * s,
    )


def delta_e(a: str, b: str, sicht: str | None) -> float:
    def lab(h: str) -> tuple[float, float, float]:
        rgb = linear(h)
        if sicht:
            m = MACHADO[sicht]
            rgb = [min(1.0, max(0.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3)]
        return oklab(rgb)

    return 100 * sum((x - y) ** 2 for x, y in zip(lab(a), lab(b))) ** 0.5


def farben(block: str) -> dict[str, str]:
    return dict(re.findall(r"--(u[123]|o[123]|in):\s*(#[0-9a-fA-F]{6})", block))


def farbbloecke() -> dict[str, str]:
    """Hell (`:root`), dunkel über die Systemeinstellung und dunkel über den Schalter (`data-theme`)."""
    css = (WEB / "style.css").read_text(encoding="utf-8")
    return {
        "hell": css.split(":root {", 1)[1].split("}", 1)[0],
        "dunkel (System)": css.split("@media (prefers-color-scheme: dark)", 1)[1].split("} }", 1)[0],
        "dunkel (Schalter)": css.split(':root[data-theme="dark"] {', 1)[1].split("}", 1)[0],
    }


def test_dunkle_farben_gleich_ob_system_oder_schalter():
    b = farbbloecke()
    assert farben(b["dunkel (System)"]) == farben(b["dunkel (Schalter)"])


@pytest.mark.parametrize("modus", ["hell", "dunkel (System)"])
@pytest.mark.parametrize("sicht", [None, "protan", "deutan"])
def test_nachbarstufen_unterscheidbar(modus, sicht):
    f = farben(farbbloecke()[modus])
    assert set(f) == set(STUFEN), f"Farbstufen fehlen in style.css ({modus})"
    zu_nah = [
        f"{a}–{b} ΔE {d:.1f}" for a, b in zip(STUFEN, STUFEN[1:]) if (d := delta_e(f[a], f[b], sicht)) < MIN_DELTA_E
    ]
    assert not zu_nah, f"{modus}, Sicht {sicht or 'normal'}: {zu_nah}"


# --- data.json ------------------------------------------------------------------------------------------------------


def kleine_tabelle() -> pd.DataFrame:
    """VR 41 und das Land OÖ, IST und PLAN, alle Fächer; Werte frei erfunden, nur das Format zählt."""
    zeilen = []
    for ebene, rid in (("VR", "41"), ("BL", "OÖ")):
        for abschnitt, jahr in (("IST", 2022), ("PLAN", 2030)):
            for fach in faecher()["Fach"]:
                zeilen.append(
                    {
                        "Datensatz": "RSG 2030", "Land": "OÖ", "Ebene": ebene, "Region_ID": rid,
                        "Abschnitt": abschnitt, "Jahr": jahr, "Zeile_ID": "insgesamt", "Fach": fach,
                        "Basis": "Sachleistung", "AAVE": 10.0, "Zuschnitt": fach, "Bevoelkerung": 100000.0,
                        "VD": 10.0, "VDmin": 5.0, "VDmax": 15.0, "Lage_im_Intervall": "im",
                        "Position_im_Intervall": 0.5, "AAVE_Abstand_Intervall": 0.0,
                    }
                )  # fmt: skip
    return pd.DataFrame(zeilen)


def baue(tabelle: pd.DataFrame, k: pd.DataFrame | None = None, f: pd.DataFrame | None = None,
         long: pd.DataFrame | None = None, regeln: pd.DataFrame | None = None) -> dict:  # fmt: skip
    return baue_daten(
        tabelle,
        lade_regionen(),
        kacheln() if k is None else k,
        faecher() if f is None else f,
        kleine_matrix() if long is None else long,
        ohne_regeln() if regeln is None else regeln,
        META,
    )


# Spalten der Testmatrix: je Fach müssen die Spalten des ÖSG-Zuschnitts genau die 10,0 ÄAVE von
# `kleine_tabelle()` ergeben. Deshalb stehen in IM und ZMK 0,0 – die 10 liegen in PUL bzw. KFO, die der
# Zuschnitt dazuzählt (IM = IM + PUL, ZMK = ZMK + KFO). KJC und PCH fehlen, wie in den meisten Matrizen.
MATRIX_SPALTEN = {
    "AM": 10.0, "KIJU": 10.0, "KJP": 10.0, "CH": 10.0, "IM": 0.0, "PUL": 10.0, "GGH": 10.0, "NEU": 10.0,
    "PSY": 10.0, "DER": 10.0, "AU": 10.0, "HNO": 10.0, "URO": 10.0, "ORTR": 10.0, "MKG": 10.0, "ZMK": 0.0,
    "KFO": 10.0,
}  # fmt: skip
TEST_PDF = "4.VO_RSG_OOe_2030_Anlage.pdf"
"""Ein PDF, das in quellen.csv als RSG-Verordnung steht – sonst findet der Bau keine RIS-Adresse."""


def kleine_matrix(**aendern: object) -> pd.DataFrame:
    """Long-Zeilen zu `kleine_tabelle()`: Zeile «insgesamt» beider Matrizen, alles aus dem PDF gelesen."""
    zeilen = []
    for ebene, rid in (("VR", "41"), ("BL", "OÖ")):
        for abschnitt, jahr in (("IST", 2022), ("PLAN", 2030)):
            for fach, wert in MATRIX_SPALTEN.items():
                zeilen.append(
                    {
                        "Land": "OÖ", "Ebene": ebene, "Region_ID": rid, "Block": "haupt", "Abschnitt": abschnitt,
                        "Jahr": jahr, "Zeile_ID": "insgesamt", "Einheit": "ÄAVE", "Fach": fach, "Wert": wert,
                        "Roh": f"{wert:.1f}".replace(".", ","), "Quelle": "PDF", "Regel": None,
                        "Zeile_PDF_roh": f"{abschnitt} ÄAVE insgesamt", "PDF": TEST_PDF, "Seite": 11,
                    }
                )  # fmt: skip
    return pd.DataFrame(zeilen).assign(**aendern)


def ohne_regeln() -> pd.DataFrame:
    return pd.DataFrame(columns=REGEL_SPALTEN, dtype=str)


# --- Herkunft -------------------------------------------------------------------------------------------------------


def test_herkunft_nennt_die_spalten_des_zuschnitts():
    """Je Zelle die Matrixspalten, aus denen sie entstand – mit dem Text wie gedruckt."""
    d = baue(kleine_tabelle())
    assert len(d["herkunft"]) == len(d["werte"]), "jede gezeigte Zelle braucht ihre Herkunft"
    assert d["herkunft"]["41|PLAN|IM"] == [
        ["IM", "0,0", 0.0, "PDF", None, None],
        ["PUL", "10,0", 10.0, "PDF", None, None],
    ]
    assert [a[0] for a in d["herkunft"]["41|PLAN|CH"]] == ["CH"], "KJC und PCH fehlen in dieser Matrix"
    quelle, seite, zeile, block = d["matrizen"]["41|PLAN"]
    assert (d["quellen"][quelle][0], seite, zeile, block) == (TEST_PDF, 11, "PLAN ÄAVE insgesamt", "haupt")
    pdf, ris, datei_url = d["quellen"][quelle]
    assert ris.startswith("https://www.ris.bka.gv.at/"), "Seite des Dokuments zum Nachlesen"
    # Adresse der Datei ohne Sprungziel: «#page=» hängt die Seite erst in app.js an
    assert datei_url == f"{OGD_HOST}/Dokumente/Spg/SPG_OB_RSG_V_20260311_5_2026/{pdf}"


def test_herkunft_unterscheidet_regeln_mit_gleichem_namen():
    """Denselben Regelnamen kann es mehrfach geben, mit verschiedener Begründung (Kärnten: `plus:6.3` ist in VR 22
    eine Lücke, im Land ihre Folge). Gemerkt wird deshalb die Regelzeile, nicht der Name – sonst stünde an einer
    Zelle die Begründung der anderen."""
    gleicher_name = pd.DataFrame(
        [
            {"Land": "OÖ", "Ebene": ebene, "Region_ID": rid, "Block": "haupt", "Abschnitt": "*",
             "Zeile_ID": "insgesamt", "Fach": "AM", "Regel": "wert:10.0", "Art": art,
             "Befund": "leere_summenzelle", "Begruendung": grund}
            for ebene, rid, art, grund in (("VR", "41", "Lücke", "in der Region"), ("BL", "OÖ", "Folge", "im Land"))
        ],
        columns=REGEL_SPALTEN,
    )  # fmt: skip
    m = kleine_matrix()
    m.loc[m["Fach"] == "AM", ["Quelle", "Regel"]] = ["korrigiert", "wert:10.0"]
    d = baue(kleine_tabelle(), long=m, regeln=gleicher_name)
    vr, bl = d["herkunft"]["41|PLAN|AM"][0][4], d["herkunft"]["OÖ|PLAN|AM"][0][4]
    assert vr != bl, "beide Zellen zeigen auf dieselbe Regel"
    assert d["regeln"][vr][1:] == ["Lücke", "in der Region"]
    assert d["regeln"][bl][1:] == ["Folge", "im Land"]


def test_herkunft_bricht_ab_wenn_die_teile_den_wert_nicht_ergeben():
    """Die Probe, die alles trägt: zeigt die Seite andere Spalten, als in den Wert eingegangen sind, bricht der Bau ab."""
    with pytest.raises(ValueError, match="ergibt 11.0, die Tabelle nennt 10.0"):
        baue(kleine_tabelle(), long=kleine_matrix().assign(Wert=lambda m: m["Wert"].where(m["Fach"] != "PUL", 11.0)))


def test_herkunft_bricht_ab_ohne_eindeutige_regel():
    """Eine korrigierte Zelle ohne Begründung bleibt nicht stumm: lieber kein Bau als eine erfundene Herkunft."""
    with pytest.raises(ValueError, match="keine eindeutige Korrekturregel"):
        baue(kleine_tabelle(), long=kleine_matrix(Quelle="korrigiert", Regel="wert:10.0"))


def test_herkunft_bricht_ab_wenn_die_matrix_auf_zwei_seiten_liegt():
    m = kleine_matrix()
    with pytest.raises(ValueError, match="nicht eindeutig"):
        baue(kleine_tabelle(), long=m.assign(Seite=m["Seite"].where(m["Fach"] != "AM", 12)))


def test_herkunft_bricht_ab_bei_unbekannter_quelle():
    with pytest.raises(ValueError, match="unbekannte Quelle"):
        baue(kleine_tabelle(), long=kleine_matrix(Quelle="geschätzt"))


def test_herkunft_bricht_ab_wenn_das_pdf_nicht_im_register_steht():
    with pytest.raises(ValueError, match="quellen.csv"):
        baue(kleine_tabelle(), long=kleine_matrix(PDF="irgendwas.pdf"))


def test_data_json_aufbau():
    d = baue(kleine_tabelle())
    assert [r["id"] for r in d["regionen"]] == ["41", "OÖ"]  # VR vor BL
    vr = d["regionen"][0]
    assert (vr["name"], vr["land_name"]) == ("OÖ Zentralraum Linz", "Oberösterreich")
    assert [f["id"] for f in d["faecher"]] == list(faecher()["Fach"])
    assert d["werte"]["41|IST|IM"] == [10.0, 10.0, 100000, 2022, "im", 0.5, 0.0, "IM"]
    assert isinstance(d["werte"]["41|IST|IM"][WERT.index("Bevoelkerung")], int)


def test_bricht_ab_wenn_spalte_fehlt():
    with pytest.raises(ValueError, match="ohne Spalten"):
        baue(kleine_tabelle().drop(columns="Position_im_Intervall"))


def test_bricht_ab_wenn_fach_nicht_in_faecher_csv():
    with pytest.raises(ValueError, match="faecher.csv"):
        baue(kleine_tabelle(), f=faecher()[faecher()["Fach"] != "KFO"])


def test_bricht_ab_wenn_kachel_fehlt():
    with pytest.raises(ValueError, match="keine Kachel für VR 41"):
        baue(kleine_tabelle(), k=kacheln()[kacheln()["Region_ID"] != "41"])


@pytest.mark.slow
def test_data_json_gleich_tabelle():
    """Jede Zelle der Zeile «insgesamt» steht unverändert in data.json, und nichts sonst."""
    from rsg2030.versorgungsdichte import baue_versorgungsdichte

    tabelle = baue_versorgungsdichte()
    d = baue(tabelle, long=lade_matrix_long(), regeln=lade_regeln())
    ins = tabelle[tabelle["Zeile_ID"] == "insgesamt"]
    assert len(d["werte"]) == len(ins)
    for r in ins.to_dict("records"):
        w = d["werte"][f"{r['Region_ID']}|{r['Abschnitt']}|{r['Fach']}"]
        for spalte, wert in zip(WERT, w):
            soll = r[spalte]
            # Bevölkerung und Jahr stehen als ganze Zahl in data.json – gerundet, nicht abgeschnitten: Die
            # Bevölkerung einer VR im PLAN hat Nachkommastellen (Landesprognose × ÖROK-Anteil der Region).
            erwartet = round(soll) if spalte in ("Bevoelkerung", "Jahr") else soll
            assert wert == erwartet, (r["Region_ID"], spalte, soll)
    assert {(r["ebene"], r["id"]) for r in d["regionen"]} == set(zip(ins["Ebene"], ins["Region_ID"].astype(str)))


@pytest.mark.slow
def test_kfo_vorbehalt_genau_wo_die_spalte_fehlt():
    """«KFO nicht getrennt ausgewiesen» steht genau an den Zellen, deren Zuschnitt das sagt – und nur dort.

    Trennt die beiden KFO-Befunde: Wien und Vorarlberg führen KFO in ZMK (Fußnote bzw. Textteil),
    Oberösterreich übernimmt es per Korrekturregel aus einer Fußnote (docs/DATEN.md, Fallstrick 4).
    """
    from rsg2030.versorgungsdichte import baue_versorgungsdichte

    tabelle = baue_versorgungsdichte()
    d = baue(tabelle, long=lade_matrix_long(), regeln=lade_regeln())
    ins = tabelle[tabelle["Zeile_ID"] == "insgesamt"]

    def zellen(kennung: str) -> set[str]:
        return {k for k, liste in d["vorbehalte"].items() if any(v[0] == kennung for v in liste)}

    def laut_zuschnitt(text: str) -> set[str]:
        treffer = ins[ins["Zuschnitt"].str.contains(text, regex=False, na=False)]
        return {f"{r.Region_ID}|{r.Abschnitt}|{r.Fach}" for r in treffer.itertuples()}

    assert zellen("kfo_nicht_getrennt") == laut_zuschnitt("KFO nicht getrennt ausgewiesen")
    assert zellen("kfo_korrekturregel") == laut_zuschnitt("per Korrekturregel")
    laender = {ins.loc[ins["Region_ID"] == k.split("|")[0], "Land"].iloc[0] for k in zellen("kfo_nicht_getrennt")}
    assert laender == {"Wien", "Vorarlberg"}

    # Was außer KFO noch in ZMK steckt, sagt nur Wiens Fußnote (5) – der Vorbehalt gilt deshalb nur dort
    wien_zmk = {
        f"{r.Region_ID}|{r.Abschnitt}|{r.Fach}" for r in ins.itertuples() if r.Land == "Wien" and r.Fach == "ZMK"
    }
    assert zellen("wien_zmk_breiter") == wien_zmk


@pytest.mark.slow
def test_herkunft_zitiert_die_tabelle_planungsmatrizen():
    """Die Herkunft ist ein Zitat, keine Darstellung: jeder Text steht zeichengleich in der Long-CSV, jede Regel so
    in korrekturen.csv. Formatiert die Seite den Rohtext um, stünde dort etwas anderes als im Dokument."""
    from rsg2030.versorgungsdichte import baue_versorgungsdichte

    long, regeln = lade_matrix_long(), lade_regeln()
    d = baue(baue_versorgungsdichte(), long=long, regeln=regeln)
    zellen = {}
    for (land, ebene, rid), _ in long.groupby(["Land", "Ebene", "Region_ID"]):
        m = matrix_long(long, str(land), str(ebene), str(rid))
        for z in m.itertuples():
            zellen[(str(ebene), str(rid), z.Abschnitt, z.Zeile_ID, z.Fach)] = z

    geprueft = 0
    for schluessel, angaben in d["herkunft"].items():
        rid, abschnitt, _ = schluessel.split("|")
        ebene = "VR" if rid.isdigit() else "BL"
        for spalte, roh, wert, quelle, _regel, _zeile in angaben:
            zeile, fach = ZAE_QUELLE if spalte == ZAE else ("insgesamt", spalte)
            z = zellen[(ebene, rid, abschnitt, zeile, fach)]
            assert roh == (None if pd.isna(z.Roh) or z.Roh == "" else z.Roh), (schluessel, spalte)
            assert wert == (None if pd.isna(z.Wert) else z.Wert), (schluessel, spalte)
            assert quelle == z.Quelle, (schluessel, spalte)
            geprueft += 1
    assert geprueft == sum(len(a) for a in d["herkunft"].values())

    for name, art, grund in d["regeln"]:
        treffer = regeln[(regeln["Regel"] == name) & (regeln["Art"] == art) & (regeln["Begruendung"] == grund)]
        assert len(treffer), f"Regel «{name}» steht nicht so in korrekturen.csv"


# --- nichts von fremden Servern -------------------------------------------------------------------------------------


def test_dashboard_hat_eine_adresse_fuer_die_suche():
    """`canonical` auf die Wurzel der Lesefassungs-Domain: Links mit ?region=…&fach=… sind keine eigenen Seiten."""
    from rsg2030.lesefassung import BASIS_STANDARD

    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert f'<link rel="canonical" href="{BASIS_STANDARD}/">' in html


def test_dashboard_verlinkt_die_lesefassung_fest_im_html():
    """Ein Link, unauffällig unter «Über diese Daten», fest im HTML: Crawler ohne JavaScript sehen nur das, und Links
    von außen zeigen aufs Dashboard, nicht auf die Seiten (docs/WEB.md, «Zwei Wege»)."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    about = re.search(r'<section [^>]*id="about"[^>]*>(.*?)</section>', html, re.S)
    assert about and '<a href="daten/">' in about.group(1)
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'getElementById("about").innerHTML' not in js, "app.js überschriebe den festen Link"


ZAHLFAELLE = [
    # (Wert, VDmin, VDmax) → wie auf der Seite; None = keine Grenze (ÄAVE)
    ((1.5890802, 1.6, 3.0), "1,59"),  # Burgenland-Nord, PUL, PLAN: sonst 1,6 neben 1,6–3,0 und «unter»
    ((1.6466737, 1.6, 3.0), "1,6"),  # IST, im Intervall: bleibt
    ((8.4143, 4.5, 8.4), "8,41"),  # knapp über VDmax
    ((3.0, 1.6, 3.0), "3,0"),  # genau auf der Grenze ist innerhalb
    ((0.787, 0.8, 1.4), "0,79"),  # KJP (VR 33, IST): eine Stelle wie im ÖSG, an der Grenze eine mehr
    ((0.7951, 0.8, 1.4), "0,795"),  # auch zwei Stellen fielen auf die Grenze: drei
    ((1.0549, 0.8, 1.4), "1,1"),  # KJP im Intervall: eine Stelle
    ((0.0351898, 2.8, 5.1), "0,04"),  # Salzburg, KFO, IST: nicht 0, also nicht «0,0»
    ((0.0, 0.5, 0.9), "0"),  # nichts geplant (in der Matrix «-»)
    ((211.47, None, None), "211,5"),  # ÄAVE
    ((0.04, None, None), "0,04"),
    ((0.0, None, None), "0"),
]


def test_zahlen_auf_der_seite():
    """Eine Stelle; eine mehr, wo die Rundung sonst etwas Falsches sagte; genau 0 als «0» (docs/WEB.md)."""
    from rsg2030.darstellung import lesbar

    for args, text in ZAHLFAELLE:
        assert lesbar(*args) == text, args


@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_dashboard_rundet_wie_die_lesefassung():
    """Dieselbe Regel in app.js (`lesbar`) – die Funktionen aus app.js herausgelöst und mit node gerechnet."""
    js = (WEB / "app.js").read_text(encoding="utf-8")
    teil = js[js.index("const nf = ") : js.index("const esc = ")]
    faelle = json.dumps([[*a, s] for a, s in ZAHLFAELLE])
    prog = (
        teil
        + f"""
for (const [x, lo, hi, soll] of {faelle}) {{
  const ist = lesbar(x, lo, hi);
  if (ist !== soll) {{ console.log(`${{x}}: ${{ist}} statt ${{soll}}`); process.exitCode = 1; }}
}}"""
    )
    lauf = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr


def test_dashboard_hat_die_fusszeile_der_lesefassung():
    """Eine Fußzeile für beide Darstellungen (rsg2030/darstellung.py, `fusszeile`): app.js setzt sie aus data.json
    ein und schreibt keine eigene. Sie trägt die Namensnennung nach LIZENZ_DATEN.md."""
    from rsg2030.darstellung import NAMENSNENNUNG, fusszeile

    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'getElementById("footer").innerHTML = D.fusszeile;' in js
    assert "Statistik Austria" not in js, "zweite Kopie der Namensnennung in app.js"
    text = fusszeile("https://github.com/x/y", "2026.9", "8657f1075b26bf76a4c9c004617feb932c85ef76")
    assert NAMENSNENNUNG in text and "Release 2026.9" in text and "Impressum" in text
    assert 'commit/8657f1075b26bf76a4c9c004617feb932c85ef76"' in text and ">8657f10</a>" in text
    assert "Stand der Seite" not in fusszeile("https://github.com/x/y", "2026.9", "unbekannt")
    assert text.count("<a ") == text.count('rel="noopener noreferrer"')


def test_seite_laedt_nichts_von_fremden_servern():
    """Schriften, Skripte und Stile kommen aus web/ selbst; Links (<a href>) auf GitHub und das RIS sind erlaubt:
    Erst wer klickt, gibt seine IP-Adresse dorthin – anders als bei einer eingebundenen Datei (Datenschutz)."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    # <link rel="canonical"> lädt nichts, es nennt nur die Adresse der Seite
    ohne_canonical = re.sub(r'<link rel="canonical" href="[^"]*">', "", html)
    assert not re.findall(r"<(?:link|script|img|iframe)[^>]+(?:href|src)=\"(?:https?:)?//", ohne_canonical)
    assert not re.findall(r"@import|url\(\s*[\"']?(?:https?:)?//", css)
    assert not re.findall(r"\b(?:fetch|import)\s*\(\s*[\"'`](?:https?:)?//", js)


def test_jede_schrift_der_css_liegt_in_web_fonts():
    css = (WEB / "style.css").read_text(encoding="utf-8")
    dateien = re.findall(r"url\(\"(fonts/[^\"]+)\"\)", css)
    assert dateien, "keine @font-face gefunden"
    assert [d for d in dateien if not (WEB / d).is_file()] == []
    assert (WEB / "fonts" / "OFL.txt").is_file(), "Lizenz der Schriften fehlt"


def test_links_auf_das_release_der_daten_nicht_auf_latest():
    """Downloads und Doku passen nur dann zu den gezeigten Zahlen, wenn sie auf dasselbe Release zeigen."""
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "releases/download/${M.version}" in js
    assert "releases/latest" not in js


def test_externe_links_schicken_keinen_referrer():
    """Jeder Link nach außen trägt `noreferrer`: Die IP-Adresse geht beim Klick ohnehin zum Ziel, von welcher Seite
    jemand kam braucht es nicht (wie bei den selbst ausgelieferten Schriften). Nebenbei die sichere Seite, falls ein
    Server fremde Referer je sperrt."""
    js = (WEB / "app.js").read_text(encoding="utf-8")
    anker = re.findall(r"<a href=[^>]*>", js)
    assert anker, "keine Links gefunden – prüft dieser Test noch, was er soll?"
    ohne = [a for a in anker if "noreferrer" not in a]
    assert not ohne, f"Link ohne noreferrer: {ohne}"
