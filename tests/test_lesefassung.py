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
    _kennungen,
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
        # Interne Links bleiben im selben Fenster – geprüft im Tag selbst, nicht in den Zeichen danach (dort steht
        # oft schon der nächste, externe Link)
        for url, rest in re.findall(r'<a href="(\.\./[^"]+|[a-z]+/[^":]*)"([^>]*)>', html):
            assert "target=" not in rest, (pfad, url)


def test_jede_seite_ist_von_der_indexseite_erreichbar(seiten):
    """Ohne Verlinkung findet ein Crawler die Unterseiten nur über die Sitemap – beides soll stimmen."""
    index = seiten["daten/"]
    for pfad in seiten:
        if pfad == "daten/":
            continue
        assert f'href="../{pfad}"' in index, pfad


def test_brotkrumen_und_beide_wege(seiten, aufbau):
    """Jede Seite zeigt, wo sie steht, und führt in beide Richtungen: nachschlagen und vergleichen."""
    for pfad, html in seiten.items():
        assert '<nav class="bereiche"' in html, pfad
        assert "Nachschlagen: Regionen und Fächer" in html and "Vergleichen: interaktive Matrix" in html, pfad
        if pfad == "daten/":
            continue
        assert '<nav class="pfad"' in html and '"@type":"BreadcrumbList"' in html, pfad
    for r in aufbau.regionen:
        assert f'?region={r["slug"]}"' in seiten[aufbau.pfad(r)], r["id"]
    for f in aufbau.faecher:
        assert f'?fach={f["id"]}"' in seiten[f"fach/{f['id']}/"], f["id"]


def test_jeder_vorbehalt_steht_einmal_bei_der_tabelle(seiten, aufbau):
    """Was für eine Zelle gilt, steht unter der Tabelle – einmal, nicht je Fach wiederholt; jede Zahl an einer
    Zeile hat ihren Vorbehalt darunter («Teil von» sagt der Satz zu PUL und KFO)."""
    for r in aufbau.regionen:
        seite = seiten[aufbau.pfad(r)]
        liste = re.search(r'<ul class="vorbehalte">(.*?)</ul>', seite, re.S)
        texte = set()
        for f in aufbau.faecher:
            for kennung, text in _kennungen(aufbau, str(r["id"]), str(f["id"])):
                if kennung != "teil_von":
                    texte.add(text)
        if not texte:
            continue
        assert liste, r["id"]
        for text in texte:
            assert liste.group(1).count(text) == 1, (r["id"], text[:60])
        zeichen = set(re.findall(r"<sup>(\d+)</sup>", seite.split('<ul class="vorbehalte">')[0]))
        unten = set(re.findall(r"<li><sup>(\d+)</sup>", liste.group(1)))
        assert zeichen == unten, (r["id"], zeichen, unten)


def test_eine_einheit_je_tabelle(seiten, aufbau):
    """Drei Tabellen, je eine Einheit: Versorgungsdichte (IST und PLAN, Soll-Intervall, Lage), ÄAVE mit dem Abstand
    zum Soll-Intervall, Sachleistungsstellen. Die Stellen (extramural) nie als Spalte neben den ÄAVE (ganze
    Sachleistung), dazu der Hinweis, beide nicht gegeneinander zu rechnen (docs/METHODIK.md, «Begriffe»)."""
    for pfad, html in seiten.items():
        if not pfad.startswith(("bl/", "vr/", "fach/")):
            continue
        tabellen = html.split("</table>")
        vd, aave = tabellen[0].split("<thead>")[1], tabellen[1].split("<thead>")[1]
        assert "VD IST" in vd and "VD PLAN 2030" in vd and "ÄAVE" not in vd and "Abstand" not in vd, pfad
        assert (
            "ÄAVE PLAN 2030" in aave and "Abstand PLAN 2030 zum Soll-Intervall" in aave and "Sachleistungs" not in aave
        ), pfad
        assert html.index('id="vd"') < html.index('id="aave"') < html.index('id="stellen"'), pfad
        assert "nicht gegeneinander rechnen" in html, pfad
    for r in aufbau.regionen:
        html = seiten[aufbau.pfad(r)]
        assert ("Wien bewertet zusätzliche Sachleistungsstellen" in html) == (r["land"] == "Wien"), r["id"]


def test_fachseite_zeigt_auch_zusaetzliche_stellen(seiten, aufbau):
    """Im PLAN sind zusätzliche Stellen eigene Stellen (docs/DATEN.md, Tabelle Stellen): Wo ein Träger in einem Fach
    irgendwo zusätzliche Stellen plant, hat die Fachseite die Spalte – sonst verzerrt der Vergleich der Regionen."""
    s = aufbau.stellen
    plan = s[(s["Ebene"] == "VR") & (s["Abschnitt"] == "PLAN") & (s["Stellen"].fillna(0) != 0)]
    for f in aufbau.faecher:
        html = seiten[f"fach/{f['id']}/"].split('id="stellen"')[1].split("</table>")[0]
        for zeile, kopf in (("slst_zus_svs", "zusätzlich SVS"), ("slst_zus_bvaeb", "zusätzlich BVAEB")):
            erwartet = not plan[(plan["Fach"] == f["id"]) & (plan["Zeile_ID"] == zeile)].empty
            assert (kopf in html) == erwartet, (f["id"], zeile)


def test_jede_seite_nennt_die_quellen_wie_die_lizenz_verlangt(seiten):
    """Bevölkerung (Statistik Austria, ÖROK) steht unter CC BY 4.0 und geht bearbeitet ein: Namensnennung auf jeder
    Seite, im Wortlaut von LIZENZ_DATEN.md."""
    for pfad, html in seiten.items():
        assert "Statistik Austria – data.statistik.gv.at (CC BY 4.0, bearbeitet)" in html, pfad
        assert "ÖROK-Prognose 2021 (CC BY 4.0, bearbeitet)" in html and "ÖSG 2023" in html, pfad


def test_keine_null_mit_vorzeichen(seiten):
    """«−0,0» sähe aus wie ein Fehler; gerundet auf null stehen zwei Nachkommastellen da."""
    for pfad, html in seiten.items():
        assert not re.search(r"[−+]0,0<", html), pfad


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
    """Der wichtigste Vorbehalt steht auf jeder Seite, bei den Zahlen: nur Sachleistung, ohne Wahlärzt:innen,
    und dass der ÖSG innerhalb des Intervalls keinen Unterschied macht (docs/DATEN.md, Fallstricke 1 und 11)."""
    for pfad, html in seiten.items():
        assert "Gezählt ist nur die Sachleistung" in html, pfad
        assert "ohne Wahlärzt:innen" in html, pfad
        assert "Innerhalb des Intervalls macht der ÖSG keinen Unterschied" in html, pfad


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
