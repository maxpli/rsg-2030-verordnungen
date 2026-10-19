"""Zweitlesung der Planungsmatrizen aus dem Seitenbild mit der Claude-API (Pflege, nicht Teil von «alles»).

Jede Matrixseite wird als Bild gerendert (längste Kante 2.576 Pixel, mehr nimmt das Modell nicht) und ohne die Werte der
ersten Lesung an das Modell geschickt; es schreibt die Tabelle zeichengenau ab. Das Ergebnis landet je Matrix als Datei
in `eingaben/<Stand>/zweitlesung/` (Format: `rsg2030/zweitlesung.py`), mit Herkunft im Dateikopf: Modell, Datum,
Prüfsumme des Bildes und Version der Anweisung (Token und Kosten nur in der Konsolenausgabe). Danach vergleicht `python -m rsg2030 daten`
Zelle für Zelle mit Lesung A; Abweichungen entscheidet ein Mensch am PDF (freigabe.xlsx).

    pip install -c requirements.txt -e ".[zweitlesung]"           # einmalig
    python -m rsg2030.scripts.zweitlesung_ki --matrizen burgenland_bl,kaernten_vr21,ooe_bl --ziel <Ordner>   # Pilot
    python -m rsg2030.scripts.zweitlesung_ki --alle --batch        # alle, über die Batch-API (halber Preis)
    python -m rsg2030.scripts.zweitlesung_ki --abholen <batch-id>  # Ergebnisse des Batches abholen

Gibt das Modell eine Zeile mit weniger Werten zurück, als die Kopfzeile Spalten hat, wäre unklar, welcher Wert in welche
Spalte gehört; solche Zeilen vergleicht `daten` nicht. Das Skript nennt dann die betroffenen Matrizen samt Befehl, sie
noch einmal lesen zu lassen. Eine neue Lesung ersetzt die vorhandene nur, wenn sie weniger unvollständige Zeilen hat –
sonst bleibt die alte. Was danach noch fehlt, entscheidet ein Mensch (Blatt «Zweitlesung» der Freigabe).

Zugang: `ANTHROPIC_API_KEY` oder ein Profil aus `ant auth login`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

import pypdfium2 as pdfium

from rsg2030.config import ausgabe_dir, quellen_dir
from rsg2030.protokoll import einrichten
from rsg2030.seitenregister import lade_seitenregister
from rsg2030.zweitlesung import dateiname, ordner

log = logging.getLogger(__name__)

MODELL = "claude-opus-5-5"
AUFWAND = "high"
LANGE_KANTE = 2576
PREIS_EIN, PREIS_AUS = 4.00, 20.00  # US-$ je Million Token (Opus 5.5); Batch-API: die Hälfte
OFFENE_BATCHES = "zweitlesung_batches.json"
"""Notiz zu eingereichten Batches – in daten_ergebnis/, nicht im Repo."""

SYSTEM = (
    "Du schreibst eine Tabelle aus einer österreichischen Verordnung (Regionaler Strukturplan Gesundheit, "
    "«RSG-Planungsmatrix») von einem Seitenbild ab. Deine Abschrift wird Zelle für Zelle mit einer zweiten, unabhängigen "
    "Lesung verglichen, und jede Abweichung prüft ein Mensch am Original. Es kommt nur auf genaues Abschreiben an – "
    "nicht auf Deutung, nicht auf Plausibilität, nicht auf Rechnen. Schreib jede Zelle so ab, wie sie gedruckt ist, auch "
    "wenn sie dir falsch vorkommt."
)

ANWEISUNG = """Schreib den Teil «Ambulante ärztliche Versorgung» der Planungsmatrix ab: alle Tabellenzeilen von der ersten \
Kopfzeile mit Fachkürzeln bis zum Ende dieser Matrix. {folgeseiten}Nicht abschreiben: Fußnoten unter der Tabelle, \
Legenden, Abschnitte zu Krankenanstalten und Betten («Akut-Krankenanstalten …») und alles danach.

Ausgabe: ein einziger Codeblock ```tsv … ``` mit Tabulator als Trennzeichen, danach nichts mehr.

- Überschrift einer Gruppe (z. B. «IST ÄAVE 2022», «IST vertragsärztliche Planstellen 2022», «PLAN ÄAVE 2030», «PLAN \
Sachleistungsstellen 2030», «sofern Planungsgröße nicht ÄAVE gemäß ÖSG:», «Umrechnungsfaktoren … PLAN 2030»):
  #Abschnitt<TAB>Text wie gedruckt
- Kopfzeile mit Fachkürzeln, genau wie gedruckt, mit Fußnotenzeichen wie (4) oder *, von links nach rechts, die letzte \
Spalte heißt meist «gesamt». Steht eine Kopfzeile mehrmals auf der Seite, gib sie jedes Mal an ihrer Stelle aus:
  #Kopf<TAB>Kopf1<TAB>Kopf2<TAB>…<TAB>gesamt
- Jede Tabellenzeile, mit genau so vielen Werten wie die letzte #Kopf-Zeile Köpfe hat:
  Zeilenbeschriftung<TAB>Wert unter Kopf1<TAB>Wert unter Kopf2<TAB>…

Werte zeichengenau wie gedruckt: Komma als Dezimalzeichen, Tausenderpunkte, «%» wenn gedruckt, «-», «n.v.», «x», «0». \
Ein Fußnotenzeichen an einem Wert in Klammern anhängen, z. B. «2,1(7)». Leere oder schraffierte Zelle: nichts zwischen \
den Tabulatoren. Zeilenbeschriftung wie gedruckt, in einer Zeile, auch wenn sie im Bild umbricht; eine Zeile ohne \
Beschriftung als «(ohne Beschriftung)». Nichts weglassen, nichts zusammenfassen, nichts ergänzen oder ausrechnen. \
Ist eine Zelle unleserlich, schreib «?»."""

ANWEISUNG_VERSION = hashlib.sha256((SYSTEM + ANWEISUNG).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Matrix:
    land: str
    ebene: str
    region_id: str
    pdf: Path
    seiten: tuple[int, ...]
    """0-basiert; Hauptseite und Folgeseiten."""

    @property
    def name(self) -> str:
        return dateiname(self.land, self.ebene, self.region_id)


def matrizen() -> list[Matrix]:
    out: list[Matrix] = []
    for q in lade_seitenregister():
        out.append(Matrix(q.land, "BL", q.land, q.pdf, (q.seite_idx,)))
        for vr in q.vr:
            out.append(Matrix(q.land, "VR", vr.region_id, q.pdf, (vr.seite_idx, *vr.folgeseiten_idx)))
    return out


def bild(pdf: Path, seite: int) -> tuple[bytes, str]:
    """Seite als PNG, längste Kante LANGE_KANTE Pixel; dazu (Breite x Höhe)."""
    doc = pdfium.PdfDocument(str(pdf))
    page = doc[seite]
    breite, hoehe = page.get_size()
    img = page.render(scale=LANGE_KANTE / max(breite, hoehe)).to_pil()
    puffer = io.BytesIO()
    img.save(puffer, format="PNG", optimize=True)
    return puffer.getvalue(), f"{img.width}x{img.height}"


def anfrage(m: Matrix) -> tuple[dict[str, Any], list[str]]:
    """Parameter der Anfrage und Herkunftszeilen der Bilder."""
    inhalt: list[dict] = []
    herkunft: list[str] = []
    for seite in m.seiten:
        png, groesse = bild(m.pdf, seite)
        inhalt.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(png).decode()},
            }
        )
        herkunft.append(
            f"{m.pdf.name} S.{seite + 1} · Bild {groesse} px, SHA-256 {hashlib.sha256(png).hexdigest()[:16]}"
        )
    folge = (
        "Die Matrix geht auf der zweiten Seite weiter; lies beide Seiten als eine Matrix. " if len(m.seiten) > 1 else ""
    )
    inhalt.append({"type": "text", "text": ANWEISUNG.format(folgeseiten=folge)})
    params: dict[str, Any] = {
        "model": MODELL,
        "max_tokens": 64000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": AUFWAND},
        "system": SYSTEM,
        "messages": [{"role": "user", "content": inhalt}],
    }
    return params, herkunft


def tsv_aus(text: str) -> str | None:
    t = re.search(r"```tsv\n(.*?)```", text, re.S)
    return t.group(1).strip("\n") if t else None


def pruefe_form(tsv: str) -> list[str]:
    """Zeilen, deren Wertezahl nicht zur letzten Kopfzeile passt."""
    hinweise, n = [], None
    for z in tsv.splitlines():
        if z.startswith("#Kopf"):
            n = len(z.split("\t")) - 1
        elif z and not z.startswith("#") and n is not None and len(z.split("\t")) - 1 != n:
            hinweise.append(f"{len(z.split(chr(9))) - 1} statt {n} Werte: {z.split(chr(9))[0][:50]}")
    return hinweise


def _vorhanden_unvollstaendig(datei: Path) -> int | None:
    """Unvollständige Zeilen der vorhandenen Lesung (None: keine vorhanden)."""
    return len(pruefe_form(datei.read_text(encoding="utf-8"))) if datei.is_file() else None


def schreibe(
    m: Matrix,
    tsv: str,
    herkunft: list[str],
    modell: str,
    ziel: Path,
) -> bool:
    """Lesung als Datei ablegen – eine vorhandene nur ersetzen, wenn die neue weniger unvollständige Zeilen hat."""
    alt = _vorhanden_unvollstaendig(ziel / m.name)
    if alt is not None and len(pruefe_form(tsv)) >= alt:
        log.info(
            f"  {m.name}: neue Lesung nicht vollständiger ({len(pruefe_form(tsv))} gegen {alt} Zeilen) – alte bleibt"
        )
        return False
    kopf = [
        f"# Zweitlesung RSG 2030 – {m.land} {'BL' if m.ebene == 'BL' else 'VR ' + m.region_id}",
        "# Verfahren: KI-Lesung des Seitenbilds, ohne Kenntnis der Werte der ersten Lesung (rsg2030/scripts/zweitlesung_ki.py)",
        f"# Modell: {modell} · Aufwand: {AUFWAND} · Anweisung: Version {ANWEISUNG_VERSION} · Datum: {date.today().isoformat()}",
        *[f"# Quelle: {h}" for h in herkunft],
        *[f"# Hinweis: {h}" for h in pruefe_form(tsv)],
    ]
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / m.name).write_text("\n".join(kopf) + "\n" + tsv + "\n", encoding="utf-8")
    return True


def melde_unvollstaendige(auswahl: list[Matrix], ziel: Path) -> None:
    """Matrizen mit unvollständigen Zeilen nennen, samt Befehl für eine neue Lesung."""
    offen = [m.name.removesuffix(".tsv") for m in auswahl if _vorhanden_unvollstaendig(ziel / m.name)]
    if offen:
        log.warning(
            f"  ✗ {len(offen)} Matrizen mit unvollständigen Zeilen – noch einmal lesen (ersetzt nur, wenn vollständiger):"
            f"\n    python -m rsg2030.scripts.zweitlesung_ki --matrizen {','.join(offen)} --batch --ueberschreiben"
        )


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if b.type == "text")


def sofort(auswahl: list[Matrix], ziel: Path, max_dollar: float) -> float:
    import anthropic

    client = anthropic.Anthropic()
    summe = 0.0
    for m in auswahl:
        if summe >= max_dollar:
            log.warning(f"  ✗ Kostengrenze {max_dollar:.2f} $ erreicht – Rest nicht gelesen")
            break
        params, herkunft = anfrage(m)
        # Lehnt das Modell ab (sehr unwahrscheinlich bei einer Tabelle), springt serverseitig ein anderes ein; welches
        # Modell gelesen hat, steht dann im Dateikopf.
        with client.beta.messages.stream(**params, betas=["server-side-fallback-2026-07-01"], fallbacks="default") as s:
            msg = s.get_final_message()
        kosten = (msg.usage.input_tokens * PREIS_EIN + msg.usage.output_tokens * PREIS_AUS) / 1e6
        summe += kosten
        tsv = tsv_aus(_text(msg)) if msg.stop_reason != "refusal" else None
        if tsv is None:
            log.warning(f"  ✗ {m.name}: keine Tabelle in der Antwort (stop_reason {msg.stop_reason})")
            continue
        if not schreibe(m, tsv, herkunft, msg.model, ziel):
            continue
        log.info(
            f"  {m.name}: {len(tsv.splitlines())} Zeilen · {msg.usage.output_tokens} Ausgabe-Token · {kosten:.2f} $ (Summe {summe:.2f} $)"
        )
    melde_unvollstaendige(auswahl, ziel)
    return summe


def batch(auswahl: list[Matrix], ziel: Path) -> None:
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = anthropic.Anthropic()
    anfragen, herkunft = [], {}
    for m in auswahl:
        params, herkunft[m.name] = anfrage(m)
        anfragen.append(
            Request(custom_id=m.name.removesuffix(".tsv"), params=cast(MessageCreateParamsNonStreaming, params))
        )
    b = client.messages.batches.create(requests=anfragen)
    merk = ausgabe_dir() / OFFENE_BATCHES
    offen = json.loads(merk.read_text()) if merk.is_file() else {}
    offen[b.id] = {"ziel": str(ziel), "herkunft": herkunft, "datum": date.today().isoformat()}
    merk.parent.mkdir(parents=True, exist_ok=True)
    merk.write_text(json.dumps(offen, ensure_ascii=False, indent=2))
    log.info(f"Batch {b.id}: {len(anfragen)} Matrizen eingereicht · abholen: --abholen {b.id}")


def abholen(batch_id: str, ziel: Path) -> None:
    import anthropic

    client = anthropic.Anthropic()
    b = client.messages.batches.retrieve(batch_id)
    if b.processing_status != "ended":
        log.info(f"Batch {batch_id}: {b.processing_status} – noch nicht fertig")
        return
    merk = ausgabe_dir() / OFFENE_BATCHES
    info = json.loads(merk.read_text())[batch_id]
    namen = {m.name.removesuffix(".tsv"): m for m in matrizen()}
    summe = 0.0
    for r in client.messages.batches.results(batch_id):
        m = namen[r.custom_id]
        if r.result.type != "succeeded":
            log.warning(f"  ✗ {m.name}: {r.result.type}")
            continue
        msg = r.result.message
        kosten = (msg.usage.input_tokens * PREIS_EIN + msg.usage.output_tokens * PREIS_AUS) / 2e6  # Batch: halber Preis
        summe += kosten
        tsv = tsv_aus(_text(msg)) if msg.stop_reason != "refusal" else None
        if tsv is None:
            log.warning(f"  ✗ {m.name}: keine Tabelle in der Antwort (stop_reason {msg.stop_reason})")
            continue
        schreibe(m, tsv, info["herkunft"][m.name], msg.model, ziel)
    log.info(f"Batch {batch_id}: abgeholt, Kosten ca. {summe:.2f} $")
    melde_unvollstaendige([m for m in matrizen() if m.name in info["herkunft"]], ziel)


def main(argv: list[str] | None = None) -> int:
    einrichten()
    a = argparse.ArgumentParser(
        prog="python -m rsg2030.scripts.zweitlesung_ki", description="Zweitlesung der Seitenbilder"
    )
    a.add_argument("--matrizen", help="Dateinamen ohne .tsv, mit Komma getrennt, z. B. burgenland_bl,kaernten_vr21")
    a.add_argument("--alle", action="store_true", help="alle Matrizen laut seiten.csv")
    a.add_argument("--ueberschreiben", action="store_true", help="auch Matrizen, die schon eine Zweitlesung haben")
    a.add_argument("--ziel", type=Path, help="Ordner für die Ergebnisse (Standard: eingaben/<Stand>/zweitlesung)")
    a.add_argument("--batch", action="store_true", help="über die Batch-API einreichen (halber Preis, Ergebnis später)")
    a.add_argument("--abholen", metavar="BATCH_ID", help="Ergebnisse eines eingereichten Batches abholen")
    a.add_argument("--max-dollar", type=float, default=50.0, help="Kostengrenze für sofortige Anfragen (Standard 50)")
    args = a.parse_args(argv)
    ziel = args.ziel or ordner()
    if not quellen_dir().is_dir():
        log.error("❌ Quellen fehlen → python -m rsg2030 download")
        return 1
    if args.abholen:
        abholen(args.abholen, ziel)
        return 0
    alle = matrizen()
    if args.alle:
        auswahl = alle
    elif args.matrizen:
        gewuenscht = {n.strip().removesuffix(".tsv") for n in args.matrizen.split(",")}
        auswahl = [m for m in alle if m.name.removesuffix(".tsv") in gewuenscht]
        unbekannt = gewuenscht - {m.name.removesuffix(".tsv") for m in auswahl}
        if unbekannt:
            log.error(f"❌ unbekannte Matrizen: {sorted(unbekannt)} (bekannt: {', '.join(m.name for m in alle)})")
            return 1
    else:
        a.print_help()
        return 1
    if not args.ueberschreiben:
        auswahl = [m for m in auswahl if not (ziel / m.name).is_file()]
    log.info(f"{len(auswahl)} Matrizen · Modell {MODELL} · Anweisung {ANWEISUNG_VERSION} · Ziel {ziel}")
    if args.batch:
        batch(auswahl, ziel)
    else:
        sofort(auswahl, ziel, args.max_dollar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
