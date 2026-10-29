"""ÖSG-Zitate: Jede Seitenangabe im Repo zeigt auf eine Seite, die den hinterlegten Anker wirklich enthält.

Belegt (docs/PRUEFUNG.md, «Wer prüft was», Regel 1): dass eine Seitenangabe stimmt – nicht, dass die Aussage, die
wir daraus ableiten, richtig ist. Das bleibt menschliches Urteil. Dass sich das Dokument nicht ändert, sichert die
Prüfsumme im Register (`rsg2030/quellen/quellen.csv`), nicht dieser Test.

Nützt zweierlei: Ein falscher Seitenverweis fällt auf, statt unbemerkt stehen zu bleiben. Und bei einem neuen
ÖSG-Stand (Namen in `oesg_methodik.pfade.OESG_BAENDE`) sagt der Test, welcher Anker auf welche Seite gewandert ist –
die Doku wird dann danach nachgezogen, nicht nach Gefühl.

Anker pflegen: `oesg_methodik/referenz/oesg_zitate.csv`, je Zeile Band, Seite, wörtlicher Anker und was er belegt.
Der Anker steht so da, wie pdfplumber die Seite liest, mit aufgelösten Trennstrichen am Zeilenende (siehe `norm`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pdfplumber
import pytest

from oesg_methodik.pfade import OESG_BAENDE, OESG_ZITATE_CSV, oesg_pdf

ROOT = Path(__file__).resolve().parents[1]
# Diese Datei nennt die Bände selbst und würde sich sonst selbst finden
AUSSEN = {Path(__file__).name}
ORDNER_AUS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "daten_original", "daten_ergebnis"}
ENDUNGEN = {".md", ".py", ".csv", ".cff", ".toml", ".html", ".js"}

# «Textband S.37», «Tabellenband, Anhang 9, S.259», «Textband S.36–37», «Textband S.66, S.75».
# Nicht über «;» oder «|»: Das sind Feldgrenzen in CSV und Markdown-Tabellen – sonst bindet ein Bandname
# die Seitenzahl der Nachbarspalte (oesg_planungsrichtwerte.csv: Quelle «ÖSG 2023 Textband», Anmerkung «S.252»).
ZITAT = re.compile(
    r"\b(Textband|Tabellenband|Methodenband)\b[^\n;|]{0,60}?"
    r"(S\.\s?\d{1,3}(?:\s*[–-]\s*\d{1,3})?(?:,\s*S\.\s?\d{1,3})*)"
)
SEITE = re.compile(r"S\.\s?(\d{1,3})")
BEREICH = re.compile(r"S\.\s?(\d{1,3})\s*[–-]\s*(\d{1,3})")
BEREICH_MAX = 4  # längere Angabe = ganzer Anhang («Anhang 5, S.15–60»), dann zählt nur die erste Seite


def norm(text: str) -> str:
    """Seitentext zu einer Zeile: Leerzeichen zusammengefasst, Trennstriche am Zeilenende aufgelöst. Ohne das
    scheitert jeder Vergleich an Umbrüchen wie «(Anga- be optional)» oder «Standardversorgungs- einheiten»."""
    return re.sub(r"-\s+", "", re.sub(r"\s+", " ", text)).strip()


def dateien() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix in ENDUNGEN
        and p.name not in AUSSEN
        and not ORDNER_AUS & set(p.relative_to(ROOT).parts)
    )


def fundstellen() -> dict[tuple[str, int], list[str]]:
    """Alle Seitenangaben im Repo: (Band, Seite) → Fundstellen «datei:zeile». Ein kurzer Bereich («S.12–13») zählt
    mit jeder Seite, ein langer («Anhang 5, S.15–60») nur mit der ersten: Dort beginnt, was zitiert wird."""
    gefunden: dict[tuple[str, int], list[str]] = {}
    for p in dateien():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for nr, zeile in enumerate(text.split("\n"), 1):
            for m in ZITAT.finditer(zeile):
                band, ausdruck = m.group(1), m.group(2)
                seiten = [int(s) for s in SEITE.findall(ausdruck)]  # «S.36, S.76» → beide
                if b := BEREICH.search(ausdruck):
                    von, bis = int(b.group(1)), int(b.group(2))
                    seiten += list(range(von, bis + 1)) if bis - von < BEREICH_MAX else [von]
                for s in dict.fromkeys(seiten):
                    gefunden.setdefault((band, s), []).append(f"{p.relative_to(ROOT)}:{nr}")
    return gefunden


def anker() -> pd.DataFrame:
    a = pd.read_csv(OESG_ZITATE_CSV, sep=";", dtype={"Seite": int})
    assert set(a["Band"]) <= set(OESG_BAENDE), f"unbekannter Band: {set(a['Band']) - set(OESG_BAENDE)}"
    assert not a.duplicated(["Band", "Seite", "Anker"]).any(), "doppelter Anker"
    return a


def test_jede_seitenangabe_hat_einen_anker():
    """Ohne Anker ist eine Seitenangabe ungeprüft – dann fehlt sie in oesg_zitate.csv."""
    haben = {(r.Band, r.Seite) for r in anker().itertuples()}
    fehlen = {k: v for k, v in fundstellen().items() if k not in haben}
    assert not fehlen, "Seitenangaben ohne Anker in oesg_zitate.csv:\n" + "\n".join(
        f"  {b} S.{s}: {', '.join(sorted(set(orte))[:4])}" for (b, s), orte in sorted(fehlen.items())
    )


def test_kein_anker_ohne_fundstelle():
    """Ein Anker zu einer Seite, die niemand zitiert, ist Pflegeaufwand ohne Nutzen."""
    zitiert = set(fundstellen())
    ueberzaehlig = sorted({(r.Band, r.Seite) for r in anker().itertuples()} - zitiert)
    assert not ueberzaehlig, f"Anker ohne Zitat im Repo: {ueberzaehlig}"


@pytest.mark.slow  # liest die ÖSG-Bände aus daten_original/
def test_anker_stehen_auf_der_zitierten_seite():
    """Der Kern: Jeder Anker steht auf der Seite, die wir angeben. Steht er woanders, nennt der Fehler die Seite –
    das ist die Arbeitsliste, wenn ein neuer ÖSG-Stand die Seiten verschiebt."""
    a = anker()
    befunde = []
    for band, gruppe in a.groupby("Band"):
        with pdfplumber.open(oesg_pdf(str(band))) as pdf:
            seiten = [norm(s.extract_text() or "") for s in pdf.pages]
        for r in gruppe.itertuples():
            if r.Seite <= len(seiten) and r.Anker in seiten[r.Seite - 1]:
                continue
            woanders = [i + 1 for i, t in enumerate(seiten) if r.Anker in t]
            wohin = f"steht auf S.{woanders}" if woanders else "nirgends gefunden"
            befunde.append(f"  {band} S.{r.Seite} ({r.Belegt}): {wohin}\n    Anker: {r.Anker[:100]}")
    assert not befunde, f"{len(befunde)} Anker nicht auf der zitierten Seite:\n" + "\n".join(befunde)


@pytest.mark.slow
def test_anker_sind_aussagekraeftig():
    """Ein Anker, der auf vielen Seiten steht, belegt keine Seitenangabe – dann muss er länger oder genauer werden."""
    grenze = 4
    befunde = []
    for band, gruppe in anker().groupby("Band"):
        with pdfplumber.open(oesg_pdf(str(band))) as pdf:
            seiten = [norm(s.extract_text() or "") for s in pdf.pages]
        for r in gruppe.itertuples():
            n = sum(1 for t in seiten if r.Anker in t)
            if n > grenze:
                befunde.append(f"  {band} S.{r.Seite}: auf {n} Seiten – {r.Anker[:80]}")
    assert not befunde, f"Anker auf mehr als {grenze} Seiten:\n" + "\n".join(befunde)
