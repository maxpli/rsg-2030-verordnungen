"""Lesefassung: statische Seiten zu den veröffentlichten Tabellen, ohne JavaScript.

Zweck: Die Zahlen sollen überhaupt in maschinenlesbarer Form existieren. In den Verordnungs-PDFs sind sie für
Suchmaschinen und Abrufsysteme unerreichbar (oft Bildseiten, immer Querformat), und auf dem Dashboard entstehen sie
erst im Browser. Hier steht jede Zahl als Text im HTML. Was es nirgends sonst gibt, ist nicht die Abschrift, sondern
der Vergleich: Versorgungsdichte, Lage zum Soll-Intervall des ÖSG, Position und ÄAVE-Abstand.

Gebaut werden (Adressen sind endgültig, GitHub Pages kann nicht umleiten – deshalb Nummern und Kürzel, keine Namen):

    /daten/        Indexseite: alle Zeilen «insgesamt» in einer Tabelle, dazu die Sachleistungsstellen
    /bl/<kurz>/    9 Bundesländer
    /vr/<nr>/      32 Versorgungsregionen
    /fach/<id>/    17 Fächer (dieselbe Tabelle gekippt)
    /sitemap.xml   alle Seiten

Dieselben Darstellungsregeln wie das Dashboard, aus derselben Schicht: Satz in Worten und Vorbehalte kommen aus
`rsg2030.darstellung`, die Werte und ihre Herkunft aus `rsg2030.web.baue_daten` – also aus genau dem, was auch
`data.json` füllt. Prosa ist ausschließlich vorlagengesteuert; die einzigen festen Texte sind Überschriften,
Spaltenköpfe und die Hinweise, die docs/WEB.md begründet.

    python -m rsg2030 lesefassung
"""

from __future__ import annotations

import argparse
import html
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from oesg_methodik.bevoelkerung import lade_regionen
from rsg2030.abgleich import gleiche_ab, paketversion
from rsg2030.analyse_eingang import lade_matrix_long
from rsg2030.config import LONG_DATEI, STELLEN_DATEI, VERSORGUNGSDICHTE_DATEI, ausgabe_dir
from rsg2030.darstellung import KEIN_WERT, VORBEHALTE, Zelle, satz, zahl
from rsg2030.korrekturen import lade_regeln
from rsg2030.protokoll import einrichten, schreibe_laufprotokoll
from rsg2030.web import LAND_SLUG, baue_daten, repo_url, seiten_commit, web_dir

log = logging.getLogger(__name__)

BASIS_STANDARD = "https://maxpli.github.io/rsg-2030-verordnungen"
"""Adresse, unter der die Seiten liegen – für `canonical` und die Sitemap. Beim Umzug auf eine eigene Domain nur
hier und im Aufruf (`--basis`) ändern; die Pfade bleiben."""

VERBOTEN = ("unterversorg", "versorgungsmangel", "versorgungslücke", "ärztemangel", "mangelversorgung")
"""Urteile über die Versorgung, die die Daten nicht tragen (docs/DATEN.md, Fallstricke 1 und 11). Der Bau bricht
ab, wenn eines im erzeugten HTML steht.

Gesucht wird nach dem Wortstamm, damit auch «Unterversorgung» und «unterversorgten Regionen» auffallen – auch in
einer Verneinung: Ein Abrufsystem, das die Seite zusammenfasst, nimmt das Wort mit und die Verneinung nicht.
Nicht verboten ist «Lücke» allein: So heißt die *Art* einer Korrekturregel, wenn eine Zelle im PDF leer ist
(`korrekturen.csv`), und diese Begründungen stehen wörtlich auf der Seite."""

ZEILEN_VD = ("insgesamt", "extramural", "spitalsambulant", "pve")
"""Zeilen der Tabelle Versorgungsdichte, die die Seiten zeigen (METHODIK R10). Soll-Intervall nur bei `insgesamt`."""

STELLEN_PLAN = ("slst_gemeinsam", "slst_zus_oegk", "slst_zus_svs", "slst_zus_bvaeb")
"""Stellen-Zeilen, die auf die Seiten kommen: nur PLAN. IST-Planstellen und PLAN-Sachleistungsstellen zählen
Verschiedenes, ein Vergleich bräuchte Annahmen (METHODIK, «Stellen – nicht in der Tabelle Versorgungsdichte»)."""

STELLEN_KOPF = {
    "slst_gemeinsam": "gemeinsam (alle Träger)",
    "slst_zus_oegk": "zusätzlich ÖGK",
    "slst_zus_svs": "zusätzlich SVS",
    "slst_zus_bvaeb": "zusätzlich BVAEB",
}
"""Spaltenköpfe der Stellen-Tabelle, nach der gedruckten Beschriftung der Vorlage (Tabellenband S.239)."""


def esc(text: object) -> str:
    """Text für HTML; None wird zum Gedankenstrich der Seite."""
    return "–" if text is None else html.escape(str(text), quote=True)


@dataclass(frozen=True)
class Seite:
    """Eine erzeugte Seite: Pfad ohne führenden Schrägstrich, Titel, Beschreibung und der Rumpf."""

    pfad: str
    titel: str
    beschreibung: str
    rumpf: str
    dashboard: str = ""
    """Abfrageteil für den Link auf das Dashboard, z. B. «?region=41» – vorbelegter Zustand statt Standardansicht."""


def _long_je_zelle(long: pd.DataFrame) -> pd.DataFrame:
    """Tabelle Planungsmatrizen, auf die Spalten reduziert, die die Seiten zitieren."""
    return long[["Land", "Ebene", "Region_ID", "Abschnitt", "Zeile_ID", "Fach", "Roh", "Wert", "Quelle", "Regel"]]


def lade_tabellen() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Die drei veröffentlichten Tabellen aus `daten_ergebnis/`, je gegen die Version des Pakets geprüft."""
    pfade = [ausgabe_dir() / n for n in (VERSORGUNGSDICHTE_DATEI, STELLEN_DATEI, LONG_DATEI)]
    for datei in pfade:
        if not datei.is_file():
            raise FileNotFoundError(f"{datei} fehlt: erst «python -m rsg2030 alles» oder die Dateien des Release")
        if gleiche_ab(datei) is not True:
            raise ValueError(f"{datei.name} ist nicht die Version {paketversion()}: Seiten nicht gebaut")
    vd, stellen, long = (pd.read_csv(p, dtype={"Region_ID": str}) for p in pfade)
    return vd, stellen, long


class Aufbau:
    """Alles, was die Seiten brauchen, einmal geladen: die Tabellen, die geteilte Darstellungsschicht und die
    Eingaben, die den Apparat tragen (Fußnoten, Korrekturregeln, bekannte Abweichungen)."""

    def __init__(self, basis: str) -> None:
        self.basis = basis.rstrip("/")
        self.vd, self.stellen, self.long = lade_tabellen()
        self.daten = baue_daten(
            self.vd,
            lade_regionen(),
            pd.read_csv(web_dir() / "kacheln.csv", dtype=str),
            pd.read_csv(web_dir() / "faecher.csv", dtype=str),
            lade_matrix_long(ausgabe_dir() / LONG_DATEI),
            lade_regeln(),
            {"version": paketversion(), "commit": seiten_commit(), "repo": repo_url()},
        )
        self.faecher = cast("list[dict[str, object]]", self.daten["faecher"])
        self.regionen = cast("list[dict[str, object]]", self.daten["regionen"])
        self.meta = cast("dict[str, str]", self.daten["meta"])
        self.werte = cast("dict[str, list[object]]", self.daten["werte"])
        self._vorbehalte = cast("dict[str, list[list[object]]]", self.daten["vorbehalte"])
        self._kein_wert = cast("dict[str, list[object]]", self.daten["kein_wert"])
        self._matrizen = cast("dict[str, list[object]]", self.daten["matrizen"])
        self._quellen = cast("list[list[object]]", self.daten["quellen"])
        self.regionen_csv = lade_regionen()
        eingaben = Path(str(web_dir().parent / "rsg2030" / "eingaben" / "2026"))
        self.fussnoten = pd.read_csv(eingaben / "fussnoten.csv", dtype={"Region_ID": str})
        self.regeln = lade_regeln()
        self.abweichungen = pd.read_csv(eingaben / "bekannte_abweichungen.csv", dtype={"Region_ID": str})

    # --- Zugriff auf die geteilte Schicht ---------------------------------------------------------------------

    def zelle(self, rid: str, abschnitt: str, fach: str) -> Zelle | None:
        w = self.werte.get(f"{rid}|{abschnitt}|{fach}")
        if w is None:
            return None
        return Zelle(
            cast("str | None", w[4]), cast("float | None", w[6]), cast("str | None", w[7]), cast("int | None", w[3])
        )

    def wert(self, rid: str, abschnitt: str, fach: str, i: int) -> object:
        w = self.werte.get(f"{rid}|{abschnitt}|{fach}")
        return None if w is None else w[i]

    def vorbehalte_roh(self, rid: str, abschnitt: str, fach: str) -> list[list[object]]:
        """Die Vorbehalte dieser Zelle als Kennung und Argumente, wie `data.json` sie trägt."""
        return self._vorbehalte.get(f"{rid}|{abschnitt}|{fach}", [])

    def vorbehalte(self, rid: str, abschnitt: str, fach: str) -> list[tuple[int, str]]:
        """Die Vorbehalte dieser Zelle als (Fallstrick, Text) – Texte und Auswahl aus `rsg2030.darstellung`."""
        out = []
        for kennung, *args in self._vorbehalte.get(f"{rid}|{abschnitt}|{fach}", []):
            fallstrick, text = VORBEHALTE[str(kennung)]
            for i, a in enumerate(args):
                text = text.replace(f"{{{i}}}", esc(a))
            out.append((fallstrick, text))
        return out

    def kein_wert(self, rid: str, abschnitt: str, fach: str) -> str | None:
        g = self._kein_wert.get(f"{rid}|{abschnitt}|{fach}")
        if g is None:
            return None
        kennung, *args = g
        text = KEIN_WERT[str(kennung)]
        for i, a in enumerate(args):
            text = text.replace(f"{{{i}}}", esc(a))
        return text

    def quelle(self, rid: str, abschnitt: str) -> tuple[str, int, str, str] | None:
        """PDF-Name, Seite, Adresse der Datei und Adresse des RIS-Dokuments dieser Matrix."""
        m = self._matrizen.get(f"{rid}|{abschnitt}")
        if m is None:
            return None
        pdf, ris, datei = self._quellen[int(str(m[0]))]
        return str(pdf), int(str(m[1])), str(datei), str(ris)

    # --- Namen und Adressen ----------------------------------------------------------------------------------

    def stellen_wert(self, rid: str, fach: str) -> tuple[object, object]:
        """Gemeinsame Sachleistungsstellen 2030 dieses Fachs und die Obergrenze für vertragsärztliche Planstellen."""
        s = self.stellen
        treffer = s[
            (s["Region_ID"] == rid)
            & (s["Abschnitt"] == "PLAN")
            & (s["Zeile_ID"] == "slst_gemeinsam")
            & (s["Fach"] == fach)
        ]
        if treffer.empty:
            return None, None
        z = treffer.iloc[0]
        return z["Stellen"], (None if pd.isna(z["Max_VAEP_Stellen"]) else z["Max_VAEP_Stellen"])

    def quellen_liste(self) -> list[list[object]]:
        """Je Verordnungs-PDF Dateiname, RIS-Adresse und Adresse der Datei (aus `quellen.csv` abgeleitet)."""
        return self._quellen

    def region(self, rid: str) -> dict[str, object]:
        return next(r for r in self.regionen if str(r["id"]) == rid)

    def pfad(self, r: dict[str, object]) -> str:
        return f"bl/{LAND_SLUG[str(r['land'])]}/" if r["ebene"] == "BL" else f"vr/{r['id']}/"

    def fach(self, fid: str) -> dict[str, object]:
        return next(f for f in self.faecher if str(f["id"]) == fid)

    def bezirke(self, rid: str) -> list[str]:
        z = self.regionen_csv[self.regionen_csv["VR"].astype(str) == rid]
        return sorted(set(z["Bezirk_Name"].astype(str)))

    def vr_des_landes(self, land_name: str) -> list[str]:
        z = self.regionen_csv[self.regionen_csv["Bundesland"] == land_name]
        return sorted(set(z["VR"].astype(str)), key=int)

    def hoch(self, pfad: str) -> str:
        """Weg von dieser Seite zur Wurzel («../../» für «vr/41/»); ohne absolute Pfade läuft die Seite auch
        lokal und unter einem Unterordner wie auf GitHub Pages."""
        return "../" * len([t for t in pfad.strip("/").split("/") if t])

    def stil(self, pfad: str) -> str:
        return f"{self.hoch(pfad)}lesefassung.css"


# --- Bausteine ------------------------------------------------------------------------------------------------

LAGE_WORT = {"unter": "unter dem Soll-Intervall", "im": "im Soll-Intervall", "über": "über dem Soll-Intervall"}
"""Lage in Worten. «unter» heißt nicht «unterversorgt» (docs/DATEN.md, Fallstrick 1) – das sagt der Kasten
«Was diese Zahlen nicht sagen» auf jeder Seite, und der Satz je Fach nennt die Sachleistung ausdrücklich."""

TEILMENGEN_HINWEIS = (
    '<p class="t2">Die Fächer PUL (Pulmologie) und KFO (Kieferorthopädie) stecken bereits in IM bzw. ZMK und '
    "haben zusätzlich ein eigenes Soll-Intervall des ÖSG. Eine Summe über alle Fächer zählt sie deshalb doppelt; "
    "für eine Summe die beiden weglassen.</p>"
)
"""Steht unter jeder Tabelle, die Fächer auflistet (docs/DATEN.md, Fallstrick 4)."""

ZUSCHNITT_ZEICHEN = "◆"
"""Zeichen an Zeilen, deren Zuschnitt vom Fach abweicht; aufgelöst in einer Zeile unter der Tabelle. Ohne diese
Angabe vergleicht man «Innere Medizin Tirol» mit «Innere Medizin Wien», wo einmal die Pulmologie drinsteckt."""


def num(x: object, stellen: int = 1) -> str:
    """Wie `darstellung.zahl`, aber für die Werte aus `data.json`, die als `object` ankommen."""
    if x is None or (isinstance(x, float) and x != x):
        return "–"
    return zahl(float(str(x)), stellen)


def _tausend(x: object) -> str:
    """Ganze Zahl mit Punkt als Tausendertrennzeichen, wie im deutschsprachigen Raum üblich."""
    if x is None:
        return "–"
    return f"{round(float(str(x))):,}".replace(",", ".")


def _stellen_vd(f: dict[str, object]) -> int:
    """Nachkommastellen der Versorgungsdichte: zwei, wo das Intervall schmaler als 2 ist (KJP, MKG)."""
    return 2 if float(str(f["max"])) < 2 else 1


def _zuschnitt_abweichend(zuschnitt: str | None, fach: str) -> bool:
    return bool(zuschnitt) and str(zuschnitt).strip() != fach


def _tabelle_vd(a: Aufbau, rid: str) -> str:
    """Versorgungsdichte im Vergleich zum Soll-Intervall, IST und PLAN, je Fach dieser Region."""
    zeilen, zuschnitte, fehlen = [], [], []
    for f in a.faecher:
        fid, dg = str(f["id"]), _stellen_vd(f)
        i, p = a.zelle(rid, "IST", fid), a.zelle(rid, "PLAN", fid)
        if i is None and p is None:
            grund = a.kein_wert(rid, "PLAN", fid)
            fehlen.append(f"<b>{esc(fid)}</b> {esc(f['name'])}: {grund or 'kein Wert in dieser Matrix.'}")
            continue
        mark = ZUSCHNITT_ZEICHEN if _zuschnitt_abweichend(p.zuschnitt if p else None, fid) else ""
        if mark and p is not None and str(p.zuschnitt) not in zuschnitte:
            zuschnitte.append(str(p.zuschnitt))
        zeilen.append(
            "<tr>"
            f'<th scope="row">{esc(f["name"])} <span class="t2">({esc(fid)}{mark})</span></th>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 1))}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 1))}</td>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 0), dg)}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 0), dg)}</td>'
            f'<td class="num">{num(f["min"], dg)}–{num(f["max"], dg)}</td>'
            f"<td>{esc(LAGE_WORT.get(str(p.lage), '–')) if p else '–'}</td>"
            f'<td class="num">{_abstand(p)}</td>'
            "</tr>"
        )
    jahr = a.wert(rid, "IST", "AM", 3)
    kopf = (
        "<thead><tr><th>Fach</th>"
        f'<th scope="col">ÄAVE IST {esc(jahr)}</th><th scope="col">ÄAVE PLAN 2030</th>'
        f'<th scope="col">VD IST {esc(jahr)}</th><th scope="col">VD PLAN 2030</th>'
        '<th scope="col">Soll-Intervall</th><th scope="col">Lage PLAN 2030</th>'
        '<th scope="col">ÄAVE-Abstand PLAN</th></tr></thead>'
    )
    hinweise = [
        '<p class="t2">ÄAVE-Abstand: so viele ÄAVE Sachleistung fehlen bis zur Untergrenze (−) bzw. liegen '
        "über der Obergrenze (+).</p>"
    ]
    hinweise.append(_zuschnitt_zeile(zuschnitte))
    hinweise.append(TEILMENGEN_HINWEIS)
    if fehlen:
        hinweise.append('<p class="t2">Ohne Wert in dieser Matrix: ' + " ".join(fehlen) + "</p>")
    titel = _beschriftung(
        f"Versorgungsdichte je Fach, {esc(a.region(rid)['name'])}: ÄAVE und Versorgungsdichte im IST "
        f"{esc(jahr)} und im PLAN 2030, im Vergleich zum Versorgungsdichte-Soll-Intervall des ÖSG"
    )
    return (
        f'<div class="scroll"><table class="t">{titel}{kopf}<tbody>{"".join(zeilen)}</tbody></table></div>'
        + "".join(hinweise)
    )


def _beschriftung(text: str) -> str:
    """`<caption>`: das Stück Metadatum, mit dem Extraktoren und Bildschirmleser eine Tabelle benennen. Ohne das
    steht die Überschrift nur daneben, und die Zuordnung muss erraten werden (docs/WEB.md, «Lesefassung»)."""
    return f"<caption>{text}</caption>"


def _zuschnitt_zeile(zuschnitte: list[str]) -> str:
    """Das Zeichen an den Zeilen auflösen, in einer Zeile unter der Tabelle – keine weitere Spalte voll Kürzel."""
    if not zuschnitte:
        return ""
    return (
        f'<p class="t2">{ZUSCHNITT_ZEICHEN} Diese Zeile ist im Zuschnitt des ÖSG gerechnet, nicht als Spalte der '
        "Matrix: " + "; ".join(esc(z) for z in zuschnitte) + ". Ein Fach bedeutet hier also nicht überall dasselbe "
        "wie im PDF – ohne diese Angabe vergleicht man Innere Medizin mit und ohne Pulmologie.</p>"
    )


def _abstand(z: Zelle | None) -> str:
    if z is None or z.aave_abstand is None:
        return "–"
    v = float(z.aave_abstand)
    return "0" if v == 0 else ("+" if v > 0 else "") + num(v)


def _tabelle_stellen(a: Aufbau, rid: str) -> str:
    """Sachleistungsstellen 2030 je Fach – nur PLAN, mit dem Maximalanteil als Stellenzahl."""
    s = a.stellen[(a.stellen["Region_ID"] == rid) & (a.stellen["Abschnitt"] == "PLAN")]
    if s.empty:
        return ""
    werte = {(r.Zeile_ID, r.Fach): r for r in s.itertuples()}
    zeilen: list[str] = []
    zuschnitte: list[str] = []
    for f in a.faecher:
        fid = str(f["id"])
        if not any((z, fid) in werte for z in STELLEN_PLAN):
            continue
        zellen = []
        for z in STELLEN_PLAN:
            r = werte.get((z, fid))
            zellen.append(f'<td class="num">{num(r.Stellen) if r is not None else "–"}</td>')
        g = werte.get(("slst_gemeinsam", fid))
        maxv = None if g is None or pd.isna(g.Max_VAEP_Stellen) else g.Max_VAEP_Stellen
        zuschnitt = None if g is None else str(g.Zuschnitt)
        mark = ZUSCHNITT_ZEICHEN if _zuschnitt_abweichend(zuschnitt, fid) else ""
        if mark and zuschnitt is not None and zuschnitt not in zuschnitte:
            zuschnitte.append(zuschnitt)
        zeilen.append(
            f'<tr><th scope="row">{esc(f["name"])} <span class="t2">({esc(fid)}{mark})</span></th>'
            + "".join(zellen)
            + f'<td class="num">{num(maxv)}</td></tr>'
        )
    kopf = (
        "<thead><tr><th>Fach</th>"
        + "".join(f'<th scope="col">{esc(t)}</th>' for t in STELLEN_KOPF.values())
        + '<th scope="col">davon maximal als vertragsärztliche Planstellen'
        '<br><span class="t2">Obergrenze, kein Planwert</span></th></tr></thead>'
    )
    titel = _beschriftung(
        f"Sachleistungsstellen im PLAN 2030 je Fach, {esc(a.region(rid)['name'])}: gemeinsame Stellen aller "
        "Krankenversicherungsträger und zusätzliche Stellen einzelner Träger. Die vertragsärztlichen Planstellen "
        "des IST-Stands sind nicht enthalten – sie zählen etwas anderes."
    )
    return (
        f'<div class="scroll"><table class="t">{titel}{kopf}<tbody>{"".join(zeilen)}</tbody></table></div>'
        + _zuschnitt_zeile(zuschnitte)
        + TEILMENGEN_HINWEIS
        + '<p class="t2">«Zusätzliche» Stellen stehen nur Versicherten eines Trägers offen – nicht über Träger '
        "addieren. ÖGK = Österreichische Gesundheitskasse, SVS = Sozialversicherung der Selbständigen, "
        "BVAEB = Versicherungsanstalt öffentlich Bediensteter, Eisenbahnen und Bergbau.</p>"
    )


def _in_worten(a: Aufbau, rid: str) -> str:
    """Je Fach ein Satz, aus den Daten abgeleitet; der Vorbehalt steht im Satz, nicht nur im Kasten.

    Vorbehalte, die für **jedes** Fach dieser Matrix gelten (z. B. «ohne Patientenströme»), stehen einmal vor der
    Liste statt siebzehnmal darin: Sonst begraben sie die fachspezifischen, auf die es ankommt.
    """
    mit_wert = [str(f["id"]) for f in a.faecher if (z := a.zelle(rid, "PLAN", str(f["id"]))) and z.lage]
    if not mit_wert:
        return ""
    gemeinsam = set.intersection(*({k for k, _ in _kennungen(a, rid, fid)} for fid in mit_wert))
    stuecke, ohne_befund = [], []
    for f in a.faecher:
        fid = str(f["id"])
        if fid not in mit_wert:
            continue
        zelle = a.zelle(rid, "PLAN", fid)
        eigen = " ".join(text for k, text in _kennungen(a, rid, fid) if k not in gemeinsam)
        # Ein Satz «im Soll-Intervall» wiederholt nur die Spalte «Lage» und sagt nichts dazu. Solche Fächer
        # kommen in eine Zeile – ihre Namen bleiben damit auf der Seite, ohne siebzehn hohle Sätze.
        if zelle is not None and zelle.lage == "im" and not eigen:
            ohne_befund.append(f"{esc(f['name'])} ({esc(fid)})")
            continue
        s = satz(zelle, "PLAN 2030").replace("<p>", "").replace("</p>", "")
        stuecke.append(f"<li><b>{esc(f['name'])} ({esc(fid)}):</b> {s} {eigen}</li>")
    if ohne_befund:
        stuecke.append(f"<li><b>Im Soll-Intervall, ohne weitere Vorbehalte:</b> {_und(ohne_befund)}.</li>")
    vorn = " ".join(text for k, text in _kennungen(a, rid, mit_wert[0]) if k in gemeinsam)
    kopf = f'<p class="t2"><b>Für jedes Fach dieser Matrix gilt:</b> {vorn}</p>' if vorn else ""
    return kopf + f'<ul class="worte">{"".join(stuecke)}</ul>'


def _kennungen(a: Aufbau, rid: str, fid: str) -> list[tuple[str, str]]:
    """Die Vorbehalte einer Zelle als (Kennung, fertiger Text); die Kennung, um Gemeinsames zu erkennen."""
    out = []
    for kennung, *args in a.vorbehalte_roh(rid, "PLAN", fid):
        _, text = VORBEHALTE[str(kennung)]
        for i, arg in enumerate(args):
            text = text.replace(f"{{{i}}}", esc(arg))
        out.append((str(kennung), text))
    return out


def _lage_satz(a: Aufbau, rid: str) -> str:
    """Der Satz der ersten Schicht: wie viele Fächer unter, im und über dem Soll-Intervall liegen.

    Jeder Teil trägt seine eigene Präposition («3 darunter», «14 darin»): Hängt man sie hinten an, entsteht
    «14 im dem Soll-Intervall».
    """
    zellen = [z for f in a.faecher if (z := a.zelle(rid, "PLAN", str(f["id"]))) and z.lage]
    n = {k: sum(1 for z in zellen if z.lage == k) for k in ("unter", "im", "über")}
    knapp = sum(1 for z in zellen if z.lage != "im" and abs(float(z.aave_abstand or 0)) < 1)
    wort = {"im": "darin", "unter": "darunter", "über": "darüber"}
    teile = [f"{n[k]} {wort[k]}" if n[k] else f"keines {wort[k]}" for k in ("im", "unter", "über")]
    satzteil = (
        f"Von {len(zellen)} Fächern mit einem Wert liegen im PLAN 2030 "
        f"{_und(teile)} – gemessen am Versorgungsdichte-Soll-Intervall des ÖSG"
    )
    if knapp:
        satzteil += (
            f"; bei {'einem Fach' if knapp == 1 else f'{knapp} Fächern'} beträgt der Abstand zur Grenze weniger "
            "als eine ÄAVE, dort sind Lage und Position nicht belastbar"
        )
    return f"<p>{satzteil}.</p>"


def _und(teile: list[str]) -> str:
    """«a, b und c» – damit die Sätze der Vorlagen nicht wie eine Aufzählung einer Maschine klingen."""
    if not teile:
        return ""
    return teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " und " + teile[-1]


def _begriffe() -> str:
    """Die vier Begriffe, ohne die keine Zahl der Seite lesbar ist – **vor** der Tabelle.

    Wortlaut aus dem Glossar in docs/METHODIK.md, wo jeder Eintrag seine Quelle hat (ÖSG-Tabellenband S.12–13,
    Textband S.227/S.38–39, S.232). Vorher stand eine Legende klein unter der Tabelle; dort liest sie niemand,
    der die Kürzel nicht schon kennt.
    """
    return """<dl class="begriffe">
<dt>ÄAVE</dt><dd>ärztliche ambulante Versorgungseinheit. Eine ÄAVE entspricht grundsätzlich einer durchschnittlich
arbeitenden Kassenärztin bzw. einem Kassenarzt des Fachs – keine Kopfzahl.</dd>
<dt>Versorgungsdichte (VD)</dt><dd>ÄAVE je 100.000 Einwohner:innen der Wohnbevölkerung.</dd>
<dt>Soll-Intervall (VDmin–VDmax)</dt><dd>die Spanne, in der die Versorgungsdichte 2030 laut Österreichischem
Strukturplan Gesundheit (ÖSG) liegen soll.</dd>
<dt>Sachleistungsstellen</dt><dd>Planstellen für niedergelassene Vertragsärzt:innen und geplante ärztliche
Vollzeitäquivalente in Ambulatorien. Niederösterreich nennt sie in seiner Matrix «Kassenstellen».</dd>
</dl>"""


def _was_nicht() -> str:
    """Kasten «Was diese Zahlen nicht sagen» – wörtlich die Vorbehalte aus docs/DATEN.md, Fallstricke 1 und 11."""
    return """<aside class="kasten">
<h2>Was diese Zahlen nicht sagen</h2>
<ul>
<li><b>Nur Sachleistung.</b> Gezählt sind Spitalsambulanzen und Niedergelassene mit Kassenvertrag – ohne
Wahlärzt:innen, die in den Soll-Intervallen des ÖSG aber enthalten sind.</li>
<li><b>Ohne Patientenströme.</b> Geteilt wird durch die Wohnbevölkerung der Region; Zentren versorgen ihr Umland
mit und liegen deshalb eher höher.</li>
<li><b>Im Soll-Intervall kein Unterschied.</b> Der ÖSG verlangt nur, dass die Dichte darin liegt.</li>
</ul>
</aside>"""


def _quellenzeile(a: Aufbau, rid: str) -> str:
    """Verordnung, Seite und RIS – die Seitenzahl auch als Text, weil `#page=` kein Standard des Web ist."""
    q = a.quelle(rid, "PLAN") or a.quelle(rid, "IST")
    if q is None:
        return ""
    pdf, seite, datei, ris = q
    return (
        f'<p class="quelle">Festgelegt in <span class="nb">{esc(pdf)}</span>, <b>Seite {seite}</b>: '
        f'<a href="{esc(datei)}#page={seite}" target="_blank" rel="noopener noreferrer">Seite {seite} öffnen</a> · '
        f'<a href="{esc(ris)}" target="_blank" rel="noopener noreferrer">Verordnung im RIS</a></p>'
    )


def _seite_link(a: Aufbau, pdf: str, seite: int) -> str:
    """«Seite 12: öffnen» in die Datei auf dem OGD-Dateiserver. Die Zahl steht auch als Text da, weil `#page=`
    eine Übereinkunft der PDF-Betrachter ist und kein Standard des Web."""
    for eintrag in a.quellen_liste():
        if str(eintrag[0]) == pdf:
            return f'Seite {seite}: <a href="{esc(eintrag[2])}#page={seite}" target="_blank" rel="noopener noreferrer">öffnen</a>'
    return f"Seite {seite}"


def _fussnoten(a: Aufbau, r: dict[str, object]) -> str:
    """Die Fußnoten der Matrix, wörtlich, gruppiert nach Einordnung. Sie hängen an der Matrix, nicht an der Zelle –
    deshalb ein eigener Block und keine erfundenen Marker in unseren Tabellen."""
    f = a.fussnoten
    treffer = f[(f["Ebene"] == r["ebene"]) & (f["Region_ID"].astype(str) == str(r["id"]))]
    if treffer.empty:
        return ""
    gruppen = []
    for einordnung, g in treffer.groupby("Einordnung", sort=True):
        punkte = "".join(
            f"<li><b>{esc(z.Zeichen)}</b> «{esc(z.Text)}» "
            f'<span class="t2">({_seite_link(a, str(z.PDF), int(z.Seite))})</span></li>'
            for z in g.drop_duplicates(["Zeichen", "Text"]).itertuples()
        )
        gruppen.append(f"<h4>{esc(einordnung)}</h4><ul>{punkte}</ul>")
    return (
        f"<details><summary>Fußnoten der Verordnung zu dieser Matrix ({len(treffer)})</summary>"
        '<p class="t2">Wörtlich wie gedruckt. «Vorlage» heißt: Die Fußnote steht schon in der ÖSG-Vorlage '
        "(Tabellenband S.239); «betrifft Werte» heißt: Sie ändert, was eine Zahl bedeutet.</p>"
        + "".join(gruppen)
        + "</details>"
    )


def _korrigiert(a: Aufbau, r: dict[str, object], regeln: int) -> str:
    """«18 Werte nach 4 dokumentierten Regeln korrigiert» – eine Regel kann viele Zellen betreffen."""
    zellen = a.long[(a.long["Region_ID"] == str(r["id"])) & (a.long["Quelle"] == "korrigiert")]
    if not len(zellen):
        return f"{regeln} dokumentierte Regeln für diese Matrix"
    return f"{len(zellen)} Werte nach {regeln} dokumentierten Regeln korrigiert"


def _korrekturen(a: Aufbau, r: dict[str, object]) -> str:
    """Die Korrekturregeln, die für diese Matrix gelten – wörtlich mit Art, Befund und Begründung."""
    k = a.regeln
    land = str(r["land"])
    treffer = k[
        ((k["Land"] == land) | (k["Land"] == "*"))
        & ((k["Region_ID"].astype(str) == str(r["id"])) | (k["Region_ID"] == "*"))
    ]
    if treffer.empty:
        return ""
    punkte = "".join(
        f"<li><b>{esc(z.Art)}</b> <code>{esc(z.Regel)}</code> "
        f'<span class="t2">(Befund {esc(z.Befund)}, {esc(z.Abschnitt)} {esc(z.Zeile_ID)}, Fach {esc(z.Fach)})</span>'
        f"<br>{esc(z.Begruendung)}</li>"
        for z in treffer.itertuples()
    )
    return (
        f"<details><summary>Woher kommt diese Zahl? {_korrigiert(a, r, len(treffer))}</summary>"
        '<p class="t2">Jede Abweichung vom PDF ist eine Regel mit Begründung, wörtlich aus <code>korrekturen.csv'
        "</code>. Der Rohtext des PDF bleibt in der veröffentlichten Tabelle erhalten.</p>"
        f"<ul>{punkte}</ul></details>"
    )


def _anker(ueberschrift: str) -> str:
    """Sprungmarke, wie GitHub sie aus einer Markdown-Überschrift bildet: klein, ohne Satzzeichen, Leerzeichen
    zu Bindestrichen. Dass sie stimmt, prüft ein Test gegen die Überschriften der Datei."""
    kern = re.sub(r"[^\w\s-]", "", ueberschrift.strip().lower(), flags=re.U)
    return re.sub(r"\s+", "-", kern)


def offene_fragen_ueberschrift(land_name: str) -> str | None:
    """Die Überschrift des Abschnitts in docs/offene_punkte.md für dieses Land, falls es einen gibt."""
    datei = web_dir().parent / "docs" / "offene_punkte.md"
    if not datei.is_file():
        return None
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        if zeile.startswith("### ") and zeile[4:].startswith(land_name):
            return zeile[4:].strip()
    return None


def _offene_fragen(a: Aufbau, r: dict[str, object]) -> str:
    """Verweis auf die offenen Fragen zu dieser Verordnung – **ohne** sie hier zu wiederholen.

    Die Unsicherheit ist unsere, nicht die des Landes: «Hier lässt sich aus der Verordnung allein nicht
    entscheiden, wie ein Wert gemeint ist» (docs/offene_punkte.md). Auf einer Seite, die den Namen des Landes in
    der Überschrift trägt, wäre eine aufgezählte Frage ein Befund gegen das Land – und damit ein Urteil über die
    Fallstricke hinaus. Was eine Zahl wirklich betrifft, steht ohnehin als Vorbehalt oder Korrekturregel auf der
    Seite (docs/WEB.md, «Lesefassung»).
    """
    ueberschrift = offene_fragen_ueberschrift(str(r["land_name"]))
    if ueberschrift is None:
        return ""
    meta = a.daten["meta"]
    repo, version = str(meta["repo"]), str(meta["version"])  # type: ignore[index]
    ziel = f"{repo}/blob/{version}/docs/offene_punkte.md#{_anker(ueberschrift)}"
    return (
        "<details><summary>Offene Fragen zu dieser Verordnung</summary>"
        "<p>Bei einzelnen Werten lässt sich aus der Verordnung allein nicht entscheiden, wie sie gemeint sind. "
        "Wir haben uns für eine Lesart entschieden und sie dokumentiert; bestätigen kann sie nur das Land. "
        f'Nachzulesen im Datensatz: <a href="{esc(ziel)}" target="_blank" rel="noopener noreferrer">offene Punkte, '
        f"«{esc(ueberschrift)}»</a>.</p></details>"
    )


def _abweichungen(a: Aufbau, r: dict[str, object]) -> str:
    """Bekannte Abweichungen: Prüfungen, die hier bewusst nicht aufgehen, mit Grund."""
    w = a.abweichungen
    land = str(r["land"])
    treffer = w[(w["Land"] == land) & ((w["Region_ID"].astype(str) == str(r["id"])) | (w["Region_ID"] == "*"))]
    if treffer.empty:
        return ""
    punkte = "".join(
        f'<li><b>{esc(z.Check)}</b> <span class="t2">({esc(z.Abschnitt)} {esc(z.Zeile_ID)}, Fach {esc(z.Fach)})'
        f"</span><br>{esc(z.Grund)}</li>"
        for z in treffer.itertuples()
    )
    return (
        f"<details><summary>Bekannte Abweichungen ({len(treffer)})</summary>"
        '<p class="t2">Eine Prüfung, die hier nicht aufgeht, und warum sie so bleibt – wörtlich aus '
        "<code>bekannte_abweichungen.csv</code>.</p>"
        f"<ul>{punkte}</ul></details>"
    )


# --- Seiten ---------------------------------------------------------------------------------------------------


def seite_region(a: Aufbau, r: dict[str, object]) -> Seite:
    """Eine Versorgungsregion oder ein Bundesland: drei Schichten (Überblick, Tabellen, Apparat)."""
    rid, ebene = str(r["id"]), str(r["ebene"])
    name = str(r["name"])
    nummer = f" (VR {rid})" if ebene == "VR" else ""
    titel = f"Planstellen und Versorgungsdichte {name}{nummer} 2030 | RSG 2030"
    jahr_ist = a.wert(rid, "IST", "AM", 3)
    bev_ist, bev_plan = a.wert(rid, "IST", "AM", 2), a.wert(rid, "PLAN", "AM", 2)

    # Kurz halten: Dass die VR-Zahl geschätzt ist, muss dastehen; wie sie geschätzt ist, steht in der Methodik.
    bev_hinweis = "für die Region geschätzt" if ebene == "VR" else "Prognose der Statistik Austria"
    if ebene == "VR":
        bezirke = a.bezirke(rid)
        lage = (
            f"<p>Versorgungsregion {esc(rid)} in {esc(r['land_name'])}, "
            f"{'Bezirk' if len(bezirke) == 1 else 'Bezirke'} {esc(', '.join(bezirke))}. "
            "Geplant wird je Versorgungsregion; Zahlen für einzelne Bezirke gibt es nicht.</p>"
        )
        verweis = (
            f'<p><a href="{a.hoch(a.pfad(r))}bl/{LAND_SLUG[str(r["land"])]}/">Alle Regionen in '
            f"{esc(r['land_name'])}</a></p>"
        )
        klein = (
            '<p class="t2">In kleinen Versorgungsregionen verschiebt eine einzige ÄAVE die Dichte stark; dort sind '
            "Lage und Position nicht belastbar. Der ÄAVE-Abstand zeigt, um wie wenig es oft geht.</p>"
        )
    else:
        vr = a.vr_des_landes(str(r["land_name"]))
        liste = ", ".join(f'<a href="{a.hoch(a.pfad(r))}vr/{v}/">{esc(v)} {esc(a.region(v)["name"])}</a>' for v in vr)
        lage = f"<p>Bundesland mit {len(vr)} Versorgungsregionen: {liste}.</p>"
        verweis = ""
        klein = ""

    rumpf = f"""<h1>{esc(name)}: ambulante Versorgung laut RSG 2030</h1>
{lage}
<p>Wohnbevölkerung: {_tausend(bev_ist)} am 1.1.{esc(jahr_ist)}, {_tausend(bev_plan)} zum 1.1.2030
({bev_hinweis}).</p>
{_quellenzeile(a, rid)}
{_lage_satz(a, rid)}
{_was_nicht()}
{_begriffe()}
<h2 id="stellen">Sachleistungsstellen 2030 je Fach ({esc(name)})</h2>
{_tabelle_stellen(a, rid)}
<h2 id="vd">Versorgungsdichte im Vergleich zum Soll-Intervall des ÖSG</h2>
{_tabelle_vd(a, rid)}
{klein}
<h3>Lage und Vorbehalte je Fach</h3>
{_in_worten(a, rid)}
<h2 id="apparat">Herkunft, Fußnoten und Korrekturen</h2>
{_fussnoten(a, r)}
{_korrekturen(a, r)}
{_abweichungen(a, r)}
{_offene_fragen(a, r)}
{verweis}"""
    beschreibung = (
        f"Sachleistungsstellen und Versorgungsdichte 2030 für {name}{nummer} je Fach, verglichen mit dem "
        "Versorgungsdichte-Soll-Intervall des ÖSG – aus der Verordnung zum RSG 2030."
    )
    return Seite(a.pfad(r), titel, beschreibung, rumpf, f"?region={r['slug']}")


def seite_fach(a: Aufbau, f: dict[str, object]) -> Seite:
    """Ein Fach über alle Versorgungsregionen – dieselben Werte, gekippt. Kein Ranking, keine Österreich-Zahl."""
    fid, name, dg = str(f["id"]), str(f["name"]), _stellen_vd(f)
    zeilen, ohne = [], []
    for r in a.regionen:
        if r["ebene"] != "VR":
            continue
        rid = str(r["id"])
        p, i = a.zelle(rid, "PLAN", fid), a.zelle(rid, "IST", fid)
        if p is None and i is None:
            ohne.append(f"{esc(rid)} {esc(r['name'])}")
            continue
        stellen, maxv = a.stellen_wert(rid, fid)
        zeilen.append(
            f'<tr><th scope="row"><a href="{a.hoch(f"fach/{fid}/")}vr/{esc(rid)}/">{esc(rid)} {esc(r["name"])}</a>'
            f"</th><td>{esc(r['land_name'])}</td>"
            f'<td class="num">{esc(a.wert(rid, "IST", fid, 3))}</td>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 0), dg)}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 0), dg)}</td>'
            f"<td>{esc(LAGE_WORT.get(str(p.lage), '–')) if p else '–'}</td>"
            f'<td class="num">{_abstand(p)}</td>'
            f'<td class="num">{num(stellen)}</td><td class="num">{num(maxv)}</td></tr>'
        )
    teil = (
        f"<p><b>{esc(fid)} ist Teil von {esc(f['teil_von'])}</b> und hat zusätzlich ein eigenes Soll-Intervall: "
        f"Die ÄAVE stecken schon in {esc(f['teil_von'])}. Nicht addieren.</p>"
        if f["teil_von"]
        else ""
    )
    rumpf = f"""<h1>{esc(name)} ({esc(fid)}) in den 32 Versorgungsregionen, RSG 2030</h1>
<p>Versorgungsdichte je Versorgungsregion im Vergleich zum Versorgungsdichte-Soll-Intervall des ÖSG für 2030:
<b>{num(f["min"], dg)} bis {num(f["max"], dg)}</b> ÄAVE je 100.000 Einwohner:innen (ÖSG-Textband S.39).</p>
{teil}
{_was_nicht()}
{_begriffe()}
<h2>Versorgungsdichte je Versorgungsregion</h2>
<div class="scroll"><table class="t">{
        _beschriftung(
            f"{esc(name)} ({esc(fid)}) in den 32 Versorgungsregionen: Versorgungsdichte im IST und im PLAN 2030, Lage "
            "zum Soll-Intervall des ÖSG und Sachleistungsstellen 2030"
        )
    }<thead><tr><th>Versorgungsregion</th><th scope="col">Bundesland</th>
<th scope="col">IST-Jahr</th><th scope="col">VD IST</th><th scope="col">VD PLAN 2030</th>
<th scope="col">Lage PLAN 2030</th><th scope="col">ÄAVE-Abstand PLAN</th>
<th scope="col">Sachleistungsstellen 2030 gemeinsam</th>
<th scope="col">davon maximal als vertragsärztliche Planstellen</th></tr></thead>
<tbody>{"".join(zeilen)}</tbody></table></div>
<p class="t2">Das IST-Jahr unterscheidet sich je Bundesland (2022 oder 2023) und steht in der Tabelle;
niedergelassene ÄAVE sind zwischen den beiden Gruppen nur mit Vorsicht vergleichbar. Die Stellen sind
gemeinsame Sachleistungsstellen aller Träger; zusätzliche trägerspezifische Stellen stehen auf der Seite der
Region, und nie über Träger addieren.
Keine Summe und kein Österreich-Wert: Der ÖSG misst die Versorgungsdichte je Versorgungsregion, und ein
Österreich-IST würde zwei Jahre mischen.</p>
{f'<p class="t2">Ohne Wert in der Matrix: {", ".join(ohne)}.</p>' if ohne else ""}
<p><a href="{a.hoch(f"fach/{fid}/")}daten/">Alle Fächer und Regionen auf einer Seite</a></p>"""
    titel = f"Planstellen und Versorgungsdichte {name} 2030 | RSG 2030"
    beschreibung = (
        f"{name} ({fid}) in allen 32 Versorgungsregionen: Versorgungsdichte 2030 im Vergleich zum "
        f"Soll-Intervall des ÖSG ({num(f['min'], dg)}–{num(f['max'], dg)} ÄAVE je 100.000)."
    )
    return Seite(f"fach/{fid}/", titel, beschreibung, rumpf, f"?fach={fid}")


def _dokument(a: Aufbau, s: Seite) -> str:
    """Eine ganze Seite: Kopf mit canonical und Dataset-Bezug, Rumpf, Fußzeile. Kein Skript, kein fremder Server."""
    meta = a.daten["meta"]
    version = esc(meta["version"])  # type: ignore[index]
    return f"""<!doctype html>
<html lang="de-AT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="format-detection" content="telephone=no,date=no,address=no">
<title>{esc(s.titel)}</title>
<meta name="description" content="{esc(s.beschreibung)}">
<link rel="canonical" href="{esc(a.basis)}/{esc(s.pfad)}">
<link rel="stylesheet" href="{esc(a.stil(s.pfad))}">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"WebPage","name":{_json(s.titel)},
"description":{_json(s.beschreibung)},"inLanguage":"de-AT",
"url":{_json(f"{a.basis}/{s.pfad}")},"isPartOf":{{"@id":{_json(f"{a.basis}/daten/#dataset")}}},
"mainEntity":{{"@id":{_json(f"{a.basis}/daten/#dataset")}}},
"license":"https://creativecommons.org/licenses/by/4.0/"}}
</script>
</head>
<body>
<a class="skip" href="#inhalt">Zum Inhalt</a>
<header class="kopf">
  <p class="eyebrow"><a href="{esc(a.hoch(s.pfad))}daten/">RSG 2030 – Planungsmatrizen der Verordnungen</a>
     · Release {version}</p>
</header>
<main id="inhalt">
{s.rumpf}
</main>
<footer class="fuss">
{_urheber(a, s.pfad, s.dashboard)}
</footer>
</body>
</html>
"""


def _json(text: str) -> str:
    """Zeichenkette für JSON-LD (die Seite schreibt JSON von Hand, damit kein Skript nötig ist)."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _urheber(a: Aufbau, pfad: str, dashboard: str = "") -> str:
    """Urheberblock: wer die Seiten erstellt hat, mit den Vorbehalten im selben Satz (docs/WEB.md)."""
    meta = a.daten["meta"]
    repo, version = str(meta["repo"]), esc(meta["version"])  # type: ignore[index]
    rel = f"{repo}/releases/tag/{version}"
    return f"""<h2 id="urheber">Wer diese Seiten erstellt hat</h2>
<p><b>Max Plischke</b>, <a href="https://loesungswerk.at/rsg-2030" target="_blank" rel="noopener noreferrer">Lösungswerk</a>,
ORCID <a href="https://orcid.org/0000-0002-7410-2611" target="_blank" rel="noopener noreferrer">0000-0002-7410-2611</a>.
Ohne Auftrag erstellte, inoffizielle Aufbereitung amtlicher Daten; maßgeblich sind die Verordnungen im RIS.
Angaben ohne Gewähr, Fehler bitte melden.</p>
<p><b>Methode:</b> Die Planungsmatrizen aller neun Verordnungen sind aus den PDFs ausgelesen, jede Zelle zweimal
unabhängig gelesen, jede Abweichung vom PDF mit einer dokumentierten Regel begründet; Versorgungsdichte, Lage,
Position und ÄAVE-Abstand sind nach der Methode des ÖSG gerechnet
(<a href="{repo}/blob/{version}/docs/METHODIK.md" target="_blank" rel="noopener noreferrer">Methodik</a>,
<a href="{repo}/blob/{version}/docs/PRUEFUNG.md" target="_blank" rel="noopener noreferrer">Prüfkonzept</a>).</p>
<p><b>Daten:</b> <a href="{rel}" target="_blank" rel="noopener noreferrer">Release {version}</a> ·
Lizenz <a href="https://creativecommons.org/licenses/by/4.0/deed.de" target="_blank" rel="noopener noreferrer">CC BY 4.0</a> ·
<a href="{repo}/blob/{version}/CITATION.cff" target="_blank" rel="noopener noreferrer">Zitieren</a> ·
<a href="{repo}/issues/new?template=wert_weicht_ab.yml" target="_blank" rel="noopener noreferrer">Fehler melden</a> ·
<a href="https://loesungswerk.at/impressum" target="_blank" rel="noopener noreferrer">Impressum</a> ·
<a href="https://loesungswerk.at/datenschutz" target="_blank" rel="noopener noreferrer">Datenschutz</a></p>
<p class="t2"><a href="{esc(a.hoch(pfad))}daten/">Alle Zahlen auf einer Seite</a> ·
<a href="{repo}" target="_blank" rel="noopener noreferrer">Datensatz und Code</a> ·
<a href="{esc(a.hoch(pfad))}{esc(dashboard)}">Interaktiv vergleichen</a></p>"""


def seite_index(a: Aufbau) -> Seite:
    """Die dichte Seite: alle Zeilen «insgesamt» in einer Tabelle, dazu der Dataset-Eintrag für Dataset Search.

    Ein **einziger** `Dataset`-Eintrag im ganzen Werk; alle anderen Seiten verweisen mit `isPartOf` hierher.
    Mehrere Einträge für denselben Datensatz konkurrieren miteinander (docs/WEB.md, «Lesefassung»).
    """
    meta = a.daten["meta"]
    repo, version = str(meta["repo"]), str(meta["version"])  # type: ignore[index]
    rel = f"{repo}/releases/download/{version}"
    zeilen = []
    for r in a.regionen:
        if r["ebene"] != "VR":
            continue
        rid = str(r["id"])
        for f in a.faecher:
            fid, dg = str(f["id"]), _stellen_vd(f)
            p = a.zelle(rid, "PLAN", fid)
            if p is None:
                continue
            zeilen.append(
                f'<tr><td class="num">{esc(rid)}</td>'
                f'<td><a href="../vr/{esc(rid)}/">{esc(r["name"])}</a></td>'
                f'<td><a href="../fach/{esc(fid)}/">{esc(fid)}</a></td>'
                f'<td class="num">{num(a.wert(rid, "PLAN", fid, 1))}</td>'
                f'<td class="num">{num(a.wert(rid, "PLAN", fid, 0), dg)}</td>'
                f'<td class="num">{num(f["min"], dg)}</td><td class="num">{num(f["max"], dg)}</td>'
                f"<td>{esc(LAGE_WORT.get(str(p.lage), '–'))}</td>"
                f'<td class="num">{_abstand(p)}</td></tr>'
            )
    laender = ", ".join(
        f'<a href="../bl/{LAND_SLUG[str(r["land"])]}/">{esc(r["land_name"])}</a>'
        for r in a.regionen
        if r["ebene"] == "BL"
    )
    faecher = ", ".join(f'<a href="../fach/{esc(f["id"])}/">{esc(f["id"])} {esc(f["name"])}</a>' for f in a.faecher)
    dataset = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Dataset","@id":{_json(f"{a.basis}/daten/#dataset")},
"name":"RSG 2030 – Planungsmatrizen der Verordnungen",
"description":{
        _json(
            "Die Planungsmatrizen der Regionalen Strukturpläne Gesundheit 2030 aller neun österreichischen Bundesländer: "
            "ambulante ärztliche Kapazität in ÄAVE und Sachleistungsstellen je Bundesland, Versorgungsregion und Fach, "
            "IST und PLAN 2030, dazu Versorgungsdichte und Lage zum Versorgungsdichte-Soll-Intervall des ÖSG."
        )
    },
"url":{_json(f"{a.basis}/daten/")},"sameAs":{_json(repo)},"version":{_json(version)},
"license":"https://creativecommons.org/licenses/by/4.0/","isAccessibleForFree":true,"inLanguage":"de-AT",
"creator":{{"@type":"Person","name":"Max Plischke","sameAs":"https://orcid.org/0000-0002-7410-2611"}},
"spatialCoverage":"Österreich","temporalCoverage":"2022/2030",
"distribution":[
 {{"@type":"DataDownload","name":"RSG_2030_Versorgungsdichte.csv","encodingFormat":"text/csv",
  "contentUrl":{_json(f"{rel}/RSG_2030_Versorgungsdichte.csv")}}},
 {{"@type":"DataDownload","name":"RSG_2030_Stellen.csv","encodingFormat":"text/csv",
  "contentUrl":{_json(f"{rel}/RSG_2030_Stellen.csv")}}},
 {{"@type":"DataDownload","name":"RSG_2030_Planungsmatrizen.csv","encodingFormat":"text/csv",
  "contentUrl":{_json(f"{rel}/RSG_2030_Planungsmatrizen.csv")}}}]}}
</script>"""
    rumpf = f"""{dataset}
<h1>Versorgungsdichte 2030 aller 32 Versorgungsregionen im Vergleich zum ÖSG</h1>
<p>Alle Zeilen «ÄAVE insgesamt» der Tabelle Versorgungsdichte: je Versorgungsregion und Fach die geplanten ÄAVE
2030, die Versorgungsdichte, das Versorgungsdichte-Soll-Intervall des Österreichischen Strukturplans Gesundheit
(ÖSG) und die Lage dazu. {len(zeilen)} Zeilen.</p>
{_quellen_uebersicht(a)}
{_was_nicht()}
{_begriffe()}
<h2>Alle Werte</h2>
<div class="scroll"><table class="t t-index">{
        _beschriftung(
            f"Versorgungsdichte PLAN 2030 je Versorgungsregion und Fach, alle {len(zeilen)} Zeilen «ÄAVE insgesamt» der "
            "Tabelle Versorgungsdichte, im Vergleich zum Soll-Intervall des ÖSG"
        )
    }<thead><tr><th scope="col">VR</th><th scope="col">Region</th>
<th scope="col">Fach</th><th scope="col">ÄAVE PLAN</th><th scope="col">VD PLAN</th><th scope="col">VDmin</th>
<th scope="col">VDmax</th><th scope="col">Lage</th><th scope="col">Abstand</th></tr></thead>
<tbody>{"".join(zeilen)}</tbody></table></div>
<h2>Seiten</h2>
<p><b>Bundesländer:</b> {laender}</p>
<p><b>Fächer:</b> {faecher}</p>
<h2 id="nicht">Was dieser Datensatz nicht tut</h2>
<ul>
<li><b>Er interpretiert nicht.</b> Die Werte stehen so da, wie die Verordnungen sie drucken; jede Abweichung vom
PDF ist eine dokumentierte Regel mit Begründung.</li>
<li><b>Er rechnet nichts nach ÖSG-Methode nach, was nicht in den Dateien steht.</b> Versorgungsdichte, Lage,
Position und ÄAVE-Abstand sind die einzigen Kennzahlen; sie stehen in der veröffentlichten Tabelle.</li>
<li><b>Keine Österreich-Werte.</b> Der ÖSG misst je Versorgungsregion, und ein Österreich-IST würde zwei
IST-Jahre mischen (2022 und 2023, je nach Bundesland).</li>
<li><b>Keine Stellen im Vergleich IST → PLAN.</b> IST-Planstellen und PLAN-Sachleistungsstellen zählen
Verschiedenes; der Vergleich bräuchte Annahmen und wäre eine Auswertung, keine Lesung.</li>
<li><b>Keine Daten von außerhalb</b> der Verordnungen, der ÖSG-Richtwerte und der amtlichen Bevölkerungsdaten.</li>
</ul>
<p><b>Herunterladen:</b>
<a href="{rel}/RSG_2030_Versorgungsdichte.csv" target="_blank" rel="noopener noreferrer">Versorgungsdichte (CSV)</a> ·
<a href="{rel}/RSG_2030_Stellen.csv" target="_blank" rel="noopener noreferrer">Stellen (CSV)</a> ·
<a href="{rel}/RSG_2030_Planungsmatrizen.csv" target="_blank" rel="noopener noreferrer">Planungsmatrizen (CSV)</a> ·
<a href="{rel}/RSG_2030_Planungsmatrizen.xlsx" target="_blank" rel="noopener noreferrer">Excel-Mappe</a> ·
<a href="{rel}/Pruefbericht.md" target="_blank" rel="noopener noreferrer">Prüfbericht</a></p>
<p><b>Vor der Verwendung bitte lesen:</b>
<a href="{repo}/blob/{version}/docs/DATEN.md#fallstricke" target="_blank" rel="noopener noreferrer">Fallstricke</a> ·
<a href="{repo}/blob/{version}/docs/METHODIK.md" target="_blank" rel="noopener noreferrer">Methodik</a> ·
<a href="{repo}/blob/{version}/docs/PRUEFUNG.md" target="_blank" rel="noopener noreferrer">Prüfkonzept</a></p>"""
    return Seite(
        "daten/",
        "Versorgungsdichte und Planstellen 2030 je Region und Fach | RSG 2030",
        "Alle Werte der RSG-2030-Verordnungen: Versorgungsdichte je Versorgungsregion und Fach im Vergleich zum "
        "Soll-Intervall des ÖSG, dazu Sachleistungsstellen – maschinenlesbar, mit Quelle je Wert.",
        rumpf,
    )


def _quellen_uebersicht(a: Aufbau) -> str:
    """Je Bundesland die Verordnung mit Seite und RIS-Link – die Herkunft aller Zahlen auf einen Blick."""
    punkte = []
    for r in a.regionen:
        if r["ebene"] != "BL":
            continue
        q = a.quelle(str(r["id"]), "PLAN")
        if q is None:
            continue
        pdf, seite, datei, ris = q
        punkte.append(
            f'<li><a href="../bl/{LAND_SLUG[str(r["land"])]}/">{esc(r["land_name"])}</a>: '
            f'<span class="nb">{esc(pdf)}</span>, Seite {seite} '
            f'(<a href="{esc(datei)}#page={seite}" target="_blank" rel="noopener noreferrer">öffnen</a>, '
            f'<a href="{esc(ris)}" target="_blank" rel="noopener noreferrer">RIS</a>)</li>'
        )
    return f"<details><summary>Die neun Verordnungen</summary><ul>{''.join(punkte)}</ul></details>"


def release_datum() -> str | None:
    """Tag der Veröffentlichung der Version, die die Seiten zeigen – aus `CITATION.cff`.

    Das ist das einzige Datum, das eine echte Änderung der Seiten bedeutet: Die Zahlen ändern sich mit dem
    Release, nicht mit dem Bau. Ein `lastmod` in Höhe des Baudatums behauptet bei jedem Lauf eine Änderung;
    Suchmaschinen ziehen daraus die richtige Folgerung und ignorieren es. Passt die Version in `CITATION.cff`
    nicht zur Paketversion (z. B. zwischen zwei Releases), bleibt das Datum weg – lieber keine Angabe als eine
    falsche.
    """
    datei = web_dir().parent / "CITATION.cff"
    if not datei.is_file():
        return None
    text = datei.read_text(encoding="utf-8")
    version = re.search(r'^version:\s*"?([^"\n]+)"?', text, re.M)
    datum = re.search(r"^date-released:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not version or not datum or version.group(1).strip() != paketversion():
        log.info("CITATION.cff passt nicht zur Paketversion – Sitemap ohne «lastmod»")
        return None
    return datum.group(1)


def _sitemap(a: Aufbau, seiten: list[Seite]) -> str:
    stand = release_datum()
    mod = f"<lastmod>{stand}</lastmod>" if stand else ""
    eintraege = "".join(f"<url><loc>{a.basis}/{s.pfad}</loc>{mod}</url>" for s in seiten)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{eintraege}</urlset>\n'


def baue_lesefassung(basis: str = BASIS_STANDARD) -> Path:
    """Alle Seiten erzeugen und nach `daten_ergebnis/web/` schreiben (neben das Dashboard)."""
    a = Aufbau(basis)
    seiten = [seite_index(a)]
    seiten += [seite_region(a, r) for r in a.regionen]
    seiten += [seite_fach(a, f) for f in a.faecher]

    ziel = ausgabe_dir() / "web"
    ziel.mkdir(parents=True, exist_ok=True)
    for s in seiten:
        text = _dokument(a, s)
        _pruefe_seite(s, text)
        ordner = ziel / s.pfad
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "index.html").write_text(text, encoding="utf-8")
    (ziel / "sitemap.xml").write_text(_sitemap(a, seiten), encoding="utf-8")
    shutil.copyfile(web_dir() / "lesefassung" / "lesefassung.css", ziel / "lesefassung.css")
    log.info(f"{len(seiten)} Seiten: 1 Index, {sum(1 for s in seiten if s.pfad.startswith('bl/'))} Bundesländer, "
             f"{sum(1 for s in seiten if s.pfad.startswith('vr/'))} Versorgungsregionen, "
             f"{sum(1 for s in seiten if s.pfad.startswith('fach/'))} Fächer")  # fmt: skip
    schreibe_laufprotokoll(ausgabe_dir(), "lesefassung", [ziel / "sitemap.xml"], {"Seiten": str(len(seiten))})
    return ziel


def _pruefe_seite(s: Seite, text: str) -> None:
    """Was eine Vorlage kaputt macht, soll den Bau abbrechen, nicht still auf der Seite landen."""
    klein = text.lower()
    for wort in VERBOTEN:
        if wort in klein:
            raise ValueError(f"{s.pfad}: verbotenes Wort «{wort}» im erzeugten HTML (docs/DATEN.md, Fallstrick 1)")
    for marke in ("{0}", "{1}", "{2}"):
        if marke in text:
            raise ValueError(f"{s.pfad}: «{marke}» im erzeugten HTML – eine Vorlage ist nicht gefüllt")
    # Nur als eigenes Wort: «nan» steckt sonst in «Krankenanstalten», «None» in keinem deutschen Wort, aber
    # Wortgrenzen sind hier ohnehin die richtige Frage – gesucht ist eine durchgerutschte Zahl, kein Textteil.
    if treffer := re.findall(r"\b(nan|None|NaN)\b", text):
        raise ValueError(f"{s.pfad}: «{treffer[0]}» als Wert im erzeugten HTML – eine Vorlage ist nicht gefüllt")
    for pflicht in ("<h1>", "<title>", 'rel="canonical"'):
        if pflicht not in text:
            raise ValueError(f"{s.pfad}: {pflicht} fehlt")


def main(argv: list[str] | None = None) -> int:
    einrichten()
    p = argparse.ArgumentParser(
        prog="python -m rsg2030 lesefassung",
        description="statische Seiten zu den veröffentlichten Tabellen bauen (docs/WEB.md, «Lesefassung»)",
    )
    p.add_argument("--basis", default=BASIS_STANDARD, help=f"Adresse der Seiten (Standard: {BASIS_STANDARD})")
    args = p.parse_args(argv)
    try:
        ziel = baue_lesefassung(args.basis)
    except (ValueError, KeyError, FileNotFoundError) as e:
        log.error(f"❌ Lesefassung nicht gebaut: {e}")
        return 1
    log.info(f"Lesefassung gebaut: {ziel} (Ansehen: python -m http.server -d {ziel})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
