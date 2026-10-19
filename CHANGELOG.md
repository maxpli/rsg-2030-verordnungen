# Änderungen

Hier steht, was sich zwischen Versionen an den **Daten** ändert – jede Änderung einer Prüfsumme in
`rsg2030/erwartete_ausgaben.csv`, mit Grund – und an den Befehlen. Versionen: `<Verordnungsstand>.<Nummer>`.

## 2026.1 – erste veröffentlichte Version

**Daten** (Verordnungsstand 2026, alle neun RSG 2030 laut RIS):

| Datei | SHA-256 | Zeilen (inkl. Kopf) |
|---|---|---:|
| `RSG_2030_Planungsmatrizen.csv` | `e698e4e1bea31891b6a9885451f5bc65db697cc3e8f9fcd0b12221f0b0435058` | 30.802 |
| `RSG_2030_Versorgungsdichte.csv` | `10d40c25de44662ab48f039d3f905bda87598faa0e66027d5528e6f9ecbfaa49` | 4.191 |

**Was drin ist:**

- **Tabelle Planungsmatrizen:** jede Zelle der 41 Planungsmatrizen (9 Bundesländer, 32
  Versorgungsregionen), 39 aus dem PDF ausgelesen, 2 Bildseiten von Hand abgetippt. Je Zelle Originaltext (`Roh`),
  Seite und Herkunft (`Quelle`, `Regel`). Zeilen und Fächer heißen wie in der ÖSG-Vorlage (Tabellenband Anhang 9,
  S.259); Spalten: docs/DATEN.md.
- **Abgeleitete Zeilen,** wo die Vorlage ein Feld vorsieht, ein Land es aber nicht ausfüllt: IST «extramural» (acht
  Länder) und gesamt-% der Sachleistungsstellen (gewichtetes Mittel der Fach-%). `Quelle = abgeleitet`, `Roh` leer.
- **Tabelle Versorgungsdichte:** je Region, IST/PLAN, Zeile und Fach die ÄAVE im Zuschnitt der ÖSG-Richtwerte,
  Bevölkerung und Versorgungsdichte. Zeilen spitalsambulant, extramural, insgesamt und PVE (nur AM und KIJU, PLAN als
  Mindestwert); Versorgungsdichte-Soll-Intervall (ÖSG) und drei Kennzahlen dazu, nur bei insgesamt: Lage
  (`Lage_im_Intervall`: unter, im, über), Position (`Position_im_Intervall`, 0 = VDmin, 1 = VDmax) und ÄAVE-Abstand
  (`AAVE_Abstand_Intervall`) (docs/METHODIK.md, R3, R10). Basis Sachleistung (ohne Wahlärzt:innen), Ebenen BL und VR,
  keine Österreich-Ebene (METHODIK R1 und «Österreich»). Fächerzuschnitt (METHODIK R4, R5): AM inkl. ZAE (nur
  spitalsambulant und insgesamt), CH inkl. KJC und PCH, IM inkl. PUL, ZMK inkl. KFO; KFO zusätzlich als eigenes Fach
  gegen sein eigenes Soll-Intervall. Die Spalte `Zuschnitt` zeigt je Wert, welche Spalten eingegangen sind. Stellen, VGF
  und Wahlärzt:innen bleiben in der Tabelle Planungsmatrizen (METHODIK, «Stellen»).
- **SVE-Länder** (Burgenland, Kärnten, Steiermark): vergleichbare ÄAVE aus dem Block der ÄAVE-Äquivalente; «SVE
  spitalsambulant» trägt die Einheit `SVE`.
- **Bevölkerung** nach ÖSG-Methode aus Open Data von Statistik Austria (CC BY 4.0) und ÖROK-Prognose 2021
  (METHODIK R7).

**Wie die Daten abgesichert sind** (docs/PRUEFUNG.md; alle Zahlen eines Laufs im Prüfbericht):

- Jede Quelldatei per SHA-256 geprüft, URL-Quellen mit Archivkopie in der Wayback Machine. ÖSG-Text- und
  Tabellenband kommen aus dem RIS (ÖSG-Gutachten 5/2025), nicht von goeg.at: amtlich kundgemacht, und der Wächter
  meldet eine neue Fassung. Der Text ist Seite für Seite derselbe wie in den goeg.at-Fassungen (verglichen mit
  pdfplumber, 19.10.2026); die Dateien unterscheiden sich, weil das RIS seine PDFs signiert.
- Jede Abweichung vom PDF ist eine Regel in `korrekturen.csv` mit Befund und Begründung: 39 Regeln, 381 Zellen.
- 13 Rechenprüfungen (Teile = Summe, VR = BL, SVE × Faktor = ÄAVE-Ä, %-Zeilen u. a.): 15.142 ok, 40 bekannte
  Abweichungen mit Grund in `bekannte_abweichungen.csv`, keine offene.
- **Zweitlesung:** jede Matrix ein zweites Mal unabhängig gelesen (KI aus dem Seitenbild, ohne die erste Lesung zu
  kennen). 29.516 Zellen gleich, 9 Abweichungen, 6 Zellen nicht verglichen – alle 15 am PDF entschieden, in allen
  stimmt die erste Lesung.
- **Fußnoten:** jede Fußnote jeder Matrix im Verzeichnis `fussnoten.csv`, Text wie gedruckt und eingeordnet; ein Test
  prüft am PDF, dass keine fehlt.
- **Tests gegen die Quelle:** Richtwerte gegen ÖSG-Textband S.37, Zuordnung Bezirk → Versorgungsregion gegen die
  GÖG-Datei «Regionale Gliederung», Zeilen und Spalten der Vorlage gegen Tabellenband S.259; Versorgungsdichte für
  jedes Land von Hand nachgerechnet, die Teilzeilen an Beispielen; spitalsambulant + extramural = insgesamt in jeder
  Region, jedem Abschnitt und Fach.
- **Freigabe:** Was keine Maschine unabhängig prüfen kann (Abweichungen der Zweitlesung, Bildseiten, abweichende
  Spalten und Zeilen, Fußnoten, jede Korrektur und bekannte Abweichung), hat ein Mensch je Zeile bestätigt
  (`freigabe.xlsx`, alle Blätter). Der Lauf endet mit `FREIGEGEBEN`.
- Geprüft: Lauf in einem leeren Ordner mit frischem Download aller 38 Quellen ergibt beide Dateien Byte für Byte
  (19.10.2026).

**Bekannte Grenzen:** docs/METHODIK.md, «Bekannte Grenzen und offene Fragen»; Widersprüche im PDF und wie sie
entschieden sind: Blatt «Entscheidungen» der Freigabe.
