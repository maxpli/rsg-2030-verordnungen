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
from rsg2030.darstellung import VORBEHALTE, lesbar, zahl
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
            lo, hi = float(str(fach["min"])), float(str(fach["max"]))
            # Rundung nach docs/WEB.md, «Zahlen auf der Seite» (Fälle in tests/test_web.py)
            for text in (lesbar(float(z.AAVE)), lesbar(float(z.VD), lo, hi)):
                assert f">{text}<" in html, (r["id"], z.Fach, text)
                geprueft += 1
    assert geprueft > 1000, geprueft


def test_soll_intervall_wie_im_richtwert(seiten, aufbau):
    """Das Soll-Intervall steht auf jeder Fachseite so da, wie der ÖSG es druckt (Textband S.39, eine Stelle):
    zeichengleich mit der Referenz der Richtwerte, die es von dort abschreibt."""
    richtwerte = pd.read_csv(ROOT / "oesg_methodik" / "referenz" / "oesg_planungsrichtwerte.csv", sep=";", dtype=str)
    gedruckt = {z.OESG_Code: (z.VDmin, z.VDmax) for z in richtwerte.itertuples()}
    for f in aufbau.faecher:
        html = seiten[f"fach/{f['id']}/"]
        min_t, max_t = gedruckt[str(f["id"])]
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


FUSSNOTE_AUF_DER_SEITE: dict[str, tuple[str, ...] | None] = {
    # Verweis in fussnoten.csv → woran man auf der Seite erkennt, dass die Fußnote berücksichtigt ist (eines genügt).
    # Wörter aus den Vorbehalten (rsg2030/darstellung.py) und dem Zuschnitt, nicht Fachnamen, die überall stehen.
    "METHODIK.md R5": ("AM + ZAE", "ZAE nicht getrennt ausgewiesen"),  # spitalsambulant = ZAE
    "Art «Fußnote» (KFO)": ("KFO in Oberösterreich",),  # OÖ: KFO nur als Fußnote, per Korrekturregel
    "R4 «ZMK und KFO je Land»": ("Wien rechnet mehr zu ZMK", "KFO in Oberösterreich"),  # was in ZMK steckt
    "OÖ spitalsambulant": ("OÖ PLAN spitalsambulant",),  # fortgeschriebenes IST
    "offene_punkte.md": ("offene_punkte.md",),  # Methodenfrage: Link unter «Offene Fragen»
    "planstellen_oegk_svs_bvaeb": None,  # betrifft IST-Planstellen; die zeigen die Seiten nicht
}


def test_jede_fussnote_die_werte_betrifft_steht_auf_der_seite(seiten, aufbau):
    """Die Fußnoten stehen nur gezählt da (docs/WEB.md, «Fußnoten»). Das ist nur vertretbar, wenn jede, die Werte
    betrifft oder eine offene Frage ist, auf der Seite ihrer Matrix berücksichtigt ist – als Vorbehalt, Zuschnitt
    oder Link. Eine neue Art Verweis lässt den Test scheitern: dann entscheiden, was die Seite dazu sagen muss."""
    from rsg2030.fussnoten import MIT_VERWEIS

    fn = aufbau.fussnoten
    pfade = {(str(r["ebene"]), str(r["id"])): aufbau.pfad(r) for r in aufbau.regionen}
    geprueft = 0
    for z in fn[fn["Einordnung"].isin(MIT_VERWEIS)].itertuples():
        merkmale = [m for k, m in FUSSNOTE_AUF_DER_SEITE.items() if k in str(z.Verweis)]
        assert merkmale, f"{z.Land} {z.Zeichen}: Verweis «{z.Verweis}» ohne Regel für die Seite"
        html = seiten[pfade[(str(z.Ebene), str(z.Region_ID))]]
        for m in merkmale:
            if m is not None:
                assert any(x in html for x in m), (z.Land, z.Region_ID, z.Zeichen, m)
                geprueft += 1
    assert geprueft > 30, geprueft


def test_fussnoten_gezaehlt_mit_link(seiten, aufbau):
    """Statt der Liste: Zahl der Fußnoten und die Seite im PDF – und kein Fußnotentext mehr auf der Seite. Der Verweis
    auf die Hinweise steht nur, wo eine Fußnote Werte betrifft; ein Leser soll nicht vergeblich suchen."""
    import html as html_mod

    from rsg2030.fussnoten import MIT_VERWEIS

    fn = aufbau.fussnoten
    mit, ohne = 0, 0
    for r in aufbau.regionen:
        seite = seiten[aufbau.pfad(r)]
        treffer = fn[(fn["Ebene"] == r["ebene"]) & (fn["Region_ID"].astype(str) == str(r["id"]))]
        if treffer.empty:
            continue
        n = len(treffer.drop_duplicates(["Zeichen", "Text"]))
        assert f"druckt zu dieser Matrix {n} Fußnote" in seite, r["id"]
        lang = [t for t in treffer["Text"] if len(str(t)) > 40]
        assert not any(html_mod.escape(str(t), quote=True) in seite for t in lang), r["id"]
        verweis = "Was davon die Werte hier betrifft" in seite
        erwartet = bool(treffer["Einordnung"].isin(MIT_VERWEIS).any())
        assert verweis == erwartet, r["id"]
        mit, ohne = mit + erwartet, ohne + (not erwartet)
    assert mit and ohne, (mit, ohne)


def test_korrekturregeln_nur_von_der_eigenen_ebene(seiten, aufbau):
    """Auf einer Seite stehen die Regeln ihrer Matrix, wörtlich und richtig gezählt – eine Regel nur für die
    Landesmatrix (Ebene BL, Region_ID «*») gehört nicht auf die Seite einer Region, und umgekehrt."""
    import html as html_mod

    k = aufbau.regeln
    ausgeschlossen = 0
    for r in aufbau.regionen:
        seite = seiten[aufbau.pfad(r)]
        passt = k["Land"].isin([str(r["land"]), "*"]) & k["Region_ID"].astype(str).isin([str(r["id"]), "*"])
        ebene = k["Ebene"].isin([str(r["ebene"]), "*"])
        eigene, andere = k[passt & ebene], k[passt & ~ebene]
        texte = set(eigene["Begruendung"])
        for t in texte:
            assert html_mod.escape(str(t), quote=True) in seite, (r["id"], str(t)[:60])
        for t in set(andere["Begruendung"]) - texte:
            assert html_mod.escape(str(t), quote=True) not in seite, (r["id"], str(t)[:60])
            ausgeschlossen += 1
        if len(eigene):
            assert re.search(rf"\b{len(eigene)} dokumentierte", seite), r["id"]
        assert not re.search(r"\b1 Werte\b|\b1 dokumentierten? Regeln\b", seite), r["id"]
    assert ausgeschlossen > 0


def test_bundesland_nennt_die_ebene_des_soll_intervalls(seiten, aufbau):
    """Der ÖSG setzt das Soll-Intervall je Versorgungsregion (Textband S.38): Auf jeder Seite eines Bundeslands steht
    das einmal bei der Tabelle, auf den Seiten der Regionen nicht (docs/DATEN.md, Fallstrick 11)."""
    text = VORBEHALTE["soll_je_region"].text
    for r in aufbau.regionen:
        assert seiten[aufbau.pfad(r)].count(text) == (1 if r["ebene"] == "BL" else 0), r["id"]


def test_jede_seite_sagt_dass_die_vd_gerechnet_ist(seiten):
    """Über der Tabelle steht nur die Verordnung, und die Matrizen haben keine VD-Zeile: Unter jeder Tabelle der VD
    steht deshalb, dass sie gerechnet ist und woher die Bevölkerung kommt (docs/WEB.md, «Was auf die Seite gehört»)."""
    for pfad, html in seiten.items():
        assert html.count("Die VD steht nicht in der Verordnung. Sie ist gerechnet") >= 1, pfad
        assert "Statistik Austria und ÖROK" in html, pfad
    assert "zu jeder Zahl" not in seiten["daten/"]


def test_bezirke_nach_kennzahl(seiten, aufbau):
    """Die Bezirke stehen wie in der Regionalen Gliederung des ÖSG, nicht alphabetisch («Wien 2.» vor «Wien 10.»)."""
    g = aufbau.regionen_csv
    for vr in g["VR"].unique():
        soll = g[g["VR"] == vr].sort_values("Bezirk")["Bezirk_Name"].astype(str).tolist()
        assert aufbau.bezirke(str(vr)) == soll, vr
    wien = seiten["vr/91/"]
    assert wien.index("Wien 2., Leopoldstadt") < wien.index("Wien 10., Favoriten")


def test_fachseite_nennt_die_ist_jahre_im_kopf(seiten, aufbau):
    """Spaltenköpfe mit dem IST-Jahr (docs/WEB.md, «Aufbau»); auf Fachseiten die Jahre der Länder, die das Fach haben."""
    tab = pd.read_csv(ausgabe_dir() / VERSORGUNGSDICHTE_DATEI, dtype={"Region_ID": str})
    ist = tab[(tab["Ebene"] == "VR") & (tab["Abschnitt"] == "IST") & (tab["Zeile_ID"] == "insgesamt")]
    for f in aufbau.faecher:
        jahre = "/".join(sorted({str(int(j)) for j in ist.loc[ist["Fach"] == f["id"], "Jahr"]}))
        html = seiten[f"fach/{f['id']}/"]
        assert f"VD IST {jahre}<" in html and f"ÄAVE IST {jahre}<" in html, (f["id"], jahre)


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


def _ld_bloecke(html: str) -> list[dict]:
    """Alle JSON-LD-Blöcke einer Seite, geparst – ein Block, der kein gültiges JSON ist, lässt den Test scheitern."""
    import json

    bloecke = re.findall(r'<script type="application/ld\+json">\n(.*?)\n</script>', html, re.S)
    knoten: list[dict] = []
    for b in bloecke:
        d = json.loads(b)
        knoten += d.get("@graph", [d])
    return knoten


def test_genau_ein_dataset_eintrag(seiten):
    """Ein Dataset für den ganzen Datensatz, auf /daten/ (docs/WEB.md, «Strukturierte Daten»). Die anderen Seiten
    zeigen einen Ausschnitt daraus (`isBasedOn`), ihr Hauptthema ist nicht der Datensatz (kein `mainEntity`)."""
    dataset_id = f"{BASIS}/daten/#dataset"
    mit = [p for p, h in seiten.items() if any(k["@type"] == "Dataset" for k in _ld_bloecke(h))]
    assert mit == ["daten/"], mit
    for pfad, html in seiten.items():
        seite = next(k for k in _ld_bloecke(html) if k["@type"] == "WebPage")
        assert seite["isPartOf"] == {"@id": f"{BASIS}/#website"}, pfad
        if pfad == "daten/":
            assert seite["mainEntity"] == {"@id": dataset_id}
        else:
            assert seite["isBasedOn"] == {"@id": dataset_id} and "mainEntity" not in seite, pfad


def test_adresse_der_seiten_ist_die_eigene_domain():
    """Die Adresse steht in canonical, Sitemap, robots.txt und jedem JSON-LD-Block, und die alte github.io-Adresse
    leitet dorthin um (docs/WEB.md, «Die Adressen sind endgültig»). Ändert sie sich still, verlieren indexierte Seiten
    ihren Platz – deshalb steht sie hier ein zweites Mal."""
    from rsg2030.lesefassung import BASIS_STANDARD

    assert BASIS_STANDARD == "https://rsg.loesungswerk.at"


def test_dataset_vollstaendig_und_downloads_im_release(seiten):
    """Was Google Dataset Search braucht, und jeder Download liegt wirklich im Release – release.yml hängt ihn an."""
    from rsg2030.lesefassung import PERSON, RELEASE_DATEIEN

    ds = next(k for k in _ld_bloecke(seiten["daten/"]) if k["@type"] == "Dataset")
    for feld in ("name", "description", "license", "creator", "version", "variableMeasured", "distribution"):
        assert ds.get(feld), feld
    assert len(ds["description"]) >= 50
    assert ds["creator"] == PERSON and PERSON["@id"] == "https://loesungswerk.at/#max-plischke"
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    liste = re.search(r'dateien="([^"]+)"', workflow)
    assert liste, "release.yml: Liste «dateien» nicht gefunden"
    angehaengt = set(liste.group(1).split())
    for name, _ in RELEASE_DATEIEN:
        assert name in angehaengt, name
    assert [d["name"] for d in ds["distribution"]] == [n for n, _ in RELEASE_DATEIEN]


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


def test_robots_nennt_die_sitemap():
    """Die eigene Domain erlaubt eine robots.txt an der Wurzel; sie zeigt auf die Sitemap derselben Adresse."""
    from rsg2030.lesefassung import Aufbau, _robots

    text = _robots(Aufbau(BASIS))
    assert f"Sitemap: {BASIS}/sitemap.xml" in text and "Disallow" not in text


def test_seiten_haben_die_fusszeile_des_dashboards(seiten, aufbau):
    """Dieselbe Fußzeile wie im Dashboard, aus derselben Funktion – nicht nur ähnlich."""
    from rsg2030.darstellung import fusszeile

    meta = aufbau.daten["meta"]
    erwartet = fusszeile(str(meta["repo"]), str(meta["version"]), str(meta["commit"]))
    for pfad, html in seiten.items():
        assert erwartet in html, pfad


def test_oesg_link_zeigt_auf_die_seite_der_richtwerte(seiten):
    """Der Link «ÖSG-Textband S.39» springt auf die Seite, von der die Soll-Intervalle stammen: dieselbe Seite wie in
    der Referenz der Richtwerte, und auf die Datei, die quellen.csv als Textband führt."""
    from rsg2030.lesefassung import OESG_TEXTBAND, RICHTWERTE_SEITE, oesg_textband_url

    richtwerte = pd.read_csv(ROOT / "oesg_methodik" / "referenz" / "oesg_planungsrichtwerte.csv", sep=";", dtype=str)
    mit_intervall = richtwerte[richtwerte["VDmin"].notna()]
    assert len(mit_intervall) and (mit_intervall["Quelle"].str.endswith(f"S.{RICHTWERTE_SEITE}")).all()
    url = oesg_textband_url(RICHTWERTE_SEITE)
    assert url.startswith("https://ogd.ris.bka.gv.at/") and url.endswith(f"{Path(OESG_TEXTBAND).name}#page=39")
    fachseiten = [h for p, h in seiten.items() if p.startswith("fach/")]
    assert fachseiten and all(f'href="{url}"' in h for h in fachseiten)


def test_keine_vd_steht_gerundet_auf_der_grenze_obwohl_ausserhalb(aufbau, seiten):
    """Liegt eine VD außerhalb, steht sie nie gerundet gleich wie VDmin/VDmax da (Burgenland-Nord, PUL: 1,59 statt 1,6
    neben 1,6–3,0). Geprüft an jeder Zelle mit Lage, über die Funktion, die die Tabellen füllen."""
    from rsg2030.lesefassung import _vd

    geprueft = 0
    for f in aufbau.faecher:
        lo, hi = float(str(f["min"])), float(str(f["max"]))
        for r in aufbau.regionen:
            for ab in ("IST", "PLAN"):
                z = aufbau.zelle(str(r["id"]), ab, str(f["id"]))
                if z is None or z.lage not in ("unter", "über"):
                    continue
                text = _vd(aufbau, str(r["id"]), ab, f)
                if text == "0":
                    continue  # nichts geplant, liegt nie auf einer Grenze
                stellen = len(text.split(",")[1])
                assert text != zahl(lo if z.lage == "unter" else hi, stellen), (r["id"], ab, f["id"], text)
                geprueft += 1
    assert geprueft > 300
    assert '<td class="num">1,59</td>' in seiten["vr/11/"]


def test_null_steht_als_null_und_fast_null_nicht_als_null(seiten):
    """Genau 0 steht als «0», nie «0,0» oder «0,00»; ein Wert ungleich 0 nie gerundet als 0 (docs/WEB.md)."""
    for pfad, html in seiten.items():
        assert not re.search(r'class="num">−?0,0+<', html), pfad
    assert '<td class="num">0</td>' in seiten["vr/11/"]  # MKG, nichts geplant


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
