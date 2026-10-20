# CLAUDE.md

Öffentliches Daten-Repository: die Planungsmatrizen der RSG 2030 (Regionale Strukturpläne Gesundheit; ambulante
ärztliche Kapazität in ÄAVE je Bundesland (BL) und Versorgungsregion (VR)), aus den Verordnungs-PDFs ausgelesen,
geprüft und zu Versorgungsdichte (VD) und Lage zum Versorgungsdichte-Soll-Intervall (ÖSG), VDmin–VDmax, verarbeitet.
Code, Kommentare, Doku, Konsolenausgaben und Daten sind **deutsch**; das bleibt so, ebenso die Fachbegriffe (ÄAVE, VD,
SVE, SLST, PVE, VGF, Soll-Intervall …). Die Doku lesen Fachleute, keine Programmierer:innen: einfach schreiben.

Die Daten liegen **nicht** in git. Bei einem Versions-Tag erzeugt GitHub Actions sie frisch und hängt sie an das
Release (`.github/workflows/release.yml`); Nutzer:innen können sie auch selbst erzeugen (`python -m rsg2030 alles`).
Jeder Lauf endet mit einem Vergleich Byte für Byte gegen die veröffentlichten Prüfsummen
(`rsg2030/erwartete_ausgaben.csv`).

Doku (maßgeblich für die Methodik – vor jeder Änderung am Verhalten lesen):
- [docs/METHODIK.md](docs/METHODIK.md): ÖSG-Regeln R1–R9 mit Dokument und Seite, Entscheidungen (nur Sachleistung, keine Österreich-Ebene)
- [docs/DATEN.md](docs/DATEN.md): jede Spalte beider Tabellen, Zellbedeutung, Fallstricke
- [docs/PRUEFUNG.md](docs/PRUEFUNG.md): Prüfkonzept (5 Ebenen), was jede belegt und was nicht
- [docs/PIPELINE.md](docs/PIPELINE.md): Betrieb: Schritte des Laufs, Eingaben, Syntax der Korrekturregeln, neue Verordnung aufnehmen
- [docs/offene_punkte.md](docs/offene_punkte.md): offene Entscheidungen und Aufgaben
- [docs/WEB.md](docs/WEB.md): Webseite zum Nachsehen: was sie zeigt, Darstellungsregeln, Entscheidungen, wer was prüft

## Regeln für die Doku

- Keine ÖSG-Regel ohne Quelle. Zuerst in docs/METHODIK.md nachsehen; fehlt sie, in den ÖSG-PDFs
  (`daten_original/oesg/`) nachschlagen und mit Dokument und Seite ergänzen, im selben Commit wie die Code-Änderung.
- Eine neue oder geänderte Spalte/Zeile wird in docs/DATEN.md beschrieben.
- Keine Zahlen eines Laufs (Zellen, Prüfungen, Regeln) fest in die Doku schreiben: Sie stehen in
  `daten_ergebnis/Pruefbericht.md`; das CHANGELOG hält sie je Version fest.
- Eine Datenänderung (Prüfsumme in `rsg2030/erwartete_ausgaben.csv`) bekommt einen Eintrag in CHANGELOG.md mit Grund
  und eine neue Version (`pyproject.toml`, `CITATION.cff`).
- Keine Verweise auf andere Projekte oder auf Analysen; dieses Repo ist nur der Datensatz. Ansichten des Datensatzes
  (Excel-Mappe, Webseite) gehören dazu: Sie zeigen nur, was in den veröffentlichten Dateien steht, und übernehmen die
  Vorbehalte aus docs/DATEN.md. Analysen und Daten von außerhalb gehören nicht hierher.
- Jede Zahl, die wir für eine Aussage oder Entscheidung der Doku gerechnet oder ausgezählt haben, ist nachrechenbar:
  aus den Ausgaben, einem Test oder einem Skript unter `rsg2030/scripts/` – nie nur aus einer einmaligen Rechnung
  außerhalb des Repos. Abgelesene Werte stehen mit Dokument und Seite da.
- Vorbehalte und offene Fragen folgen den Daten: Ändert sich eine Prüfung, Korrektur, bekannte Abweichung oder die
  Lesart einer Fußnote, im selben Commit nachziehen, worauf Nutzer:innen achten müssen (docs/DATEN.md «Fallstricke»,
  docs/METHODIK.md «Bekannte Grenzen»), und die Fragen je Land (docs/offene_punkte.md, «Unklare Angaben in den
  Verordnungen»). Die Doku klingt nie sicherer als die Belege: Eine unbestätigte Lesart steht als solche da.

## Umgebung und Befehle

Python 3.13 in `.venv/`, editierbar installiert; `requirements.txt` ist die vollständige Sperrdatei. Eine aktivierte
Shell bleibt zwischen deinen Befehlen nicht erhalten, also `.venv/bin/python` usw. direkt aufrufen. Datenordner sind
relativ zum Arbeitsordner (oder `RSG2030_DATEN`): aus dem Stammordner des Repos aufrufen.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -c requirements.txt -e ".[dev]"   # einmalig

.venv/bin/python -m rsg2030 alles        # download → daten → versorgungsdichte
.venv/bin/python -m rsg2030 download     # Quellen, SHA-256-Prüfung (--neu = neu laden)
.venv/bin/python -m rsg2030 seiten       # Seitenregister seiten.csv neu erzeugen
.venv/bin/python -m rsg2030 manuell      # Blätter für Bildseiten in manuell.xlsx anlegen
.venv/bin/python -m rsg2030 fussnoten    # neue Fußnoten der Matrixseiten als Entwurf in fussnoten.csv
.venv/bin/python -m rsg2030 freigabe     # freigabe.xlsx (Freigabe durch einen Menschen) nachziehen, Häkchen bleiben
.venv/bin/python -m rsg2030 daten        # auslesen, korrigieren, prüfen → FREIGEGEBEN / NICHT FREIGEGEBEN, ✓/✗ gegen veröffentlicht
.venv/bin/python -m rsg2030 versorgungsdichte  # ÄAVE im ÖSG-Zuschnitt, VD, Lage zum Soll-Intervall, ✓/✗ gegen veröffentlicht
.venv/bin/python -m rsg2030 waechter     # neue Verordnungen im RIS? --quellen: Originale ersetzt? --archiv: Archivkopien richtig? nur Hinweise

.venv/bin/python -m pytest -m "not slow"  # ~5 s, ohne Quelldateien
.venv/bin/python -m pytest                # ~2,5 min, braucht daten_original/
.venv/bin/ruff check --fix . && .venv/bin/ruff format . && .venv/bin/mypy
```

Bevor eine Änderung fertig ist: ruff, mypy und die schnellen Tests laufen durch; nach jeder Änderung an Auslesen,
Korrekturen, Schema, Bevölkerung oder VD-Code auch die ganze Suite. Vorsicht mit `ruff --fix` F401: Es entfernt
ungenutzte Importe, auch Re-Exporte; Namen von dort importieren, wo sie definiert sind.

## Aufbau

```
oesg_methodik/        ÖSG-Regeln, unabhängig von einem Datensatz (importiert nichts aus rsg2030 – tests/test_pakete.py)
  pfade.py              Datenordner als Funktionen (Arbeitsordner / RSG2030_DATEN) und Referenzdateien des Pakets
  eingang.py            Vertrag der ÄAVE-Eingabe (Basis Sachleistung, Ebene BL/VR) + pruefe()
  faecher.py            ZUSCHNITT: Matrixspalten → Richtwertzeilen des ÖSG (AM+ZAE, CH+KJC+PCH, IM+PUL, ZMK+KFO), aave_fach
  richtwerte.py         ÖSG-Richtwerte (referenz/oesg_planungsrichtwerte.csv, Textband S.37)
  bevoelkerung.py       Bevölkerung von Statistik Austria / ÖROK (Stichtag 1.1.), bevoelkerung_fuer()
  dichte.py             kennzahlen(): ÄAVE-Eingabe + Bevölkerung + Richtwerte → VD; Lage, Position, ÄAVE-Abstand
  referenz/             oesg_planungsrichtwerte.csv, oesg_regionen.csv (32 VR / 116 Bezirke)
rsg2030/              der Datensatz; __main__.py ruft die main() der Module auf
  quellen/              Register quellen.csv (RIS / URL, SHA-256, Verwendet) + Download
  pipeline.py           «daten»: Quellen → Auslesen → Zweitlesung → Fußnoten → Befunde → Korrektur → Prüfen → Freigabe → Ausgabe
  schema.py             Vertrag der Long-CSV (Spalten, Schlüssel, erlaubte Werte, Block-Regel bl_long/matrix_long)
  matrix_extract.py     Auslesen über Koordinaten mit pdfplumber, ZEILEN_DEFS; specs.py ordnet PDF-Köpfe den Fachspalten zu
  korrekturen.py, checks.py, ableitungen.py, manuell.py, quellenpruefung.py, seitenregister.py
  freigabe.py           Freigabe-Mappe: nur, was keine Maschine unabhängig prüfen kann (PRUEFUNG.md, «Wer prüft was»)
  zweitlesung.py        zweite, unabhängige Lesung (KI aus dem Seitenbild, scripts/zweitlesung_ki.py) gegen die Daten, Zelle für Zelle
  pruefbericht.py       daten_ergebnis/Pruefbericht.md: alle Zahlen eines Laufs (die Doku schreibt keine Zahlen fest)
  fussnoten.py          Fußnotenverzeichnis fussnoten.csv: Entwurf aus den PDFs, Prüfungen (vollständig, wie gedruckt, eingeordnet)
  scripts/              von Hand aufgerufen, nicht Teil von «alles»: zweitlesung_ki, monitoring_abgleich, abdeckung, seiten, …
  analyse_eingang.py    öffentliche Schnittstelle zur Long-CSV; aave_eingang() = ÄAVE-Eingabe für oesg_methodik
  versorgungsdichte.py  Long-CSV → oesg_methodik → RSG_2030_Versorgungsdichte.csv
  abgleich.py           Ausgaben gegen erwartete_ausgaben.csv (✓/✗ am Ende eines Laufs)
  protokoll.py          Logging, Laufprotokoll_<schritt>.json
  eingaben/2026/        von Hand gepflegte Eingaben: seiten, korrekturen, bekannte_abweichungen, manuell.xlsx, fussnoten.csv, zweitlesung/, freigabe.xlsx
tests/                pytest; Fixture `pipeline` = baue_pipeline() einmal je Testlauf
```

## Regeln, die leicht brechen

- **Jede Abweichung vom PDF ist eine Regel in `korrekturen.csv`**, die einen Befund der Prüfungen auf den Rohdaten
  auflöst. Nie Werte im Code flicken. Was bewusst bleibt, kommt mit Grund in `bekannte_abweichungen.csv`. Der Rohtext
  bleibt in `Roh`; `Quelle`/`Regel` halten die Herkunft fest.
- **Zellbedeutung:** «-» = 0 in ÄAVE-, Stellen- und Anzahl-Zeilen, leer in Prozent- und Faktor-Zeilen – außer «-» in
  einer %-Zeile unter Stellen > 0 (Fachspalte, nicht «gesamt») = 0 % (`prozent_strich_null`); «n.v.», «x», leere und
  schraffierte Zellen = leer. Eine optionale Zeile (Wahlärzt:innen) ohne eine einzige Zahl > 0 ist «nicht
  ausgefüllt» → leer (Regel `nicht_ausgewiesen`). Toleranz der Prüfungen = Rundung des Rohwerts (`Rundung`).
- **Block-Regel:** Für Länder, die in SVE planen (Burgenland, Kärnten, Steiermark), kommen vergleichbare ÄAVE aus dem
  Block `aequivalent`. `schema.bl_long` / `matrix_long` verwenden; nie eine Liste von Ländern fest einbauen.
- **Basis der VD:** nur Sachleistung, keine Basis inkl. Wahlärzt:innen und keine Österreich-Ebene in den Kennzahlen
  (Entscheidungen in docs/METHODIK.md, R1 und «Österreich»). Die Tabelle Versorgungsdichte hat nur ÄAVE-Zeilen, die es
  in IST und PLAN gibt (spitalsambulant, extramural, insgesamt, pve; R10), Soll-Intervall nur bei `insgesamt`; keine
  Stellen, VGF, Wahlärzt:innen oder IST-Teilzeilen (METHODIK, «Stellen»). Nicht ohne Rückfrage ergänzen.
- **Bevölkerung** nur nach der Methode des ÖSG (IST = Bezirke am 1.1. des IST-Jahrs des Landes; PLAN BL = Prognose
  2025 zum 1.1.2030; PLAN VR = ÖROK-Anteil 2021 × BL). Keine anderen Varianten im Code.
- **Andere Projekte lesen die veröffentlichten Dateien.** Was in `RSG_2030_Versorgungsdichte.csv` oder
  `RSG_2030_Planungsmatrizen.csv` steht, wird dort gelesen, nicht mit Funktionen dieses Pakets nachgerechnet: Nur die
  Dateien haben Version und Prüfsumme, eine geänderte Funktion wirkt sonst still mit. Importieren dürfen andere
  Projekte Lese-Hilfen (`analyse_eingang.lade_matrix_long`, `schema.bl_long`/`matrix_long`, Dateinamen aus `config`,
  `abgleich`, `protokoll`) und ÖSG-Regeln ohne Datenbezug aus `oesg_methodik`. Muss ein Projekt etwas nach
  ÖSG-Methode selbst rechnen, fehlt es in den Dateien.
- **Pfade werden beim Aufruf bestimmt:** Datenordner und Eingabedateien sind Funktionen (`pfade.original_dir()`,
  `config.ausgabe_dir()`, `config.seiten_csv()` …), nie Konstanten auf Modulebene oder Standardargumente – das Paket
  wird in andere Projekte importiert, die `RSG2030_DATEN` erst später setzen.
- **`daten` schreibt nie in `rsg2030/eingaben/`.** Eingaben ändert nur ein eigener Befehl (`seiten`, `manuell`,
  `freigabe`); ein normaler Lauf schreibt nur nach `daten_ergebnis/`.
- **Feste Paketversionen:** pdfplumber/pdfminer beeinflussen, wie Text zerlegt wird. Nur bewusst ändern, dann alles neu
  laufen lassen; die Long-CSV darf sich nicht ändern.
- **Deterministische Ausgabe.** Eine geänderte Prüfsumme ist eine Datenänderung: erklären, dann
  `erwartete_ausgaben.csv`, CHANGELOG.md und die Version nachziehen.
- **Quellen:** Was in die Ausgaben eingeht, muss frei nutzbar sein (freie amtliche Werke, Open Data unter CC BY 4.0)
  oder wird als einzelne Angabe mit Quellenangabe übernommen (ÖSG-Richtwerte, Regionen); Dateien ohne bekannte Lizenz
  werden nur verlinkt, nie weitergegeben (Lizenz «keine Freigabe bekannt – nur verlinkt, nicht weitergegeben»).
  Open-Data-Fassungen (data.statistik.gv.at) vor Dateien aus Publikationen. Lizenz der Daten: CC BY 4.0
  (LIZENZ_DATEN.md).
- **Namen unter `daten_original/`:** Ordner nur Kleinbuchstaben (ASCII), Ziffern, `_`, `-`; Dateien behalten den Namen
  der Quelle, aber nur ASCII-Buchstaben, Ziffern, `_`, `-`, `.` (keine Leerzeichen, keine Umlaute).
- **Nur zwei Pakete** auf oberster Ebene (`oesg_methodik`, `rsg2030`); keine allgemeinen Module dort – das Paket wird
  in andere Projekte installiert.

## Arbeitsweise

- **Erst planen, dann programmieren.** Bei allem, was über eine kleine Korrektur hinausgeht, zuerst aufschreiben,
  welche Fehler auftreten können und wer jeden findet (Vorbild: Tabelle «Wer prüft was» in docs/PRUEFUNG.md), mit dem
  Herausgeber abstimmen, dann umsetzen.
- **Zuerst die ÖSG-Vorlage.** Die Vorlage der RSG-Planungsmatrix (Tabellenband Anhang 9, S.259) legt Zeilen, Spalten
  und Fußnoten fest; Referenzen in `oesg_methodik/referenz/`, Vergleich in `rsg2030/vorlage.py`. Jede Abweichung eines
  Landes davon festhalten.
- **Handrechnungen als Tests**, bevor auf neuen Zahlen aufgebaut wird (VD je Land, tests/test_versorgungsdichte.py).
- **Prüfung durch einen Menschen zuletzt.** Häkchen in `freigabe.xlsx` verfallen, wenn sich der bestätigte Inhalt
  ändert; um Freigabe erst bitten, wenn die maschinelle Seite stabil ist. Was eine Maschine gegen die Quelle prüfen
  kann, ist ein Test, kein Häkchen.
- **Eine KI ändert nie von Hand gepflegte Eingaben** (`manuell.xlsx`, `freigabe.xlsx`, Einträge von Menschen in jeder
  Datei unter `eingaben/`). Weicht eine KI-Lesung von einer Abschrift ab, ist das ein Befund für den Menschen (Blatt
  «Zweitlesung»), keine Korrektur: Einmal angeglichen, sind die beiden Lesungen nicht mehr unabhängig (PRUEFUNG.md,
  Ebene 2).
- **Namen vor Versionen.** Zeile_IDs, Fachspalten und die öffentliche Schnittstelle (`analyse_eingang`, `schema`)
  stehen fest, bevor eine Version getaggt wird; bis dahin bleibt der CHANGELOG-Eintrag «in Arbeit». Eine Umbenennung
  nach einem Tag erzwingt Änderungen in jedem Projekt, das das Paket nutzt.

## Stil

`from __future__ import annotations`, Typangaben, kurze deutsche Docstrings und Kommentare, die das *Warum* erklären,
Konstanten in GROSSBUCHSTABEN; jedes ausführbare Modul hat `main(argv=None) -> int` (0 = ok, 1 = Fehler) und ruft
`protokoll.einrichten()` auf. Konsolenausgabe über `logging` (`log = logging.getLogger(__name__)`), nicht print;
✗-Zeilen sind `log.warning`, ❌-Zeilen `log.error`. Formatierung: ruff, Zeilenlänge 120.

## Git

Auf einem Feature-Branch arbeiten. Committen, mergen (`git merge --ff-only`) und pushen **nur auf ausdrücklichen
Wunsch**. Releases: Tag `<version>` (z. B. `2026.1`) auf main, nachdem die ganze Suite und ein frischer `alles`-Lauf
grün sind.
