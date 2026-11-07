"""Lesefassung (docs/WEB.md, «Lesefassung»): Adressen, Vorlagen, Zahlen und der Apparat.

Was diese Tests belegen: Die Seiten sagen nichts, was die Daten nicht tragen, jede Zahl steht so da wie in der
veröffentlichten Tabelle, und jede Seite ist erreichbar und auffindbar. Was sie nicht belegen: ob die Seiten
verständlich sind – das liest ein Mensch (docs/WEB.md, «Wer prüft was»).

Die Tests brauchen die veröffentlichten Tabellen in `daten_ergebnis/` und sind deshalb `slow`; sie bauen die
Seiten einmal je Testlauf (Fixture `lesefassung`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
from conftest import ROOT

from rsg2030.config import VERSORGUNGSDICHTE_DATEI, ausgabe_dir
from rsg2030.darstellung import VORBEHALTE
from rsg2030.lesefassung import (
    LAND_SLUG,
    VERBOTEN,
    Aufbau,
    _anker,
    _dokument,
    offene_fragen_ueberschrift,
    release_datum,
    seite_fach,
    seite_index,
    seite_region,
)

BASIS = "https://beispiel.invalid/rsg"


@pytest.fixture(scope="module")
def seiten() -> dict[str, str]:
    """Alle Seiten einmal bauen: Pfad → fertiges HTML."""
    a = Aufbau(BASIS)
    alle = [seite_index(a), *[seite_region(a, r) for r in a.regionen], *[seite_fach(a, f) for f in a.faecher]]
    return {s.pfad: _dokument(a, s) for s in alle}


@pytest.fixture(scope="module")
def aufbau() -> Aufbau:
    return Aufbau(BASIS)


pytestmark = pytest.mark.slow


# --- Umfang und Adressen --------------------------------------------------------------------------------------


def test_umfang(seiten):
    """9 Bundesländer, 32 Versorgungsregionen, 17 Fächer, eine Indexseite – mehr nicht, weniger nicht."""
    assert sum(1 for p in seiten if p.startswith("bl/")) == 9
    assert sum(1 for p in seiten if p.startswith("vr/")) == 32
    assert sum(1 for p in seiten if p.startswith("fach/")) == 17
    assert "daten/" in seiten
    assert len(seiten) == 59


def test_adressen_bleiben_nummern_und_kuerzel(seiten):
    """Eine Adresse kann nicht umziehen (GitHub Pages kann nicht umleiten): keine Namen, keine Umlaute."""
    for pfad in seiten:
        assert re.fullmatch(r"(daten|bl/[a-z]+|vr/\d{2}|fach/[A-Z/]+)/", pfad), pfad
    assert set(LAND_SLUG.values()) == {p.split("/")[1] for p in seiten if p.startswith("bl/")}


def test_jede_seite_hat_titel_h1_und_canonical(seiten):
    for pfad, html in seiten.items():
        assert "<title>" in html and "</title>" in html, pfad
        assert html.count("<h1>") == 1, pfad
        assert f'<link rel="canonical" href="{BASIS}/{pfad}">' in html, pfad
        assert 'name="description"' in html, pfad
        titel = re.search(r"<title>(.*?)</title>", html, re.S)
        assert titel and 20 < len(titel.group(1)) < 120, pfad


def test_kein_javascript_und_nichts_von_fremden_servern(seiten):
    """Der ganze Zweck ist reiner Text; und die Seiten geben nichts an Dritte weiter."""
    for pfad, html in seiten.items():
        ohne_jsonld = re.sub(r'<script type="application/ld\+json">.*?</script>', "", html, flags=re.S)
        assert "<script" not in ohne_jsonld, pfad
        assert "onclick" not in html and "javascript:" not in html, pfad
        fremde = [
            u
            for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
            if "ogd.ris.bka.gv.at" not in u and not u.startswith(BASIS)
        ]
        for url in fremde:
            assert re.match(r"https://(www\.ris\.bka\.gv\.at|github\.com|loesungswerk\.at|orcid\.org|creativecommons\.org)", url), (pfad, url)  # fmt: skip
        # Jeder Link nach außen: neues Fenster wie im Dashboard, und nichts über die Herkunft verraten
        for url in re.findall(r'<a href="(https?://[^"]+)"', html):
            stelle = html[html.index(f'<a href="{url}"') : html.index(f'<a href="{url}"') + 400]
            assert 'rel="noopener noreferrer"' in stelle, (pfad, url)
            assert 'target="_blank"' in stelle, (pfad, url)
        # Interne Links bleiben im selben Fenster
        for url in re.findall(r'<a href="(\.\./[^"]+|[a-z]+/[^":]*)"[^>]*>', html):
            stelle = html[html.index(f'<a href="{url}"') : html.index(f'<a href="{url}"') + 200]
            assert "target=" not in stelle, (pfad, url)


def test_jede_seite_ist_von_der_indexseite_erreichbar(seiten):
    """Ohne Verlinkung findet ein Crawler die Unterseiten nur über die Sitemap – beides soll stimmen."""
    index = seiten["daten/"]
    for pfad in seiten:
        if pfad == "daten/":
            continue
        assert f'href="../{pfad}"' in index, pfad


# --- Was die Seiten sagen dürfen ------------------------------------------------------------------------------


def test_kein_urteil_das_die_daten_nicht_tragen(seiten):
    for pfad, html in seiten.items():
        for wort in VERBOTEN:
            assert wort not in html.lower(), (pfad, wort)


def test_keine_unausgefuellte_vorlage(seiten):
    for pfad, html in seiten.items():
        assert not re.search(r"\{\d\}", html), pfad
        assert not re.search(r"\b(nan|NaN|None)\b", html), pfad
        assert "  ," not in html and "( )" not in html, pfad


def test_jede_seite_nennt_die_grenzen_der_zahlen(seiten):
    """«Was diese Zahlen nicht sagen» steht auf jeder Seite mit Werten – nicht nur auf der Indexseite."""
    for pfad, html in seiten.items():
        assert "Was diese Zahlen nicht sagen" in html, pfad
        assert "ohne Wahlärzt:innen" in html or "Wahlärzt:innen" in html, pfad


def test_zuschnitt_und_teilmengen_stehen_bei_jeder_fachtabelle(seiten):
    """19 % der Zeilen haben einen Zuschnitt, der vom Fach abweicht; ohne Hinweis vergleicht man Verschiedenes."""
    for pfad, html in seiten.items():
        if not (pfad.startswith(("bl/", "vr/"))):
            continue
        assert "◆" in html, pfad
        assert "Zuschnitt des ÖSG" in html, pfad
        assert "stecken bereits in IM bzw. ZMK" in html, pfad


def test_sve_laender_nennen_den_block_der_aequivalente(seiten, aufbau):
    """Nur der zweite Block ist mit den anderen Ländern vergleichbar (docs/DATEN.md, Fallstrick 3)."""
    for r in aufbau.regionen:
        if aufbau.daten["matrizen"].get(f"{r['id']}|PLAN", [None, None, None, None])[3] != "aequivalent":
            continue
        html = seiten[aufbau.pfad(r)]
        assert "ÄAVE-Äquivalente" in html, r["id"]


# --- Zahlen gegen die veröffentlichte Tabelle -----------------------------------------------------------------


def test_jede_zahl_steht_so_in_der_tabelle(seiten, aufbau):
    """Stichprobe über alle Regionen: VD und ÄAVE der Zeile «insgesamt» stehen zeichengleich auf der Seite."""
    tabelle = pd.read_csv(ausgabe_dir() / VERSORGUNGSDICHTE_DATEI, dtype={"Region_ID": str})
    ins = tabelle[(tabelle["Zeile_ID"] == "insgesamt") & (tabelle["Abschnitt"] == "PLAN")]
    geprueft = 0
    for r in aufbau.regionen:
        html = seiten[aufbau.pfad(r)]
        for z in ins[ins["Region_ID"] == str(r["id"])].itertuples():
            fach = next(f for f in aufbau.faecher if f["id"] == z.Fach)
            stellen = 2 if float(str(fach["max"])) < 2 else 1
            for wert, dg in ((z.AAVE, 1), (z.VD, stellen)):
                text = f"{float(wert):.{dg}f}".replace(".", ",")
                assert f">{text}<" in html, (r["id"], z.Fach, text)
                geprueft += 1
    assert geprueft > 1000, geprueft


def test_soll_intervall_wie_im_richtwert(seiten, aufbau):
    """Das Soll-Intervall steht auf jeder Fachseite so da wie in der Tabelle."""
    for f in aufbau.faecher:
        dg = 2 if float(str(f["max"])) < 2 else 1
        html = seiten[f"fach/{f['id']}/"]
        min_t = f"{float(str(f['min'])):.{dg}f}".replace(".", ",")
        max_t = f"{float(str(f['max'])):.{dg}f}".replace(".", ",")
        assert f"{min_t} bis {max_t}" in html, f["id"]


def test_zellen_ohne_wert_nennen_grund_und_quelle(seiten, aufbau):
    """Auch ohne Wert muss die Seite sagen, woran es liegt (Kärnten/MKG, Wien und Vorarlberg/KFO)."""
    fehlend = [k.split("|") for k in aufbau.daten["kein_wert"]]
    assert fehlend, "keine Zelle ohne Wert – stimmt die Erwartung noch?"
    for rid, abschnitt, fach in fehlend:
        if abschnitt != "PLAN":
            continue
        html = seiten[aufbau.pfad(aufbau.region(rid))]
        assert "Ohne Wert in dieser Matrix" in html, (rid, fach)
        assert f"<b>{fach}</b>" in html, (rid, fach)


# --- Apparat --------------------------------------------------------------------------------------------------


def test_fussnoten_wortgleich_aus_dem_verzeichnis(seiten, aufbau):
    """Die Seiten zitieren, sie formulieren nicht um."""
    import html as html_mod

    fn = aufbau.fussnoten
    for r in aufbau.regionen:
        seite = seiten[aufbau.pfad(r)]
        treffer = fn[(fn["Ebene"] == r["ebene"]) & (fn["Region_ID"].astype(str) == str(r["id"]))]
        for z in treffer.drop_duplicates(["Zeichen", "Text"]).itertuples():
            assert html_mod.escape(str(z.Text), quote=True) in seite, (r["id"], z.Zeichen)


def test_jede_korrigierte_matrix_zeigt_ihre_regeln(seiten, aufbau):
    """Eine korrigierte Zelle ohne Begründung auf der Seite wäre genau die Lücke, die der Datensatz schließt."""
    import html as html_mod

    long = aufbau.long
    for r in aufbau.regionen:
        korrigiert = long[(long["Region_ID"] == str(r["id"])) & (long["Quelle"] == "korrigiert")]
        if korrigiert.empty:
            continue
        seite = seiten[aufbau.pfad(r)]
        assert "Woher kommt diese Zahl?" in seite, r["id"]
        for regel in sorted(set(korrigiert["Regel"].dropna())):
            assert html_mod.escape(str(regel), quote=True) in seite, (r["id"], regel)


def test_jede_seite_verlinkt_pdf_mit_seite_und_das_ris(seiten, aufbau):
    """«Seite 11 öffnen» und «Verordnung im RIS»; die Seitenzahl steht auch als Text da."""
    import html as html_mod

    for r in aufbau.regionen:
        seite = seiten[aufbau.pfad(r)]
        q = aufbau.quelle(str(r["id"]), "PLAN")
        assert q is not None, r["id"]
        pdf, nummer, datei, ris = q
        assert f"{datei}#page={nummer}" in seite, r["id"]
        assert f"Seite {nummer}" in seite, r["id"]
        # Der Link steht im HTML maskiert («&amp;» in der RIS-Adresse)
        assert html_mod.escape(ris, quote=True) in seite, r["id"]


def test_vorbehalte_kommen_aus_der_gemeinsamen_schicht(seiten, aufbau):
    """Kein eigener Vorbehaltstext in der Lesefassung: Jeder gezeigte stammt aus rsg2030/darstellung.py."""
    quelle = (ROOT / "rsg2030" / "lesefassung.py").read_text(encoding="utf-8")
    for kennung, v in VORBEHALTE.items():
        # Der Teil **nach** der Hervorhebung: «Wien» allein wäre kein Fingerabdruck (das Wort steht auch in
        # der Adressliste), der Satz danach schon.
        kern = v.text.split("</b>", 1)[-1].strip()[:30]
        assert kern not in quelle, f"Vorbehalt «{kennung}» steht als Text in lesefassung.py"


def test_offene_fragen_nur_als_verweis_und_mit_gueltigem_anker(seiten, aufbau):
    """Die Fragen stehen nicht auf der Seite, nur der Verweis – und die Sprungmarke muss es wirklich geben.

    Begründung für den Verweis statt des Texts: docs/WEB.md, «Lesefassung». Eine aufgezählte Frage wäre auf einer
    Seite mit dem Namen des Landes in der Überschrift ein Befund gegen das Land.
    """
    doku = (ROOT / "docs" / "offene_punkte.md").read_text(encoding="utf-8")
    fragen = [z for z in doku.splitlines() if z.startswith("*Frage:")]
    assert fragen, "keine Fragen in offene_punkte.md – stimmt die Erwartung noch?"
    for r in aufbau.regionen:
        html = seiten[aufbau.pfad(r)]
        # Kein Fragetext auf der Seite
        for frage in fragen:
            assert frage.strip("*").split("–")[0][:40] not in html, (r["id"], frage[:40])
        ueberschrift = offene_fragen_ueberschrift(str(r["land_name"]))
        if ueberschrift is None:
            assert "Offene Fragen zu dieser Verordnung" not in html, r["id"]
            continue
        assert "Offene Fragen zu dieser Verordnung" in html, r["id"]
        assert f"offene_punkte.md#{_anker(ueberschrift)}" in html, r["id"]
        assert f"### {ueberschrift}" in doku, ueberschrift


# --- Sitemap und Dataset --------------------------------------------------------------------------------------


def test_genau_ein_dataset_eintrag(seiten):
    """Mehrere Dataset-Einträge für denselben Datensatz konkurrieren miteinander (docs/WEB.md)."""
    mit = [p for p, h in seiten.items() if '"@type":"Dataset"' in h]
    assert mit == ["daten/"], mit
    for pfad, html in seiten.items():
        if pfad == "daten/":
            continue
        assert '"isPartOf"' in html, pfad


def test_sitemap_enthaelt_jede_seite():
    """Gebaute Sitemap gegen die gebauten Seiten – der Bau schreibt beide."""
    ziel: Path = ausgabe_dir() / "web"
    if not (ziel / "sitemap.xml").is_file():
        pytest.skip("Lesefassung nicht gebaut (python -m rsg2030 lesefassung)")
    xml = (ziel / "sitemap.xml").read_text(encoding="utf-8")
    seiten_auf_platte = sorted(
        str(p.parent.relative_to(ziel)).replace("\\", "/") + "/" for p in ziel.rglob("index.html") if p.parent != ziel
    )
    for pfad in seiten_auf_platte:
        assert f"/{pfad}</loc>" in xml, pfad
    assert xml.count("<url>") == len(seiten_auf_platte)


def test_lastmod_ist_der_tag_des_release():
    """Das Datum muss eine echte Änderung bedeuten – sonst gar keines (siehe `release_datum`)."""
    ziel: Path = ausgabe_dir() / "web"
    if not (ziel / "sitemap.xml").is_file():
        pytest.skip("Lesefassung nicht gebaut (python -m rsg2030 lesefassung)")
    xml = (ziel / "sitemap.xml").read_text(encoding="utf-8")
    stand = release_datum()
    if stand is None:
        assert "<lastmod>" not in xml, "ohne gesichertes Datum kein lastmod"
        return
    assert xml.count(f"<lastmod>{stand}</lastmod>") == xml.count("<url>")
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"date-released: {stand}" in cff
