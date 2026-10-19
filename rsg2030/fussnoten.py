"""Fußnoten der Planungsmatrizen: Verzeichnis, Vollständigkeit, Einordnung.

Eine Fußnote kann die Bedeutung einer Zahl ändern, ohne dass eine Summe bricht («ZMK einschließlich KFO», «spitalsambulant
= ZAE»). Deshalb steht jede Fußnote jeder Matrix im Verzeichnis `eingaben/<Stand>/fussnoten.csv` – Text wie gedruckt und
eine Einordnung, was sie für die Daten bedeutet. Wer was prüft (docs/PRUEFUNG.md, «Wer prüft was»):

- **Maschine (bei jedem Lauf):** Jede Fußnote, die auf einer Matrixseite steht, ist im Verzeichnis, und jeder Text im
  Verzeichnis steht so auf seiner Seite. Fußnoten, die wörtlich der ÖSG-Vorlage entsprechen
  (`oesg_methodik/referenz/oesg_rsgpm_fussnoten.csv`, Tabellenband Anhang 9), sind damit erledigt; ihre Bedeutung
  steht einmal in docs/DATEN.md.
- **Mensch (Freigabe, Blatt «Fußnoten»):** jede andere Fußnote – auch eine Vorlage, die ein Land mit Zahlen gefüllt
  hat – mit ihrer Einordnung; dazu alle Fußnoten der Bildseiten (dort gibt es keinen Text zum Abgleichen).

Fußnoten stehen meist unter der Tabelle mit Zeichen «(1)», «(2)» …, auch mehrspaltig nebeneinander. Oberösterreich
setzt «*» an Spaltenköpfe und Zeilen und erklärt sie auf der folgenden Seite unter «Fußnoten OÖ Gesamt» bzw.
«Fußnoten VR 41» als «Bezug - Text».

    python -m rsg2030 fussnoten     # neue Fußnoten als Entwurf ins Verzeichnis (bestehende Einträge bleiben)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

from oesg_methodik.pfade import OESG_RSGPM_FUSSNOTEN_CSV
from rsg2030.config import eingaben_dir
from rsg2030.manuell import manuelle_matrizen
from rsg2030.matrix_extract import _ist_labelbeginn, _ist_werttoken, _kopfspalten, _pdf_zeilen, kompakt
from rsg2030.protokoll import einrichten
from rsg2030.seitenregister import Rsg2030Quelle, lade_seitenregister

log = logging.getLogger(__name__)

DATEI = "fussnoten.csv"
SPALTEN = ["Land", "Ebene", "Region_ID", "PDF", "Seite", "Zeichen", "Text", "Einordnung", "Verweis", "Anmerkung"]
EINORDNUNGEN = {
    "Vorlage": "Text der ÖSG-Vorlage, nicht ausgefüllt – Bedeutung in docs/DATEN.md",
    "Hinweis": "erläutert, ändert weder eine Zahl noch, was sie bedeutet",
    "Teilmenge": "nennt einen «davon»-Wert (z. B. EVA, UC, PSD), der nicht als eigene Zelle übernommen wird",
    "betrifft Werte": "ändert Zahlen oder ihre Bedeutung – Verweis auf Regel bzw. Doku-Stelle",
    "Methodenfrage": "offen – Verweis auf docs/offene_punkte.md",
}
MIT_VERWEIS = {"betrifft Werte", "Methodenfrage"}

_ZEICHEN = re.compile(r"^\((\d{1,2})\)")
"""Fußnotenzeichen am Wortanfang, auch angeklebt: «(5)spitalsambulant»."""
_ZEICHEN_IM_TEXT = re.compile(r"\((\d{1,2}(?:\s*,\s*\d{1,2})*)\)")
_OOE_KOPF = re.compile(r"^\*?\s*fußnoten(oö|vr\d\d)")
_OOE_ENDE = re.compile(r"^akut-?krankenanstalten")
_OOE_BEZUG = re.compile(r"^(?P<bezug>.{1,45}?)\s+-\s+(?P<text>\S.*)$")
_SPALTENLUECKE = 12.0
"""Größere Lücke zwischen zwei Wörtern einer Zeile: nächste Fußnotenspalte (mehrspaltiger Satz, NÖ)."""
_MAX_ABSTAND = 14.0
_FUSSZEILE = re.compile(r"seite\d+von\d+")
"""Größerer Abstand zur vorigen Fußnotenzeile: kein Fortsetzungstext mehr."""


def pfad() -> Path:
    return eingaben_dir() / DATEI


def norm(text: str) -> str:
    """Text zum Vergleichen: Leerraum vereinheitlicht, Gedankenstriche als «-», kein Leerzeichen nach «(4)»."""
    t = re.sub(r"[‐-―−]", "-", text)
    return re.sub(r"\s+", " ", t).strip()


def vorlage() -> pd.DataFrame:
    return pd.read_csv(OESG_RSGPM_FUSSNOTEN_CSV, dtype=str)


def vorlagentexte() -> set[str]:
    """Texte der Vorlage, verglichen ohne Leerraum; die zwei Teile von (5) auch zusammen, wie sie meist dastehen."""
    v = vorlage()
    texte = list(v["Text"]) + [" ".join(g) for _, g in v.groupby("Zeichen")["Text"] if len(g) > 1]
    return {kompakt(norm(t)) for t in texte}


def ist_vorlage(text: str) -> bool:
    """Wörtlich wie die ÖSG-Vorlage, Platzhalter «x» nicht ausgefüllt? Das Zeichen zählt nicht – manche Länder
    nummerieren anders (Salzburg: «(1) zugeordnet zu CH»)."""
    return kompakt(norm(text)) in vorlagentexte()


# --- Entwurf: Fußnoten einer Seite finden -------------------------------------------------------


@dataclass
class _Fussnote:
    zeichen: str
    x: float
    teile: list[str]

    @property
    def text(self) -> str:
        return norm(" ".join(self.teile))


def _laeufe(woerter: list[dict]) -> list[tuple[str | None, float, list[str]]]:
    """Eine Zeile in Läufe zerlegen, je Fußnotenzeichen ein neuer Lauf: (Zeichen oder None, x, Wörter)."""
    out: list[tuple[str | None, float, list[str]]] = []
    vorher: dict | None = None
    for w in woerter:
        m = _ZEICHEN.match(w["text"])
        spaltenwechsel = vorher is not None and w["x0"] - vorher["x1"] > _SPALTENLUECKE
        if m:
            rest = w["text"][m.end() :]
            out.append((f"({m.group(1)})", w["x0"], [rest] if rest else []))
        elif out and not spaltenwechsel:
            out[-1][2].append(w["text"])
        else:
            out.append((None, w["x0"], [w["text"]]))
        vorher = w
    return out


def _ist_tabelle(text: str, woerter: list[dict]) -> bool:
    """Gehört die Zeile zu einer Tabelle (Kopf, Zeile, Werte, Kürzelzeile wie bei den Krankenanstalten)?"""
    k = kompakt(text)
    kuerzel = sum(bool(re.fullmatch(r"[A-ZÄÖÜ][A-ZÄÖÜ/\-*]{1,9}(\(\d+(,\d+)*\))?\S*", w["text"])) for w in woerter)
    return kuerzel >= 8 or bool(
        _kopfspalten_ok(woerter)
        or (_ist_labelbeginn(k) and not _ZEICHEN.match(k))
        or sum(_ist_werttoken(w["text"]) for w in woerter) >= 5
    )


def _kopfspalten_ok(woerter: list[dict]) -> bool:
    from rsg2030.matrix_extract import _PdfZeile

    return _kopfspalten(_PdfZeile(woerter[0]["top"], woerter)) is not None


def fussnoten_seite(page) -> list[tuple[str, str]]:
    """(Zeichen, Text) der Fußnoten «(n) …» einer Seite; gleiche Zeichen zusammengeführt («(5)spitalsambulant …»,
    «(5)extramural …»). Mehrspaltig gesetzte Fußnoten: Fortsetzungstext gehört zur Fußnote, deren Zeichen links davon
    am nächsten steht."""
    zeilen = _pdf_zeilen(page.extract_words())
    offen: list[_Fussnote] = []
    alle: list[_Fussnote] = []
    letzte_top: float | None = None
    for z in zeilen:
        text = " ".join(w["text"] for w in z.words)
        if _FUSSZEILE.search(kompakt(text)):
            continue
        laeufe = _laeufe(z.words)
        beginnt = laeufe[0][0] is not None and any(t for t in laeufe[0][2] if re.search(r"[A-Za-zÄÖÜäöü]", t))
        if not re.search(r"[a-zäöüß]{2}", text):
            continue  # nur Zeichen und Zahlen, z. B. hochgestellt in der Tabelle: «(8) 15(9)», «(1) PAL(2)PSO-…»
        weiter = (
            offen and letzte_top is not None and z.top - letzte_top <= _MAX_ABSTAND and not _ist_tabelle(text, z.words)
        )
        if not (beginnt or (laeufe[0][0] is not None) or weiter):
            offen = []
            continue
        if not beginnt and laeufe[0][0] is None and not weiter:
            offen = []
            continue
        for zeichen, x, woerter in laeufe:
            if zeichen is not None and woerter and not any(re.search(r"[a-zäöüß]", w) for w in woerter):
                continue  # hochgestelltes Zeichen in der Tabelle («(8) 15(9)», «(1) PAL(2)PSO-…»), keine Fußnote
            if zeichen is not None:
                f = _Fussnote(zeichen, x, list(woerter))
                offen.append(f)
                alle.append(f)
            elif offen:
                # die zuletzt begonnene Fußnote der Spalte links davon
                links = [i for i, f in enumerate(offen) if f.x <= x + 6]
                if links:
                    rechts = max(offen[i].x for i in links)
                    ziel = offen[max(i for i in links if offen[i].x >= rechts - 3)]
                else:
                    ziel = offen[0]
                ziel.teile += woerter
        letzte_top = z.top
    zusammen: dict[str, list[str]] = {}
    for f in alle:
        if f.text:
            zusammen.setdefault(f.zeichen, []).append(f.text)
    return [(z, " ".join(dict.fromkeys(t))) for z, t in zusammen.items()]


def fussnoten_ooe(page) -> list[tuple[str, str]]:
    """OÖ: Block «Fußnoten OÖ Gesamt» bzw. «Fußnoten VR 41», Teil «Ambulante ärztliche Versorgung»: «Bezug - Text»."""
    out: list[list[str]] = []
    drin = False
    for z in (page.extract_text() or "").splitlines():
        k = kompakt(z)
        if _OOE_KOPF.match(k):
            drin = True
            continue
        if not drin or k == "ambulanteärztlicheversorgung":
            continue
        if _OOE_ENDE.match(k):
            break
        m = _OOE_BEZUG.match(z.strip())
        if m:
            out.append([m.group("bezug").strip(), m.group("text")])
        elif out:
            out[-1][1] += " " + z.strip()
    return [(f"*{b}", norm(t)) for b, t in out]


@dataclass(frozen=True)
class Matrixseite:
    land: str
    ebene: str
    region_id: str
    pdf: Path
    seite_idx: int
    """0-basiert: Seite, auf der die Fußnoten stehen (Matrixseite, Folgeseite oder OÖ-Fußnotenseite)."""


def seiten(quellen: tuple[Rsg2030Quelle, ...] | None = None) -> list[Matrixseite]:
    """Alle Seiten mit Fußnoten zu einer Matrix: Matrix- und Folgeseiten; in OÖ die Seite danach (Fußnotenblock)."""
    out: list[Matrixseite] = []
    for q in quellen or lade_seitenregister():
        matrizen = [("BL", q.land, (q.seite_idx,))] + [
            ("VR", vr.region_id, (vr.seite_idx, *vr.folgeseiten_idx)) for vr in q.vr
        ]
        for ebene, rid, idx in matrizen:
            for i in idx:
                out.append(Matrixseite(q.land, ebene, rid, q.pdf, i))
            if q.land == "OÖ":
                out.append(Matrixseite(q.land, ebene, rid, q.pdf, idx[-1] + 1))
    return out


def entwurf(quellen: tuple[Rsg2030Quelle, ...] | None = None) -> pd.DataFrame:
    """Fußnoten aller Textseiten, wie die Maschine sie findet (Bildseiten: leer – dort von Hand)."""
    bild = {(m.land, m.region_id) for m in manuelle_matrizen()}
    zeilen: list[dict] = []
    offen: dict[Path, pdfplumber.PDF] = {}
    try:
        for s in seiten(quellen):
            if (s.land, s.region_id) in bild:
                continue
            if s.pdf not in offen:
                offen[s.pdf] = pdfplumber.open(s.pdf)
            pdf = offen[s.pdf]
            page = pdf.pages[s.seite_idx]
            gefunden = fussnoten_ooe(page) if s.land == "OÖ" else fussnoten_seite(page)
            for zeichen, text in gefunden:
                zeilen.append(
                    dict(
                        Land=s.land,
                        Ebene=s.ebene,
                        Region_ID=s.region_id,
                        PDF=s.pdf.name,
                        Seite=s.seite_idx + 1,
                        Zeichen=zeichen,
                        Text=text,
                    )
                )
    finally:
        for p in offen.values():
            p.close()
    return pd.DataFrame(zeilen, columns=SPALTEN[:7])


# --- Verzeichnis ---------------------------------------------------------------------------------


def lade(path: Path | None = None) -> pd.DataFrame:
    path = path or pfad()
    if not path.is_file():
        return pd.DataFrame(columns=SPALTEN)
    return pd.read_csv(path, dtype=str, keep_default_na=False)[SPALTEN]


def pruefe_verzeichnis(df: pd.DataFrame, register: list[Matrixseite] | None = None) -> list[str]:
    """Ohne PDF: jede Fußnote eingeordnet, mit Verweis wo nötig; Vorlage nur, wo es eine ist; gleiche Fußnote eines
    Landes überall gleich eingeordnet. Mit `register` (`seiten()`): jeder Eintrag gehört zu einer Seite des
    Seitenregisters – sonst stammt er aus einer ersetzten Fassung und der PDF-Abgleich würde ihn übergehen."""
    befunde: list[str] = []
    da = None if register is None else {(s.land, s.region_id, s.pdf.name, s.seite_idx + 1) for s in register}
    for r in df.itertuples(index=False):
        wo = f"{r.Land} {r.Ebene} {r.Region_ID} S.{r.Seite} {r.Zeichen}"
        if da is not None and (r.Land, r.Region_ID, r.PDF, int(r.Seite)) not in da:
            befunde.append(f"{wo}: {r.PDF} S.{r.Seite} ist keine Seite dieser Matrix im Seitenregister – alte Fassung?")
        if r.Einordnung not in EINORDNUNGEN:
            befunde.append(f"{wo}: Einordnung «{r.Einordnung}» fehlt oder unbekannt ({', '.join(EINORDNUNGEN)})")
        elif r.Einordnung in MIT_VERWEIS and not r.Verweis.strip():
            befunde.append(f"{wo}: «{r.Einordnung}» braucht einen Verweis (Regel bzw. Doku-Stelle)")
        if ist_vorlage(r.Text) and r.Einordnung != "Vorlage":
            befunde.append(f"{wo}: wörtlich die ÖSG-Vorlage, eingeordnet als «{r.Einordnung}»")
    gruppen = df.assign(_t=df["Text"].map(lambda t: kompakt(norm(t)))).groupby(["Land", "_t"])
    for (land, _), g in gruppen:
        if g["Einordnung"].nunique() > 1:
            befunde.append(f"{land}: gleiche Fußnote verschieden eingeordnet: «{g['Text'].iloc[0][:60]}»")
    return befunde


def _woerter(text: str) -> set[str]:
    return {w for w in re.findall(r"[0-9A-Za-zÄÖÜäöüß]{3,}", norm(text).lower())}


def _zeichen_der_tabelle(text: str) -> set[str]:
    """Fußnotenzeichen im ambulanten Teil einer Seite («AM (3, 13)» → (3), (13)); der Bettenteil zählt nicht."""
    teil = re.split(r"\n\s*Akut-?Krankenanstalten", text)[0]
    return {f"({n})" for m in _ZEICHEN_IM_TEXT.finditer(teil) for n in re.split(r"\s*,\s*", m.group(1))}


def pruefe_gegen_pdf(df: pd.DataFrame, quellen: tuple[Rsg2030Quelle, ...] | None = None) -> list[str]:
    """Mit PDF (Textseiten): (1) jede Fußnote, die die Maschine auf einer Seite findet, steht im Verzeichnis; (2) jedes
    Fußnotenzeichen der Tabelle hat eine Fußnote; (3) jeder Text im Verzeichnis steht so auf seiner Seite (alle Wörter)."""
    befunde: list[str] = []
    bild = {(m.land, m.region_id) for m in manuelle_matrizen()}
    haben: dict[tuple[str, str], set[str]] = {}
    for r in df.itertuples(index=False):
        haben.setdefault((r.Land, r.Region_ID), set()).add(r.Zeichen)
    gefunden = entwurf(quellen)
    for r in gefunden.itertuples(index=False):
        if r.Zeichen not in haben.get((r.Land, r.Region_ID), set()):
            befunde.append(
                f"{r.Land} {r.Ebene} {r.Region_ID} S.{r.Seite} {r.Zeichen}: nicht im Verzeichnis – «{r.Text[:60]}»"
            )
    seitentext: dict[tuple[str, int], str] = {}
    offen: dict[Path, pdfplumber.PDF] = {}
    try:
        for s in seiten(quellen):
            if (s.land, s.region_id) in bild:
                continue
            if s.pdf not in offen:
                offen[s.pdf] = pdfplumber.open(s.pdf)
            seite = offen[s.pdf].pages[s.seite_idx].extract_text() or ""
            seitentext[(s.pdf.name, s.seite_idx + 1)] = seite
            if s.land != "OÖ":
                for z in sorted(_zeichen_der_tabelle(seite) - haben.get((s.land, s.region_id), set())):
                    befunde.append(f"{s.land} {s.ebene} {s.region_id} S.{s.seite_idx + 1}: Zeichen {z} ohne Fußnote")
    finally:
        for p in offen.values():
            p.close()
    for r in df.itertuples(index=False):
        text = seitentext.get((r.PDF, int(r.Seite)))
        if text is None:
            continue  # Bildseite; Seiten außerhalb des Registers meldet pruefe_verzeichnis
        fehlen = _woerter(r.Text) - _woerter(text)
        if fehlen:
            befunde.append(f"{r.Land} {r.Region_ID} S.{r.Seite} {r.Zeichen}: nicht auf der Seite: {sorted(fehlen)[:5]}")
    return befunde


def main(argv: list[str] | None = None) -> int:
    einrichten()
    argparse.ArgumentParser(
        prog="python -m rsg2030 fussnoten",
        description="neue Fußnoten der Matrixseiten als Entwurf ins Verzeichnis fussnoten.csv (Einordnung von Hand)",
    ).parse_args(argv)
    alt = lade()
    neu = entwurf()
    schon = set(zip(alt["Land"], alt["Region_ID"], alt["Zeichen"]))
    dazu = neu[[k not in schon for k in zip(neu["Land"], neu["Region_ID"], neu["Zeichen"])]].reindex(columns=SPALTEN)
    dazu = dazu.fillna("")
    dazu["Einordnung"] = ["Vorlage" if ist_vorlage(t) else "" for t in dazu["Text"]]
    if len(dazu):
        pd.concat([alt, dazu], ignore_index=True).to_csv(pfad(), index=False, lineterminator="\n")
    log.info(f"{pfad().name}: {len(alt)} Einträge, {len(dazu)} neu" + (" – Einordnung ergänzen" if len(dazu) else ""))
    if len(dazu):
        for r in dazu.itertuples(index=False):
            log.warning(f"  ✗ neu: {r.Land} {r.Region_ID} S.{r.Seite} {r.Zeichen} «{r.Text[:70]}»")
    befunde = pruefe_verzeichnis(lade(), seiten())
    for b in befunde:
        log.warning(f"  ✗ {b}")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
