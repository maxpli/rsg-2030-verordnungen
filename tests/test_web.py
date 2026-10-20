"""Webseite (docs/WEB.md, «Wer prüft was»): Kacheln, Fächer, Vorbehalte, Farben und data.json gegen die Tabelle.

Die schnellen Tests brauchen keine Quelldateien. Der langsame rechnet die Tabelle Versorgungsdichte frisch und
vergleicht jede Zelle von data.json mit ihr.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest
from conftest import ROOT

from oesg_methodik import LAND_KURZ
from oesg_methodik.bevoelkerung import lade_regionen
from oesg_methodik.faecher import ZUSCHNITT
from oesg_methodik.richtwerte import lade_richtwerte
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
    js = (WEB / "app.js").read_text(encoding="utf-8")
    teil = js.split("function vorbehalte(", 1)[1].split("\nfunction ", 1)[0]
    genannt = [int(n) for n in re.findall(r"fallstrick: (\d+)", teil)]
    assert len(genannt) == teil.count("out.push("), "ein Vorbehalt ohne Fallstrick"
    assert set(genannt) <= fallstricke_in_daten_md(), "Vorbehalt verweist auf einen Fallstrick, den es nicht gibt"


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


def baue(tabelle: pd.DataFrame, k: pd.DataFrame | None = None, f: pd.DataFrame | None = None) -> dict:
    return baue_daten(tabelle, lade_regionen(), kacheln() if k is None else k, faecher() if f is None else f, META)


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
    d = baue(tabelle)
    ins = tabelle[tabelle["Zeile_ID"] == "insgesamt"]
    assert len(d["werte"]) == len(ins)
    for r in ins.to_dict("records"):
        w = d["werte"][f"{r['Region_ID']}|{r['Abschnitt']}|{r['Fach']}"]
        for spalte, wert in zip(WERT, w):
            soll = r[spalte]
            assert wert == (int(soll) if spalte in ("Bevoelkerung", "Jahr") else soll), (r["Region_ID"], spalte)
    assert {(r["ebene"], r["id"]) for r in d["regionen"]} == set(zip(ins["Ebene"], ins["Region_ID"].astype(str)))


# --- nichts von fremden Servern -------------------------------------------------------------------------------------


def test_seite_laedt_nichts_von_fremden_servern():
    """Schriften, Skripte und Stile kommen aus web/ selbst; Links (<a href>) auf GitHub sind erlaubt (Datenschutz)."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert not re.findall(r"<(?:link|script|img|iframe)[^>]+(?:href|src)=\"(?:https?:)?//", html)
    assert not re.findall(r"@import|url\(\s*[\"']?(?:https?:)?//", css)
    assert not re.findall(r"\b(?:fetch|import)\s*\(\s*[\"'`](?:https?:)?//", js)


def test_jede_schrift_der_css_liegt_in_web_fonts():
    css = (WEB / "style.css").read_text(encoding="utf-8")
    dateien = re.findall(r"url\(\"(fonts/[^\"]+)\"\)", css)
    assert dateien, "keine @font-face gefunden"
    assert [d for d in dateien if not (WEB / d).is_file()] == []
    assert (WEB / "fonts" / "OFL.txt").is_file(), "Lizenz der Schriften fehlt"
