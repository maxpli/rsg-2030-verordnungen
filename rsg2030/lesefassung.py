"""Lesefassung: statische Seiten zu den veröffentlichten Tabellen, ohne JavaScript.

Zweck: Die Zahlen sollen überhaupt in maschinenlesbarer Form existieren. In den Verordnungs-PDFs sind sie für
Suchmaschinen und Abrufsysteme unerreichbar (oft Bildseiten, immer Querformat), und auf dem Dashboard entstehen sie
erst im Browser. Hier steht jede Zahl als Text im HTML. Was es nirgends sonst gibt, ist nicht die Abschrift, sondern
der Vergleich: Versorgungsdichte, Lage zum Soll-Intervall des ÖSG, Position und ÄAVE-Abstand.

Gebaut werden (Adressen sind endgültig, GitHub Pages kann nicht umleiten – deshalb Nummern und Kürzel, keine Namen):

    /daten/        Einstieg: Verzeichnis der Regionen und Fächer, Downloads; alle Zeilen «insgesamt» zugeklappt
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
from rsg2030.darstellung import KEIN_WERT, VORBEHALTE, Zelle, zahl
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
    pfadleiste: tuple[tuple[str, str], ...] = ()
    """Brotkrumen: (Name, Pfad ab der Wurzel); der letzte Eintrag ist die Seite selbst, mit leerem Pfad."""


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

    def stellen_plan(self, rid: str, fach: str) -> dict[str, object]:
        """Sachleistungsstellen 2030 dieses Fachs je Stellen-Zeile (gemeinsam, zusätzlich je Träger)."""
        s = self.stellen
        treffer = s[(s["Region_ID"] == rid) & (s["Abschnitt"] == "PLAN") & (s["Fach"] == fach)]
        return {str(z.Zeile_ID): z.Stellen for z in treffer.itertuples() if z.Zeile_ID in STELLEN_PLAN}

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

LAGE_KURZ = {"unter": "unter", "im": "im", "über": "über"}
"""Lage in der Tabelle: ein Wort, der Bezug steht im Spaltenkopf («Lage zum Soll-Intervall»). Ausgeschrieben
bricht «unter dem Soll-Intervall» in jeder Zeile um und verdoppelt die Höhe der Tabelle. Weiterhin ein Wort,
keine Farbe (docs/WEB.md, «Darstellungsregeln der Lesefassung»)."""

TEILMENGEN_HINWEIS = (
    '<p class="t2">PUL und KFO stecken bereits in IM bzw. ZMK und haben zusätzlich ein eigenes Soll-Intervall; '
    "für eine Summe über alle Fächer beide weglassen.</p>"
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


def _beschriftung(text: str) -> str:
    """`<caption>`: das Stück Metadatum, mit dem Extraktoren und Bildschirmleser eine Tabelle benennen. Ohne das
    steht die Überschrift nur daneben, und die Zuordnung muss erraten werden (docs/WEB.md, «Lesefassung»)."""
    return f"<caption>{text}</caption>"


def _zuschnitt_zeile(zuschnitte: list[str]) -> str:
    """Das Zeichen an den Zeilen auflösen, in einer Zeile unter der Tabelle – keine weitere Spalte voll Kürzel."""
    if not zuschnitte:
        return ""
    return (
        f'<p class="t2">{ZUSCHNITT_ZEICHEN} Im Zuschnitt des ÖSG gerechnet, nicht als Spalte der Matrix: '
        + "; ".join(esc(z) for z in zuschnitte)
        + ".</p>"
    )


def _tabelle_stellen(a: Aufbau, rid: str) -> str:
    """Sachleistungsstellen 2030 je Fach – nur PLAN, gemeinsam und zusätzlich je Träger."""
    s = a.stellen[(a.stellen["Region_ID"] == rid) & (a.stellen["Abschnitt"] == "PLAN")]
    if s.empty:
        return ""
    werte = {(r.Zeile_ID, r.Fach): r for r in s.itertuples()}
    # Eine Spalte «zusätzlich …», in der für jedes Fach 0 steht, sagt nur «keine»; das steht dann als Satz unter
    # der Tabelle, und die Tabelle passt am Handy ohne Scrollen. Die gemeinsamen Stellen bleiben immer.
    nur_null = [
        z
        for z in STELLEN_PLAN[1:]
        if all(pd.isna(r.Stellen) or float(r.Stellen) == 0 for (zid, _), r in werte.items() if zid == z)
    ]
    spalten = [z for z in STELLEN_PLAN if z not in nur_null]
    zeilen: list[str] = []
    zuschnitte: list[str] = []
    for f in a.faecher:
        fid = str(f["id"])
        if not any((z, fid) in werte for z in STELLEN_PLAN):
            continue
        g = werte.get(("slst_gemeinsam", fid))
        zellen = []
        for z in spalten:
            r = werte.get((z, fid))
            zellen.append(f'<td class="num">{num(r.Stellen) if r is not None else "–"}</td>')
        zuschnitt = None if g is None else str(g.Zuschnitt)
        mark = ZUSCHNITT_ZEICHEN if _zuschnitt_abweichend(zuschnitt, fid) else ""
        if mark and zuschnitt is not None and zuschnitt not in zuschnitte:
            zuschnitte.append(zuschnitt)
        zeilen.append(
            f'<tr><th scope="row">{esc(f["name"])} <span class="t2">({esc(fid)}{mark})</span></th>'
            + "".join(zellen)
            + "</tr>"
        )
    # Ohne die Obergrenze für vertragsärztliche Planstellen: Die Matrix druckt sie je Träger-Zeile, eine Spalte für
    # alle wäre eine eigene Rechnung, eine nur für die gemeinsamen Stellen missverständlich. Sie steht in der
    # Tabelle Stellen (`Max_VAEP_Stellen`; docs/WEB.md, «Lesefassung»).
    kopf = (
        '<thead><tr><th scope="col">Fach</th>'
        + "".join(f'<th scope="col" class="num">{esc(STELLEN_KOPF[z])}</th>' for z in spalten)
        + "</tr></thead>"
    )
    zusatz = " und zusätzliche Stellen einzelner Träger" if len(spalten) > 1 else ""
    titel = _beschriftung(
        f"Sachleistungsstellen im PLAN 2030 je Fach, {esc(a.region(rid)['name'])}: gemeinsame Stellen aller "
        f"Krankenversicherungsträger{zusatz}. Die vertragsärztlichen Planstellen des IST-Stands sind nicht "
        "enthalten – sie zählen etwas anderes."
    )
    traeger = {
        "slst_zus_oegk": "ÖGK (Österreichische Gesundheitskasse)",
        "slst_zus_svs": "SVS (Sozialversicherung der Selbständigen)",
        "slst_zus_bvaeb": "BVAEB (Versicherungsanstalt öffentlich Bediensteter, Eisenbahnen und Bergbau)",
    }
    hinweise = []
    if nur_null:
        hinweise.append(
            "<p>Zusätzliche Stellen einzelner Träger: In der Matrix steht für jedes Fach 0 bei "
            + _und([traeger[z] for z in nur_null])
            + "; diese Spalten sind deshalb nicht abgebildet.</p>"
        )
    gezeigt = [traeger[z] for z in spalten if z in traeger]
    if gezeigt:
        hinweise.append(f"<p>{STELLEN_ZUSAMMEN} " + "; ".join(gezeigt) + ".</p>")
    wien = f" {STELLEN_WIEN}" if a.region(rid)["land"] == "Wien" else ""
    return (
        f'<div class="scroll"><table class="t">{titel}{kopf}<tbody>{"".join(zeilen)}</tbody></table></div>'
        f'<div class="lesehilfe"><p>{STELLEN_HILFE}{wien}</p>'
        + _zuschnitt_zeile(zuschnitte)
        + TEILMENGEN_HINWEIS
        + "".join(hinweise)
        + "</div>"
    )


def _kennungen(a: Aufbau, rid: str, fid: str) -> list[tuple[str, str]]:
    """Die Vorbehalte einer Zelle als (Kennung, fertiger Text); die Kennung, um Gemeinsames zu erkennen."""
    out = []
    for kennung, *args in a.vorbehalte_roh(rid, "PLAN", fid):
        _, text = VORBEHALTE[str(kennung)]
        for i, arg in enumerate(args):
            text = text.replace(f"{{{i}}}", esc(arg))
        out.append((str(kennung), text))
    return out


def _und(teile: list[str]) -> str:
    """«a, b und c» – damit die Sätze der Vorlagen nicht wie eine Aufzählung einer Maschine klingen."""
    if not teile:
        return ""
    return teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " und " + teile[-1]


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


def _json(text: str) -> str:
    """Zeichenkette für JSON-LD (die Seite schreibt JSON von Hand, damit kein Skript nötig ist)."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _abstand(z: Zelle | None) -> str:
    """ÄAVE-Abstand wie in der Tabelle: 0 im Intervall, sonst mit Vorzeichen. Rundet der Abstand auf 0,0, stehen
    zwei Nachkommastellen da – «−0,0» sähe aus wie ein Fehler, und «0» hieße «im Intervall»."""
    if z is None or z.aave_abstand is None:
        return "–"
    v = float(z.aave_abstand)
    if v == 0:
        return "0"
    text = num(v)
    if text in ("0,0", "−0,0"):
        text = num(v, 2)
    return ("+" if v > 0 else "") + text


def _lage_zelle(z: Zelle | None) -> str:
    """Die Lage als Wort. «unter» und «über» sind die Auskunft und stehen kräftig, «im» ist der Normalfall und
    steht zurückhaltend – über die Schrift, nicht über eine Farbe: Das Wort trägt die Aussage."""
    if z is None or z.lage is None:
        return "<td>–</td>"
    wort = esc(LAGE_KURZ.get(str(z.lage), "–"))
    if z.lage == "im":
        return f'<td class="lage lage-im">{wort}</td>'
    return f'<td class="lage"><strong>{wort}</strong></td>'


def _quellenzeile(a: Aufbau, rid: str) -> str:
    """Verordnung, Seite und RIS – die Seitenzahl auch als Text, weil `#page=` kein Standard des Web ist."""
    q = a.quelle(rid, "PLAN") or a.quelle(rid, "IST")
    if q is None:
        return ""
    pdf, seite, datei, ris = q
    return (
        f'<p class="quelle">Verordnung: <span class="nb">{esc(pdf)}</span>, <b>Seite {seite}</b> · '
        f'<a href="{esc(datei)}#page={seite}" target="_blank" rel="noopener noreferrer">Seite {seite} öffnen</a> · '
        f'<a href="{esc(ris)}" target="_blank" rel="noopener noreferrer">Verordnung im RIS</a></p>'
    )


LESEHILFE = (
    "VD = ÄAVE je 100.000 Einwohner:innen; eine ÄAVE entspricht grundsätzlich einer durchschnittlich arbeitenden "
    "Kassenärztin bzw. einem Kassenarzt des Fachs. Gezählt ist nur die Sachleistung (Kassenvertrag, Ambulatorien, "
    "Spitalsambulanzen), ohne Wahlärzt:innen. Die Soll-Intervalle des ÖSG zählen Wahlärzt:innen mit, die Werte hier "
    "nicht: Liegt ein Fach <b>unter</b> dem Intervall, kann es mit Wahlärzt:innen trotzdem darin liegen; liegt es "
    "<b>über</b> dem Intervall, liegt es mit Wahlärzt:innen erst recht darüber. Innerhalb des Intervalls macht der "
    "ÖSG keinen Unterschied."
)
"""Die eine Lesehilfe unter jeder Tabelle: was VD und ÄAVE sind, der wichtigste Vorbehalt und was «unter» deshalb
heißt (docs/DATEN.md, Fallstricke 1 und 11, «Vergleich mit dem Soll-Intervall»). Steht direkt bei den Zahlen,
nicht in einem Kasten darüber – wer eine Tabelle zitiert, nimmt den Text darunter eher mit als einen Kasten weiter
oben."""

QUELLEN = (
    "Quellen: Verordnungen zu den RSG 2030 (RIS) · Bevölkerung: Statistik Austria – data.statistik.gv.at "
    "(CC BY 4.0, bearbeitet) · Aufteilung 2030 auf Versorgungsregionen: ÖROK-Prognose 2021 (CC BY 4.0, bearbeitet) · "
    "Soll-Intervalle und Versorgungsregionen: ÖSG 2023 (BMASGPK/GÖG)"
)
"""Namensnennung in der Fußzeile jeder Seite, Wortlaut nach LIZENZ_DATEN.md: Die Bevölkerungsdaten stehen unter
CC BY 4.0 und gehen bearbeitet in die Versorgungsdichte ein; die Lizenz verlangt die Nennung bei jeder
Veröffentlichung, ein Link auf die Methodik reicht dafür nicht. Derselbe Text steht in der Fußzeile des Dashboards
(`web/app.js`; Test in tests/test_web.py)."""

IST_HILFE = (
    "Das Soll-Intervall gilt für 2030; am IST-Wert gemessen zeigt es den Abstand zur Norm 2030, keine Verletzung im "
    "IST-Jahr."
)
"""Weil die VD IST in derselben Tabelle neben dem Soll-Intervall steht (docs/DATEN.md, Fallstrick 11)."""

ABSTAND_HILFE = (
    "Abstand zum Soll-Intervall: so viele ÄAVE Sachleistung fehlen im PLAN 2030 bis zur Untergrenze (−) oder liegen "
    "über der Obergrenze (+); 0 heißt im Intervall. Die ÄAVE stehen so in der Verordnung – bei den Ländern, die in "
    "SVE planen, als ÄAVE-Äquivalente –, die Fächer zugeschnitten wie in der Tabelle darüber."
)
"""Unter der ÄAVE-Tabelle: der Abstand ist in ÄAVE angegeben und steht bei seiner Einheit (docs/DATEN.md,
«Vergleich mit dem Soll-Intervall»)."""

STELLEN_HILFE = (
    "Sachleistungsstellen sind Planstellen für Vertragsärzt:innen und geplante ärztliche Vollzeitäquivalente in "
    "Ambulatorien; Niederösterreich nennt sie «Kassenstellen». Sie planen nur den niedergelassenen Bereich und die "
    "Ambulatorien, nicht die Spitalsambulanzen – mit den ÄAVE der Versorgungsdichte deshalb nicht gegeneinander "
    "rechnen. Die Fächer sind wie dort zugeschnitten, nur AM ohne die ZAE, die spitalsambulant sind."
)
"""Unter jeder Stellen-Tabelle. Sachleistung (ÄAVE, mit Spitalsambulanzen) und Sachleistungsstellen (extramural)
sind «nicht zu verwechseln» (docs/METHODIK.md, «Begriffe»; Tabellenband S.232); AM ohne ZAE: docs/DATEN.md,
Tabelle Stellen. Deshalb eine eigene Tabelle und keine Spalte neben den ÄAVE."""

STELLEN_ZUSAMMEN = (
    "Zusätzliche Stellen stehen nur den Versicherten eines Trägers offen. Anders als die IST-Planstellen sind "
    "gemeinsame und zusätzliche Sachleistungsstellen verschiedene Stellen; zusammen ergeben sie alle geplanten Stellen."
)
"""docs/DATEN.md, Tabelle Stellen («IST nicht addieren, PLAN schon»). Die Summe selbst steht noch in keiner Datei
(docs/offene_punkte.md, «alle Sachleistungsstellen als eigene Zeile»)."""

STELLEN_WIEN = (
    "Wien bewertet zusätzliche Sachleistungsstellen nach ihrer Versorgungswirksamkeit (Textteil S.19); eine Wiener "
    "Sachleistungsstelle ist nicht unbedingt eine Stelle im Sinn einer Planstelle."
)
"""Nur auf Seiten mit Wiener Stellen (docs/DATEN.md, «Stellen lesen»; docs/METHODIK.md, «Stellen»)."""


def _vorbehalte_je_zeile(zeilen: list[tuple[str, list[tuple[str, str]]]]) -> tuple[dict[str, str], str]:
    """Vorbehalte einer Tabelle: jeder **einmal**, unter der Tabelle; an den Zeilen, für die er gilt, eine Zahl.

    `zeilen` ist je Tabellenzeile (Schlüssel, [(Kennung, fertiger Text)]). Was für **jede** Zeile gilt (z. B.
    «ohne Patientenströme» auf einer Regionsseite), steht ohne Zahl; der Rest nummeriert in der Reihenfolge des
    ersten Auftretens. «Teil von» bleibt weg: Das sagt der Satz zu PUL und KFO, der unter jeder Tabelle steht.
    Gleiche Kennung mit anderem Text (SVE: «Burgenland plant …», «Kärnten plant …») sind verschiedene Vorbehalte.
    """
    je_zeile = {k: [t for kennung, t in v if kennung != "teil_von"] for k, v in zeilen}
    mengen = [set(v) for v in je_zeile.values()]
    gemeinsam = set.intersection(*mengen) if mengen else set()
    reihenfolge: list[str] = []
    for v in je_zeile.values():
        for t in v:
            if t not in gemeinsam and t not in reihenfolge:
                reihenfolge.append(t)
    nummer = {t: i for i, t in enumerate(reihenfolge, start=1)}
    zeichen = {k: "".join(f"<sup>{nummer[t]}</sup>" for t in v if t in nummer) for k, v in je_zeile.items()}
    erste = next(iter(je_zeile.values()), [])
    punkte = [f"<li>{t}</li>" for t in erste if t in gemeinsam]
    punkte += [f"<li><sup>{nummer[t]}</sup> {t}</li>" for t in reihenfolge]
    return zeichen, (f'<ul class="vorbehalte">{"".join(punkte)}</ul>' if punkte else "")


def _ohne_wert(fehlen: list[str]) -> str:
    return f'<p class="t2">Ohne Wert in dieser Matrix: {" ".join(fehlen)}</p>' if fehlen else ""


def _tabelle_region(a: Aufbau, rid: str, titel: str) -> str:
    """Die erste Tabelle einer Region: Versorgungsdichte im IST und im PLAN 2030, Soll-Intervall, Lage.

    Eine Einheit je Tabelle: hier nur die VD (ÄAVE je 100.000), darunter die ÄAVE selbst mit dem Abstand zum
    Soll-Intervall (`_tabelle_aave_region`), dann die Stellen. IST und PLAN nebeneinander, damit man eine
    Veränderung sieht, ohne eine Differenz zu rechnen: beide Werte stehen so in der Tabelle Versorgungsdichte. Die
    heiklen Fälle an der Grenze trägt die Zahl am Fach («weniger als 1 ÄAVE vom Intervall entfernt»), so bleibt die
    Lage nicht allein stehen (docs/DATEN.md, «Vergleich mit dem Soll-Intervall»).
    """
    zuschnitte, fehlen, roh = [], [], []
    faecher = []
    for f in a.faecher:
        fid = str(f["id"])
        p = a.zelle(rid, "PLAN", fid)
        if p is None and a.zelle(rid, "IST", fid) is None:
            grund = a.kein_wert(rid, "PLAN", fid)
            fehlen.append(f"<b>{esc(fid)}</b> {esc(f['name'])}: {grund or 'kein Wert in dieser Matrix.'}")
            continue
        faecher.append(f)
        roh.append((fid, _kennungen(a, rid, fid)))
    zeichen, vorbehalte = _vorbehalte_je_zeile(roh)
    jahr = esc(a.wert(rid, "IST", "AM", 3))
    zeilen = []
    for f in faecher:
        fid, dg = str(f["id"]), _stellen_vd(f)
        p = a.zelle(rid, "PLAN", fid)
        mark = ZUSCHNITT_ZEICHEN if _zuschnitt_abweichend(p.zuschnitt if p else None, fid) else ""
        if mark and p is not None and str(p.zuschnitt) not in zuschnitte:
            zuschnitte.append(str(p.zuschnitt))
        zeilen.append(
            f'<tr><th scope="row">{esc(f["name"])} <span class="t2">({esc(fid)}{mark})</span>{zeichen[fid]}</th>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 0), dg)}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 0), dg)}</td>'
            f'<td class="num">{num(f["min"], dg)}–{num(f["max"], dg)}</td>'
            f"{_lage_zelle(p)}</tr>"
        )
    n = '<th scope="col" class="num">'
    kopf = (
        f'<thead><tr><th scope="col">Fach</th>{n}VD IST {jahr}</th>{n}VD PLAN 2030</th>{n}Soll-Intervall</th>'
        '<th scope="col">Lage PLAN 2030</th></tr></thead>'
    )
    tabelle = (
        f'<div class="scroll"><table class="t">{_beschriftung(titel)}{kopf}<tbody>{"".join(zeilen)}</tbody>'
        "</table></div>"
    )
    return (
        tabelle
        + f'<div class="lesehilfe"><p>{LESEHILFE} {IST_HILFE}</p>'
        + vorbehalte
        + _zuschnitt_zeile(zuschnitte)
        + TEILMENGEN_HINWEIS
        + _ohne_wert(fehlen)
        + "</div>"
    )


def _tabelle_aave_region(a: Aufbau, rid: str) -> str:
    """Die zweite Tabelle einer Region: die ÄAVE im IST und im PLAN 2030 und der Abstand zum Soll-Intervall.

    Die ÄAVE sind, was in der Verordnung steht – wer «Seite … öffnen» klickt, findet sie dort. Der Abstand ist in
    ÄAVE angegeben und steht deshalb hier, bei seiner Einheit. Alle Werte aus der Tabelle Versorgungsdichte.
    """
    name = esc(a.region(rid)["name"])
    jahr = esc(a.wert(rid, "IST", "AM", 3))
    zeilen = []
    for f in a.faecher:
        fid = str(f["id"])
        p = a.zelle(rid, "PLAN", fid)
        if p is None and a.zelle(rid, "IST", fid) is None:
            continue
        mark = ZUSCHNITT_ZEICHEN if _zuschnitt_abweichend(p.zuschnitt if p else None, fid) else ""
        zeilen.append(
            f'<tr><th scope="row">{esc(f["name"])} <span class="t2">({esc(fid)}{mark})</span></th>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 1))}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 1))}</td>'
            f'<td class="num">{_abstand(p)}</td></tr>'
        )
    n = '<th scope="col" class="num">'
    titel = _beschriftung(
        f"{name}: ÄAVE der Sachleistung je Fach im IST {jahr} und im PLAN 2030, Abstand zum Soll-Intervall"
    )
    return (
        f'<div class="scroll"><table class="t">{titel}<thead><tr><th scope="col">Fach</th>{n}ÄAVE IST {jahr}</th>'
        f"{n}ÄAVE PLAN 2030</th>{n}Abstand PLAN 2030 zum Soll-Intervall</th></tr></thead>"
        f"<tbody>{''.join(zeilen)}</tbody></table></div>"
        f'<div class="lesehilfe"><p>{ABSTAND_HILFE}</p></div>'
    )


def seite_fach(a: Aufbau, f: dict[str, object]) -> Seite:
    """Ein Fach über alle Versorgungsregionen – dieselben drei Tabellen wie auf der Seite einer Region, gekippt.
    Kein Ranking, keine Österreich-Zahl."""
    fid, name, dg = str(f["id"]), str(f["name"]), _stellen_vd(f)
    regionen, ohne, roh = [], [], []
    for r in a.regionen:
        if r["ebene"] != "VR":
            continue
        rid = str(r["id"])
        if a.zelle(rid, "PLAN", fid) is None and a.zelle(rid, "IST", fid) is None:
            ohne.append(f"{esc(rid)} {esc(r['name'])}")
            continue
        regionen.append(r)
        roh.append((rid, _kennungen(a, rid, fid)))
    zeichen, vorbehalte = _vorbehalte_je_zeile(roh)
    hoch = a.hoch(f"fach/{fid}/")
    vd_zeilen, aave_zeilen, stellen_zeilen = [], [], []
    stellen_je_region: dict[str, dict[str, object]] = {}
    jahre: dict[str, list[str]] = {}
    for r in regionen:
        rid = str(r["id"])
        p = a.zelle(rid, "PLAN", fid)
        jahr = str(a.wert(rid, "IST", fid, 3))
        land = str(r["land_name"])
        if land not in jahre.setdefault(jahr, []):
            jahre[jahr].append(land)
        vd_zeilen.append(
            f'<tr><th scope="row"><a href="{hoch}vr/{esc(rid)}/">{esc(rid)} {esc(r["name"])}</a>{zeichen[rid]}</th>'
            f"<td>{esc(land)}</td>"
            f'<td class="num">{num(a.wert(rid, "IST", fid, 0), dg)}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 0), dg)}</td>'
            f"{_lage_zelle(p)}</tr>"
        )
        aave_zeilen.append(
            f'<tr><th scope="row">{esc(rid)} {esc(r["name"])}</th>'
            f'<td class="num">{num(a.wert(rid, "IST", fid, 1))}</td>'
            f'<td class="num">{num(a.wert(rid, "PLAN", fid, 1))}</td>'
            f'<td class="num">{_abstand(p)}</td></tr>'
        )
        stellen_je_region[rid] = a.stellen_plan(rid, fid)
    # Wie auf der Seite einer Region: gemeinsame und zusätzliche Stellen je Träger. Im PLAN sind das verschiedene
    # Stellen (docs/DATEN.md, Tabelle Stellen) – nur die gemeinsamen zu zeigen, verzerrte den Vergleich der Regionen
    # dort, wo ein Land viele trägerspezifische Stellen plant. Eine Spalte mit lauter 0 (ÖGK) entfällt.
    spalten = [
        z
        for z in STELLEN_PLAN
        if z == "slst_gemeinsam"
        or any(not pd.isna(w.get(z)) and float(str(w.get(z) or 0)) != 0 for w in stellen_je_region.values())
    ]
    for r in regionen:
        rid = str(r["id"])
        w = stellen_je_region[rid]
        stellen_zeilen.append(
            f'<tr><th scope="row">{esc(rid)} {esc(r["name"])}</th>'
            + "".join(f'<td class="num">{num(w.get(z))}</td>' for z in spalten)
            + "</tr>"
        )
    stellen_kopf = "".join(f'<th scope="col" class="num">{esc(STELLEN_KOPF[z])}</th>' for z in spalten)
    ist_jahre = "; ".join(f"{esc(j)} in {_und([esc(x) for x in jahre[j]])}" for j in sorted(jahre))
    teil = (
        f'Teil von <a href="{hoch}fach/{esc(f["teil_von"])}/">{esc(f["teil_von"])}</a>, mit eigenem Soll-Intervall '
        "(nicht addieren)"
        if f["teil_von"]
        else ""
    )
    soll = (
        f'Soll-Intervall des ÖSG <b class="num">{num(f["min"], dg)} bis {num(f["max"], dg)}</b> ÄAVE je 100.000 '
        "Einwohner:innen (ÖSG-Textband S.39)"
    )
    n = '<th scope="col" class="num">'
    b_vd = (
        f"{esc(name)} ({esc(fid)}): Versorgungsdichte der Sachleistung je Versorgungsregion im IST und im PLAN 2030, "
        "Lage zum Soll-Intervall des ÖSG"
    )
    b_aave = f"{esc(name)} ({esc(fid)}): ÄAVE der Sachleistung je Versorgungsregion, Abstand zum Soll-Intervall"
    b_stellen = (
        f"{esc(name)} ({esc(fid)}): Sachleistungsstellen im PLAN 2030 je Versorgungsregion, gemeinsame aller Träger "
        "und zusätzliche einzelner Träger"
    )
    rumpf = f"""<h1>{esc(name)} ({esc(fid)})</h1>
{_kopfzeile([soll, teil])}
<h2 id="vd">Versorgungsdichte: {esc(name)}</h2>
<div class="scroll"><table class="t">{_beschriftung(b_vd)}<thead><tr><th scope="col">Versorgungsregion</th>
<th scope="col">Bundesland</th>{n}VD IST</th>{n}VD PLAN 2030</th><th scope="col">Lage PLAN 2030</th></tr></thead>
<tbody>{"".join(vd_zeilen)}</tbody></table></div>
<div class="lesehilfe"><p>{LESEHILFE} {IST_HILFE} IST-Jahr: {ist_jahre}. Keine Summe und kein Österreich-Wert:
Der ÖSG misst je Versorgungsregion.</p>
{vorbehalte}
{f'<p class="t2">Ohne Wert in der Matrix: {", ".join(ohne)}.</p>' if ohne else ""}</div>
<h2 id="aave">ÄAVE: {esc(name)}</h2>
<div class="scroll"><table class="t">{_beschriftung(b_aave)}<thead><tr><th scope="col">Versorgungsregion</th>
{n}ÄAVE IST</th>{n}ÄAVE PLAN 2030</th>{n}Abstand PLAN 2030 zum Soll-Intervall</th></tr></thead>
<tbody>{"".join(aave_zeilen)}</tbody></table></div>
<div class="lesehilfe"><p>{ABSTAND_HILFE}</p></div>
<h2 id="stellen">Sachleistungsstellen PLAN 2030: {esc(name)}</h2>
<div class="scroll"><table class="t">{_beschriftung(b_stellen)}
<thead><tr><th scope="col">Versorgungsregion</th>{stellen_kopf}</tr></thead>
<tbody>{"".join(stellen_zeilen)}</tbody></table></div>
<div class="lesehilfe"><p>{STELLEN_HILFE} {STELLEN_ZUSAMMEN} {STELLEN_WIEN}</p>
{TEILMENGEN_HINWEIS}</div>"""
    titel = f"Planstellen und Versorgungsdichte {name} 2030 | RSG 2030"
    beschreibung = (
        f"{name} ({fid}) in allen 32 Versorgungsregionen: Versorgungsdichte 2030 im Vergleich zum "
        f"Soll-Intervall des ÖSG ({num(f['min'], dg)}–{num(f['max'], dg)} ÄAVE je 100.000)."
    )
    pfadleiste = (("RSG 2030", "daten/"), ("Fächer", "daten/#faecher"), (name, ""))
    return Seite(f"fach/{fid}/", titel, beschreibung, rumpf, f"?fach={fid}", pfadleiste)


def _urheber(a: Aufbau, pfad: str, dashboard: str = "") -> str:
    """Fußzeile: wer die Seiten erstellt hat, mit den Vorbehalten im selben Satz, und die Links, die eine
    veröffentlichte Seite braucht (docs/WEB.md, Entscheidung 15). Zwei Zeilen, Wortlaut wie im Dashboard. Die ORCID
    steht in den strukturierten Daten (`creator`), nicht sichtbar auf jeder Seite; die Methode einmal auf /daten/."""
    meta = a.daten["meta"]
    repo, version = str(meta["repo"]), esc(meta["version"])  # type: ignore[index]
    neu = 'target="_blank" rel="noopener noreferrer"'
    return f"""<p>Inoffizielle Aufbereitung amtlicher Daten, erstellt von
<a href="https://loesungswerk.at/max-plischke" {neu}>Max Plischke</a> (Lösungswerk), ohne Auftrag. Maßgeblich sind
die Verordnungen im RIS; Angaben ohne Gewähr.</p>
<p><a href="{repo}/releases/tag/{version}" {neu}>Release {version}</a> ·
<a href="https://creativecommons.org/licenses/by/4.0/deed.de" {neu}>CC BY 4.0</a> ·
<a href="{repo}/blob/{version}/docs/METHODIK.md" {neu}>Methodik</a> ·
<a href="{repo}/blob/{version}/CITATION.cff" {neu}>Zitieren</a> ·
<a href="{repo}/issues/new?template=wert_weicht_ab.yml" {neu}>Fehler melden</a> ·
<a href="https://loesungswerk.at/impressum" {neu}>Impressum</a> ·
<a href="https://loesungswerk.at/datenschutz" {neu}>Datenschutz</a></p>
<p class="t2">{QUELLEN}</p>"""


def _kopfzeile(teile: list[str]) -> str:
    """Die Eckdaten in einer Zeile unter der Überschrift, getrennt durch Punkte."""
    return f'<p class="eckdaten">{" · ".join(t for t in teile if t)}</p>'


def seite_region(a: Aufbau, r: dict[str, object]) -> Seite:
    """Eine Versorgungsregion oder ein Bundesland: Eckdaten, Quelle, die Tabelle mit ihren Vorbehalten, dann zum
    Aufklappen der Apparat (docs/WEB.md, «Lesefassung»)."""
    rid, ebene = str(r["id"]), str(r["ebene"])
    name = str(r["name"])
    nummer = f" (VR {rid})" if ebene == "VR" else ""
    titel = f"Planstellen und Versorgungsdichte {name}{nummer} 2030 | RSG 2030"
    jahr_ist = a.wert(rid, "IST", "AM", 3)
    bev_ist, bev_plan = a.wert(rid, "IST", "AM", 2), a.wert(rid, "PLAN", "AM", 2)
    hoch = a.hoch(a.pfad(r))
    land_pfad = f"bl/{LAND_SLUG[str(r['land'])]}/"
    # Dass die VR-Zahl geschätzt ist, muss dastehen; wie sie geschätzt ist, steht in der Methodik
    geschaetzt = " (für die Region geschätzt)" if ebene == "VR" else ""
    bevoelkerung = (
        f"Wohnbevölkerung {_tausend(bev_plan)} zum 1.1.2030{geschaetzt}, {_tausend(bev_ist)} am 1.1.{esc(jahr_ist)}"
    )
    if ebene == "VR":
        bezirke = a.bezirke(rid)
        eck = [
            f'<a href="{hoch}{land_pfad}">{esc(r["land_name"])}</a>',
            f"{'Bezirk' if len(bezirke) == 1 else 'Bezirke'} {esc(', '.join(bezirke))} "
            "(geplant wird je Versorgungsregion, nicht je Bezirk)",
            bevoelkerung,
        ]
        pfadleiste: tuple[tuple[str, str], ...] = (("RSG 2030", "daten/"), (str(r["land_name"]), land_pfad), (name, ""))
        weiter = [
            f'<a href="{hoch}vr/{v}/">{esc(a.region(v)["name"])}</a>'
            for v in a.vr_des_landes(str(r["land_name"]))
            if v != rid
        ]
        verweis = (
            f'<p class="weiter">Weitere Regionen in {esc(r["land_name"])}: {" · ".join(weiter)}</p>' if weiter else ""
        )
    else:
        vr = a.vr_des_landes(str(r["land_name"]))
        liste = ", ".join(f'<a href="{hoch}vr/{v}/">{esc(a.region(v)["name"])}</a>' for v in vr)
        eck = [f"Bundesland mit {len(vr)} Versorgungsregionen: {liste}", bevoelkerung]
        pfadleiste = (("RSG 2030", "daten/"), (name, ""))
        verweis = ""
    beschriftung = (
        f"{esc(name)}{esc(nummer)}: Versorgungsdichte der Sachleistung je Fach im IST und im PLAN 2030, Lage zum "
        "Soll-Intervall des ÖSG"
    )
    rumpf = f"""<h1>{esc(name)}{esc(nummer)}</h1>
{_kopfzeile(eck)}
{_quellenzeile(a, rid)}
<h2 id="vd">Versorgungsdichte: {esc(name)}</h2>
{_tabelle_region(a, rid, beschriftung)}
<h2 id="aave">ÄAVE: {esc(name)}</h2>
{_tabelle_aave_region(a, rid)}
<h2 id="stellen">Sachleistungsstellen PLAN 2030: {esc(name)}</h2>
{_tabelle_stellen(a, rid)}
<h2 id="herkunft">Herkunft</h2>
{_fussnoten(a, r)}
{_korrekturen(a, r)}
{_abweichungen(a, r)}
{_offene_fragen(a, r)}
{verweis}"""
    beschreibung = (
        f"Sachleistungsstellen und Versorgungsdichte 2030 für {name}{nummer} je Fach, verglichen mit dem "
        "Versorgungsdichte-Soll-Intervall des ÖSG – aus der Verordnung zum RSG 2030."
    )
    return Seite(a.pfad(r), titel, beschreibung, rumpf, f"?region={r['slug']}", pfadleiste)


def _pfadleiste(a: Aufbau, s: Seite) -> tuple[str, str]:
    """Brotkrumen als Navigation und als `BreadcrumbList`: wo die Seite steht, und ein Klick zum Land."""
    if not s.pfadleiste:
        return "", ""
    hoch = a.hoch(s.pfad)
    punkte, json_punkte = [], []
    for i, (name, ziel) in enumerate(s.pfadleiste, start=1):
        if ziel:
            punkte.append(f'<li><a href="{hoch}{esc(ziel)}">{esc(name)}</a></li>')
        else:
            punkte.append(f'<li aria-current="page">{esc(name)}</li>')
        adresse = f"{a.basis}/{ziel or s.pfad}"
        json_punkte.append(f'{{"@type":"ListItem","position":{i},"name":{_json(name)},"item":{_json(adresse)}}}')
    nav = f'<nav class="pfad" aria-label="Pfad"><ol>{"".join(punkte)}</ol></nav>'
    ld = (
        '<script type="application/ld+json">\n'
        f'{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{",".join(json_punkte)}]}}\n'
        "</script>"
    )
    return nav, ld


def _dokument(a: Aufbau, s: Seite) -> str:
    """Eine ganze Seite: Kopf mit canonical und Dataset-Bezug, Rumpf, Fußzeile. Kein Skript, kein fremder Server.

    Oben stehen die beiden Wege durch den Datensatz nebeneinander: nachschlagen (diese Seiten) und vergleichen
    (das Dashboard, mit vorbelegtem Zustand). So sieht man, warum es beides gibt (docs/WEB.md, «Lesefassung»).
    """
    meta = a.daten["meta"]
    version = esc(meta["version"])  # type: ignore[index]
    hoch = esc(a.hoch(s.pfad))
    nav, ld_pfad = _pfadleiste(a, s)
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
{ld_pfad}
</head>
<body>
<a class="skip" href="#inhalt">Zum Inhalt</a>
<header class="kopf">
  <p class="eyebrow"><a href="{hoch}daten/">RSG 2030 – Planungsmatrizen der Verordnungen</a> · Release {version}</p>
  <nav class="bereiche" aria-label="Bereiche">
    <a href="{hoch}daten/"{' aria-current="page"' if s.pfad == "daten/" else ""}>Nachschlagen: Regionen und Fächer</a>
    <a href="{hoch}{esc(s.dashboard)}">Vergleichen: interaktive Matrix</a>
  </nav>
</header>
<main id="inhalt">
{nav}
{s.rumpf}
</main>
<footer class="fuss">
{_urheber(a, s.pfad, s.dashboard)}
</footer>
</body>
</html>
"""


def _verzeichnis_regionen(a: Aufbau) -> str:
    """Je Bundesland seine Versorgungsregionen – der Weg zur eigenen Region in zwei Klicks, ohne Suchfeld."""
    bloecke = []
    for r in a.regionen:
        if r["ebene"] != "BL":
            continue
        vr = a.vr_des_landes(str(r["land_name"]))
        punkte = "".join(f'<li><a href="../vr/{esc(v)}/">{esc(a.region(v)["name"])}</a></li>' for v in vr)
        bloecke.append(
            f'<section><h3><a href="../bl/{LAND_SLUG[str(r["land"])]}/">{esc(r["land_name"])}</a></h3>'
            f'<ul class="vr-liste">{punkte}</ul></section>'
        )
    return f'<div class="verzeichnis">{"".join(bloecke)}</div>'


def _verzeichnis_faecher(a: Aufbau) -> str:
    """Die 17 Fächer mit ihrem Soll-Intervall – das Intervall gilt für ganz Österreich, also steht es hier."""
    punkte = []
    for f in a.faecher:
        dg = _stellen_vd(f)
        teil = f" · Teil von {esc(f['teil_von'])}" if f["teil_von"] else ""
        punkte.append(
            f'<li><a href="../fach/{esc(f["id"])}/">{esc(f["name"])}</a> '
            f'<span class="t2">{esc(f["id"])} · Soll-Intervall <span class="num">{num(f["min"], dg)}–'
            f"{num(f['max'], dg)}</span>{teil}</span></li>"
        )
    return f'<ul class="fach-liste">{"".join(punkte)}</ul>'


def seite_index(a: Aufbau) -> Seite:
    """Der Einstieg: wofür der Datensatz da ist, das Verzeichnis der Regionen und Fächer, die Downloads – und am
    Ende alle Zeilen «insgesamt» in einer Tabelle, zugeklappt.

    Bewusst kein 537-zeiliges Raster als Hauptinhalt: Wer vergleichen will, nimmt das Dashboard, wer rechnen will,
    die CSV. Die große Tabelle steht trotzdem im HTML (zum Durchsuchen mit Strg+F und für Maschinen), nur nicht
    als das Erste, was man sieht.

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
                f"{_lage_zelle(p)}"
                f'<td class="num">{_abstand(p)}</td></tr>'
            )
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
<h1>Versorgungsdichte und Planstellen 2030 je Region und Fach</h1>
<p>Was die Verordnungen zu den Regionalen Strukturplänen Gesundheit (RSG) 2030 für die ambulante ärztliche
Versorgung festlegen, je Versorgungsregion und Fach, mit Verordnung und Seite zu jeder Zahl. Zum Vergleichen über
alle Regionen auf einmal: <a href="../">interaktive Matrix</a>.</p>
<p class="t2">{LESEHILFE}</p>
<h2 id="regionen">Nach Region</h2>
{_verzeichnis_regionen(a)}
<h2 id="faecher">Nach Fach</h2>
{_verzeichnis_faecher(a)}
<h2 id="herunterladen">Daten und Quellen</h2>
<p><a href="{
        rel
    }/RSG_2030_Versorgungsdichte.csv" target="_blank" rel="noopener noreferrer">Versorgungsdichte (CSV)</a> ·
<a href="{rel}/RSG_2030_Stellen.csv" target="_blank" rel="noopener noreferrer">Stellen (CSV)</a> ·
<a href="{rel}/RSG_2030_Planungsmatrizen.csv" target="_blank" rel="noopener noreferrer">Planungsmatrizen (CSV)</a> ·
<a href="{rel}/RSG_2030_Planungsmatrizen.xlsx" target="_blank" rel="noopener noreferrer">Excel-Mappe</a> ·
<a href="{rel}/Pruefbericht.md" target="_blank" rel="noopener noreferrer">Prüfbericht</a></p>
<p>Die Planungsmatrizen aller neun Verordnungen sind aus den PDFs ausgelesen, jede Zelle zweimal unabhängig
gelesen, jede Abweichung vom PDF mit einer dokumentierten Regel begründet; Versorgungsdichte, Lage und ÄAVE-Abstand
sind nach der Methode des ÖSG gerechnet.</p>
<p>Vor der Verwendung bitte lesen:
<a href="{repo}/blob/{version}/docs/DATEN.md#fallstricke" target="_blank" rel="noopener noreferrer">Fallstricke</a> ·
<a href="{repo}/blob/{version}/docs/METHODIK.md" target="_blank" rel="noopener noreferrer">Methodik</a> ·
<a href="{repo}/blob/{version}/docs/PRUEFUNG.md" target="_blank" rel="noopener noreferrer">Prüfkonzept</a></p>
{_quellen_uebersicht(a)}
<details><summary>Was dieser Datensatz nicht tut</summary><ul>
<li>Er interpretiert nicht: Die Werte stehen so da, wie die Verordnungen sie drucken; jede Abweichung vom PDF ist
eine dokumentierte Regel mit Begründung.</li>
<li>Versorgungsdichte, Lage, Position und ÄAVE-Abstand sind die einzigen Kennzahlen; sie stehen in der
veröffentlichten Tabelle.</li>
<li>Keine Österreich-Werte: Der ÖSG misst je Versorgungsregion, und ein Österreich-IST würde zwei IST-Jahre mischen
(2022 und 2023, je nach Bundesland).</li>
<li>Kein Vergleich der Stellen IST → PLAN: IST-Planstellen und PLAN-Sachleistungsstellen zählen Verschiedenes.</li>
<li>Keine Daten von außerhalb der Verordnungen, der ÖSG-Richtwerte und der amtlichen Bevölkerungsdaten.</li>
</ul></details>
<details class="alle"><summary>Alle {len(zeilen)} Werte in einer Tabelle (PLAN 2030)</summary>
<div class="scroll"><table class="t t-index">{
        _beschriftung(
            f"Versorgungsdichte PLAN 2030 je Versorgungsregion und Fach, alle {len(zeilen)} Zeilen «ÄAVE insgesamt» der "
            "Tabelle Versorgungsdichte, im Vergleich zum Soll-Intervall des ÖSG"
        )
    }<thead><tr><th scope="col" class="num">VR</th><th scope="col">Region</th>
<th scope="col">Fach</th><th scope="col" class="num">ÄAVE PLAN 2030</th><th scope="col" class="num">VD PLAN 2030</th><th scope="col" class="num">VDmin</th>
<th scope="col" class="num">VDmax</th><th scope="col">Lage PLAN 2030</th><th scope="col" class="num">Abstand PLAN 2030</th></tr></thead>
<tbody>{"".join(zeilen)}</tbody></table></div>
</details>"""
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
    # Dieselben Schriften wie das Dashboard, aus demselben Ordner – auch wenn «web» nicht vorher lief
    shutil.copytree(web_dir() / "fonts", ziel / "fonts", dirs_exist_ok=True)
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
