# RSG 2030 – Planungsmatrizen der Verordnungen

[![Tests](https://github.com/maxpli/rsg-2030-verordnungen/actions/workflows/tests.yml/badge.svg)](https://github.com/maxpli/rsg-2030-verordnungen/actions/workflows/tests.yml)
[![Webseite](https://github.com/maxpli/rsg-2030-verordnungen/actions/workflows/webseite.yml/badge.svg)](https://maxpli.github.io/rsg-2030-verordnungen/)
[![Daten: CC BY 4.0](https://img.shields.io/badge/Daten-CC%20BY%204.0-lightgrey.svg)](LIZENZ_DATEN.md)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](.python-version)

Die **Regionalen Strukturpläne Gesundheit (RSG) 2030** der neun Bundesländer legen fest, wie viel ambulante
ärztliche Versorgung es 2030 geben soll. Jeder RSG enthält «Planungsmatrizen»: eine für das Bundesland und je eine
für jede Versorgungsregion, mit dem Stand (IST) und dem Plan 2030, je Fach.

Dieses Repository macht daraus einen **geprüften, nachvollziehbaren Datensatz**:

- Es lädt die Verordnungen aus dem Rechtsinformationssystem (RIS) und die Bevölkerungsdaten von Statistik Austria,
  und prüft jede Datei per Prüfsumme.
- Es liest alle 41 Planungsmatrizen aus (9 Bundesländer, 32 Versorgungsregionen), prüft sie und dokumentiert jede
  Korrektur mit Begründung.
- Es berechnet je Region und Fach die **Versorgungsdichte** (ÄAVE je 100.000 Einwohner:innen) und vergleicht sie
  mit dem **Versorgungsdichte-Soll-Intervall des Österreichischen Strukturplans Gesundheit (ÖSG)**: darunter, darin
  oder darüber, wo genau und wie viele ÄAVE bis zur Grenze.

**Die fertigen Dateien gibt es bei jedem [Release](../../releases)** zum Herunterladen. GitHub Actions erzeugt sie dort
aus dem öffentlichen Code und den öffentlichen Quellen; Lauf und Protokoll sind einsehbar. Wer will, erzeugt sie
auch selbst ([Selbst erzeugen](#selbst-erzeugen)) und sieht am Ende, ob das Ergebnis Byte für Byte der
veröffentlichten Version entspricht.

**Zum Nachsehen im Browser:** [Webseite zur Tabelle Versorgungsdichte](https://maxpli.github.io/rsg-2030-verordnungen/)
– je Versorgungsregion und Fach, ob die Sachleistung unter, im oder über dem Soll-Intervall liegt, mit den Daten des
aktuellen Release ([docs/WEB.md](docs/WEB.md)).

[Was herauskommt](#was-herauskommt) · [Selbst erzeugen](#selbst-erzeugen) ·
[Wie die Daten abgesichert sind](#wie-die-daten-abgesichert-sind) · [Fehler gefunden?](#fehler-gefunden-fragen) ·
[Versionen und Zitieren](#versionen-und-zitieren)

---

## Was herauskommt

| Datei | Inhalt |
|---|---|
| `RSG_2030_Planungsmatrizen.csv` | jede Zelle jeder Planungsmatrix: Region, IST/PLAN, Zeile, Fach, Wert – und woher der Wert kommt (PDF-Seite, Originaltext, ggf. Korrekturregel) |
| `RSG_2030_Versorgungsdichte.csv` | je Region × IST/PLAN × Zeile × Fach: ÄAVE im ÖSG-Zuschnitt, Bevölkerung, Versorgungsdichte; für «insgesamt» dazu das Soll-Intervall (ÖSG) und Lage, Position und ÄAVE-Abstand dazu |
| `RSG_2030_Stellen.csv` | je Region × IST/PLAN × Stellen-Zeile × Fach: vertragsärztliche Planstellen und Sachleistungsstellen **im selben Fach-Zuschnitt wie die ÄAVE**, dazu der Maximalanteil vertragsärztlicher Planstellen |
| `RSG_2030_Planungsmatrizen.xlsx` | zum Nachsehen: die Matrizen je Land, alle Prüfungen, Korrekturen, Österreich-Summe |
| `Pruefbericht.md` | alle Zahlen des Laufs: Zellen nach Herkunft, Prüfungen, Korrekturen, Stand der Freigabe |
| `Laufprotokoll_*.json` | wann und womit die Dateien entstanden sind, mit Prüfsummen |

Jede Spalte ist in [docs/DATEN.md](docs/DATEN.md) beschrieben.

Beispiel aus der Versorgungsdichte, Version 2026.1 (Innere Medizin einschließlich Pulmologie,
[docs/METHODIK.md](docs/METHODIK.md) R4; PLAN 2030, Zeile «insgesamt»):

| Land | ÄAVE | Bevölkerung 1.1.2030 | Versorgungsdichte | Soll-Intervall (ÖSG) | Lage | Position | ÄAVE-Abstand |
|---|---:|---:|---:|---|---|---:|---:|
| OÖ | 210,5 | 1.555.701 | 13,5 | 14,4–26,8 | unter | −0,07 | −13,5 |
| Wien | 695,0 | 2.101.123 | 33,1 | 14,4–26,8 | über | 1,51 | +131,9 |

OÖ liegt knapp unter der Untergrenze (Position −0,07), bis dorthin fehlen 13,5 ÄAVE Sachleistung; Wien liegt weit
darüber. Was jede Zahl aussagt und was nicht:
[docs/DATEN.md](docs/DATEN.md#vergleich-mit-dem-soll-intervall-welche-zahl-für-welche-aussage).

**Bevor Sie die Zahlen verwenden**, bitte alle Fallstricke in [docs/DATEN.md](docs/DATEN.md#fallstricke) lesen. Die
drei wichtigsten:

- **Ohne Wahlärzt:innen.** Die Versorgungsdichte zählt nur die Sachleistung (Kassenvertrag, Ambulatorien,
  Spitalsambulanzen). Die Soll-Intervalle des ÖSG sind aber *mit* Wahlärzt:innen berechnet. Die Werte liegen deshalb
  systematisch tiefer, als der ÖSG-Vergleich es vorsieht. Warum das so ist: [docs/METHODIK.md](docs/METHODIK.md), R1.
- **Zwei IST-Jahre.** Fünf Länder melden 2022, vier 2023. Die Bevölkerung passt jeweils zum Jahr des Landes.
- **Keine Österreich-Werte in der Versorgungsdichte.** Der ÖSG misst je Versorgungsregion. Die Excel-Mappe enthält eine
  reine Summe der Länder.

---

## Selbst erzeugen

Gebraucht wird **Python 3.13** (geprüft; andere Versionen können PDF-Text anders zerlegen) und eine
Internetverbindung.

```bash
git clone https://github.com/maxpli/rsg-2030-verordnungen.git
cd rsg-2030-verordnungen
python3.13 -m venv .venv
.venv/bin/pip install -c requirements.txt -e .
.venv/bin/python -m rsg2030 alles
```

`alles` lädt die Quelldateien (eine Anfrage nach der anderen, mit Pausen – einige Minuten), liest die Matrizen
aus, prüft sie und rechnet die Versorgungsdichte. Am Ende steht:

```
   ✓ RSG_2030_Planungsmatrizen.csv entspricht Version 2026.1 (SHA-256 …)
FREIGEGEBEN
   ✓ RSG_2030_Versorgungsdichte.csv entspricht Version 2026.1 (SHA-256 …)
   ✓ RSG_2030_Stellen.csv entspricht Version 2026.1 (SHA-256 …)
```

Die Ergebnisse liegen dann in `daten_ergebnis/`, die Quellen in `daten_original/`. `alles` besteht aus drei
Schritten, die sich auch einzeln aufrufen lassen: `download`, `daten`, `versorgungsdichte`. Die Befehle zur Pflege
(neue Verordnung, Bildseiten, Freigabe, Wächter) stehen in [docs/PIPELINE.md](docs/PIPELINE.md).

**Was tun, wenn ✗ statt ✓ erscheint?** Dann ist das Ergebnis ein anderes als das veröffentlichte. Ersetzt eine
Quelle online ihre Datei (Statistik Austria tut das unter derselben Adresse), lädt `download` automatisch die geprüfte
Fassung aus der Wayback Machine und sagt das im Log. Erscheint trotzdem ✗, bitte ein Issue eröffnen.

---

## Wie die Daten abgesichert sind

Jeder Wert in `RSG_2030_Planungsmatrizen.csv` steht so in der Verordnung – oder er trägt eine Kennzeichnung, warum
nicht (`korrigiert` mit Regel und Begründung, `abgeleitet` mit Rechnung). Fünf Ebenen:

1. **Quellen:** jede Datei mit Herkunft und SHA-256 im Register [`quellen.csv`](rsg2030/quellen/quellen.csv).
2. **Lesung:** Textseiten über die Position jedes Worts im PDF, Bildseiten von Hand abgetippt.
3. **Zweitlesung:** ein unabhängiges Verfahren (KI-Lesung aus dem Seitenbild) liest dieselben Seiten; jeder Lauf
   vergleicht Zelle für Zelle. Die Lesung liegt im Repository – zum Erzeugen braucht es weder KI noch API-Schlüssel.
4. **Prüfungen:** Rechenprüfungen bei jedem Lauf (Zeilensummen, Teile = Ganzes, Regionen = Bundesland …); Korrekturen
   nur mit Regel und Begründung ([`korrekturen.csv`](rsg2030/eingaben/2026/korrekturen.csv)).
5. **Freigabe:** Ein Mensch entscheidet am PDF, was keine Maschine unabhängig prüfen kann
   ([`freigabe.xlsx`](rsg2030/eingaben/2026/freigabe.xlsx)).

Ausführlich, mit dem Abgleich gegen das RSG-Monitoring der GÖG und der Übersicht, wie sicher welche Aussage ist:
[docs/PRUEFUNG.md](docs/PRUEFUNG.md). Die ÖSG-Regeln, jede mit Dokument und Seite: [docs/METHODIK.md](docs/METHODIK.md).

---

## Fehler gefunden? Fragen?

Bitte ein [Issue](../../issues/new/choose) eröffnen:

- **«Wert weicht vom PDF ab»** – mit Land, Matrix, Zeile, Fach und PDF-Seite. Jede Korrektur wird eine Zeile in
  `korrekturen.csv` mit Begründung, die Pipeline prüft sie wie jede andere.
- **«Frage zur Methodik»** – z. B. zu Fachzuordnung, Bevölkerung oder Soll-Intervallen.

Ohne GitHub-Konto: E-Mail an [max.plischke@loesungswerk.at](mailto:max.plischke@loesungswerk.at).

---

## Versionen und Zitieren

- Jede Version gehört zu einem **Verordnungsstand** (heute `2026`, Ordner `rsg2030/eingaben/2026/`). Was sich zwischen
  Versionen an den Daten ändert, steht mit Grund in [CHANGELOG.md](CHANGELOG.md).
- Zitieren: [CITATION.cff](CITATION.cff) (GitHub zeigt daraus «Cite this repository»).
- Lizenz: Code MIT ([LICENSE](LICENSE)); die erzeugten Daten CC BY 4.0 mit Quellenangabe
  ([LIZENZ_DATEN.md](LIZENZ_DATEN.md)). Die Werte stammen aus frei verwendbaren Quellen (Verordnungen, Open Data von
  Statistik Austria und ÖROK unter CC BY 4.0); aus dem ÖSG sind einzelne Angaben mit Quellenangabe übernommen
  (Richtwerte, Regionen), die ÖSG-Dateien selbst werden nur verlinkt. Die Lizenz jeder Quelldatei steht im Register.
  Die Schriften der Webseite (`web/fonts/`, IBM Plex) stehen unter der SIL Open Font License 1.1
  ([web/fonts/OFL.txt](web/fonts/OFL.txt)).

## Für Entwickler:innen

```bash
.venv/bin/pip install -c requirements.txt -e ".[dev]"
.venv/bin/python -m pytest -m "not slow"   # schnell, ohne Quelldaten
.venv/bin/python -m pytest                 # alles, braucht daten_original/ (python -m rsg2030 download)
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
.venv/bin/pre-commit install               # Prüfungen vor jedem Commit
```

Zwei Pakete: `oesg_methodik/` (die ÖSG-Regeln, unabhängig vom Datensatz) und `rsg2030/` (der Datensatz). Andere
Projekte binden das Paket in einer festen Version ein:
`rsg-2030-verordnungen @ git+https://github.com/maxpli/rsg-2030-verordnungen@2026.1` (Datenordner: Arbeitsordner
oder `RSG2030_DATEN`). Was in den veröffentlichten Dateien steht, bitte dort lesen, nicht mit Funktionen des Pakets
nachrechnen. Vor dem Umstellen auf eine neue Version: Abschnitt «Schnittstelle» im [CHANGELOG](CHANGELOG.md) – dort
steht, was sich an den importierbaren Namen geändert hat.
