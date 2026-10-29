# Die Daten

Zwei Tabellen, beide entstehen mit `python -m rsg2030 alles` in `daten_ergebnis/`:

1. **Tabelle Planungsmatrizen `RSG_2030_Planungsmatrizen.csv`** – die Planungsmatrizen, Zelle für Zelle, so wie sie in
   den Verordnungen stehen (plus dokumentierte Korrekturen).
2. **Tabelle Versorgungsdichte `RSG_2030_Versorgungsdichte.csv`** – daraus berechnet: die ÄAVE im Zuschnitt der
   ÖSG-Richtwerte, die Bevölkerung und die Versorgungsdichte je Region, Zeile und Fach, für «insgesamt» dazu das
   Versorgungsdichte-Soll-Intervall (ÖSG) und wo die Versorgungsdichte dazu liegt.

Dazu die Excel-Mappe `RSG_2030_Planungsmatrizen.xlsx` zum Lesen und die Laufprotokolle. Alle CSV-Dateien: UTF-8,
Komma als Trenner, Punkt als Dezimalzeichen.

---

## So arbeiten Sie mit den Tabellen

**Welche Tabelle wofür:**

| Frage | Tabelle |
|---|---|
| Versorgungsdichte und Lage zum Versorgungsdichte-Soll-Intervall (ÖSG); Länder und Regionen vergleichen | Tabelle Versorgungsdichte, Zeile `insgesamt` |
| ÄAVE spitalsambulant / extramural / insgesamt, IST → PLAN, absolut oder je 100.000 | Tabelle Versorgungsdichte |
| ÄAVE in Primärversorgungseinheiten (AM, KIJU) | Tabelle Versorgungsdichte, Zeile `pve` |
| Fächer ohne Richtwert (NCH, AN, STR, RAD, NUK, PMR, PAT, LAB, SON/IDB) und die Spalte `gesamt` | Tabelle Planungsmatrizen |
| Planstellen und Sachleistungsstellen **im selben Fach-Zuschnitt wie die ÄAVE** (ZMK inkl. KFO, IM inkl. PUL …) | Tabelle Stellen |
| Wahlärzt:innen, VGF, IST-Teilzeilen (niedergelassen, Ambulatorien), Faktoren, Stellen je **Matrixspalte** | Tabelle Planungsmatrizen – meist nur je Land sinnvoll, Spalte «Auswerten» der [Zeilen](#zeilen); Stellen: [Stellen lesen](#stellen-lesen) |
| Woher eine Zahl kommt (PDF, Seite, Originaltext, Korrekturregel) | Tabelle Planungsmatrizen |

Die Tabelle Versorgungsdichte nimmt Ihnen ab, was bei der Tabelle Planungsmatrizen leicht schiefgeht: Sie verwendet bei
den SVE-Ländern den richtigen Block (Fallstrick 3), schneidet die Fächer wie der ÖSG zu (Fallstrick 4) und hat die
passende Bevölkerung je IST-Jahr (Fallstrick 2). Nachdenken muss man dort nur über Summen (Fallstricke 4 und 10). Die
Tabelle Planungsmatrizen bleibt so, wie gedruckt.

Das gilt für Bundesländer und Versorgungsregionen gleich. Die VR ist die Ebene, auf der der ÖSG die
Versorgungsdichte misst; dort zusätzlich beachten: Rundung (Fallstrick 7), kleine Regionen (Fallstrick 6) und die
geschätzte PLAN-Bevölkerung ([Tabelle Versorgungsdichte](#rsg_2030_versorgungsdichtecsv)).

Beide CSV-Dateien sind im **«long»-Format**: eine Zeile je Wert, jede Eigenschaft in einer eigenen Spalte. Die Zahl
808,8 aus der NÖ-Matrix (IST 2023, Zeile «ÄAVE insgesamt», Allgemeinmedizin) ist zum Beispiel diese eine Zeile:

| Land | Ebene | Region_ID | Block | Abschnitt | Jahr | Zeile_ID | Fach | Wert | Roh | PDF | Seite |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NÖ | BL | NÖ | haupt | IST | 2023 | insgesamt | AM | 808.8 | 808,8 | RSG_NOe_2030_VO_Anlage.pdf | 1 |

Warum so: Die 41 Matrizen sind nicht gleich gebaut (andere Zeilen, andere Fachspalten je Land), und zu jeder einzelnen
Zahl gehört ihre Herkunft (PDF, Seite, Originaltext, ggf. Korrekturregel). Excel-Pivot, Power BI, R und Python filtern
und gruppieren direkt auf diesem Format. Wer die Matrizen so sehen will wie im PDF, öffnet die Excel-Mappe
(`RSG_2030_Planungsmatrizen.xlsx`, ein Blatt je Matrix).

**Achtung Excel mit deutscher Einstellung:** Die CSV-Dateien trennen mit Komma und haben einen Punkt als
Dezimalzeichen. Per Doppelklick geöffnet, landet alles in einer Spalte oder `48.41` wird zu einem Datum bzw. zu 4841.
So geht es richtig:

1. **Daten → Aus Text/CSV**, Datei wählen; Dateiursprung «65001: Unicode (UTF-8)», Trennzeichen «Komma».
2. **Daten transformieren**; Zahlenspalten (z. B. `VD`, `AAVE`, `Bevoelkerung`) markieren → Rechtsklick → **Typ ändern →
   Mithilfe des Gebietsschemas …** → Dezimalzahl, Gebietsschema «Englisch (USA)».
3. **Schließen & laden**.

**Beispiel: Versorgungsdichte PLAN 2030, Länder × Fächer**

- *Excel:* Einfügen → PivotTable aus der geladenen Tabelle Versorgungsdichte; Filter `Ebene` = BL, `Abschnitt` = PLAN
  und `Zeile_ID` = insgesamt, Zeilen `Land`, Spalten `Fach`, Werte `VD` (es gibt je Zelle genau einen Wert).
- *Python (pandas):*

  ```python
  import pandas as pd

  k = pd.read_csv("daten_ergebnis/RSG_2030_Versorgungsdichte.csv")
  plan = k[(k["Ebene"] == "BL") & (k["Abschnitt"] == "PLAN") & (k["Zeile_ID"] == "insgesamt")]
  plan.pivot(index="Land", columns="Fach", values="VD").round(1)
  ```

- *R (tidyverse):*

  ```r
  library(dplyr); library(tidyr)
  k <- read.csv("daten_ergebnis/RSG_2030_Versorgungsdichte.csv")
  k |> filter(Ebene == "BL", Abschnitt == "PLAN", Zeile_ID == "insgesamt") |>
    select(Land, Fach, VD) |> pivot_wider(names_from = Fach, values_from = VD)
  ```

Ergebnis (Ausschnitt): Burgenland AM 64,6 · Kärnten 51,2 · NÖ 50,0 … Ohne den Filter auf `Zeile_ID` gäbe es je Land
und Fach bis zu vier Werte (Fallstrick 10).

### Vergleich mit dem Soll-Intervall: welche Zahl für welche Aussage

Für die Zeile `insgesamt` hat die Tabelle Versorgungsdichte drei Zahlen zum Versorgungsdichte-Soll-Intervall (ÖSG).
Jede beantwortet eine andere Frage; erst zusammen geben sie ein richtiges Bild.

| Frage | Spalte | Beispielsatz |
|---|---|---|
| Liegt die Versorgungsdichte im Soll-Intervall? | `Lage_im_Intervall`: `unter`, `im`, `über` | «OÖ plant die Innere Medizin unter dem Soll-Intervall.» |
| Wo liegt sie, vergleichbar über Fächer und Regionen? | `Position_im_Intervall`: 0 = VDmin, 1 = VDmax | «… knapp unter der Untergrenze (Position −0,07).» |
| Wie viel ist das in ÄAVE? | `AAVE_Abstand_Intervall`: 0 im Intervall, negativ = fehlt bis VDmin, positiv = über VDmax | «Bis zur Untergrenze fehlen 13,5 ÄAVE Sachleistung.» |

Beispiele (PLAN 2030, Version 2026.1):

| Region, Fach | VD | Soll-Intervall | Lage | Position | ÄAVE-Abstand | Was es heißt |
|---|---:|---|---|---:|---:|---|
| OÖ, IM | 13,5 | 14,4–26,8 | unter | −0,07 | −13,5 | knapp unter der Grenze, aber 13,5 ÄAVE: eine echte Lücke in der Sachleistung |
| Westliche Obersteiermark (VR 66), KJP | 0,52 | 0,8–1,4 | unter | −0,46 | −0,26 | relativ weit darunter, aber eine Viertel-ÄAVE: kleine Region, schmales Intervall (Fallstrick 6) |
| Tirol, KJP | 1,41 | 0,8–1,4 | über | 1,01 | +0,04 | formal darüber, praktisch auf der Grenze |
| Wien, IM | 33,1 | 14,4–26,8 | über | 1,51 | +131,9 | weit darüber; Wien ist nicht Basis der Intervalle, und die ZAE stecken in IM (Fallstrick 4) |

Daraus folgt:

- Die **Lage** allein überzeichnet Fälle an der Grenze (Tirol). Der ÄAVE-Abstand zeigt, ob es um Bruchteile einer ÄAVE
  geht.
- Die **Position** allein überzeichnet kleine Regionen (VR 66). Der ÄAVE-Abstand ordnet ein.
- Der **ÄAVE-Abstand** allein macht große und kleine Regionen nicht vergleichbar. Dafür die Position.
- **Charts über mehrere Fächer:** die Position als Achse; das Soll-Intervall liegt dann für jedes Fach genau bei 0–1.
- **Innerhalb des Intervalls** macht der ÖSG keinen Unterschied: Position 0,2 ist nicht «schlechter» als 0,8.

Für alle drei gilt: Gemessen wird die **Sachleistung allein**, das Soll-Intervall gilt mit Wahlärzt:innen
(Fallstrick 1). «über» gilt damit auch nach ÖSG. «unter» heißt «die Sachleistung allein reicht nicht bis VDmin», nicht
«Unterversorgung nach ÖSG»; also «es fehlen 13,5 ÄAVE Sachleistung», nicht «laut ÖSG fehlen 13,5 ÄAVE». Weitere
Vorbehalte: Fallstrick 11.

---

## Fallstricke

Bitte vor jeder Auswertung lesen.

1. **Versorgungsdichte ohne Wahlärzt:innen, Soll-Intervalle mit.** Die Tabelle Versorgungsdichte zählt die
   *Sachleistung*: Zeile «ÄAVE insgesamt» = spitalsambulant + niedergelassen mit Kassenvertrag + Ambulatorien mit
   Kassenvertrag. Die Versorgungsdichte-Soll-Intervalle des ÖSG sind *mit* Wahlärzt:innen berechnet (ÖSG Textband S.39),
   und bei der Planung ist ihre Versorgungswirksamkeit «jedenfalls mit zu berücksichtigen» (Textband S.15). Eine Dichte
   unter dem Soll-Intervall heißt also nicht automatisch Unterversorgung nach ÖSG; eine Dichte darüber liegt auch nach
   ÖSG darüber, weil Wahlärzt:innen sie nur erhöhen. Für PLAN 2030 gibt es
   nach ÖSG gar keine Wahlärzt:innen in den Matrizen, im IST weisen sie nur 6 von 9 Ländern aus (siehe
   [unten](#wahlärztinnen-zeile-wahl)). Wo die Zeile nicht ausgefüllt ist, gibt es trotzdem Wahlärzt:innen (laut
   RSG-Monitoring, [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)), deshalb leer und nicht 0. Begründung:
   [METHODIK.md](METHODIK.md), R1.
2. **Zwei IST-Jahre.** IST 2022: Burgenland, Kärnten, Oberösterreich, Steiermark, Wien. IST 2023: Niederösterreich,
   Salzburg, Tirol, Vorarlberg. Spalte `Jahr` beachten. Die Bevölkerung passt jeweils zum Jahr des Landes. Die
   **niedergelassenen** ÄAVE sind wahrscheinlich je IST-Jahr mit einem anderen DAA gerechnet, OÖ mit einem eigenen: Im
   Vergleich zum RSG-Monitoring liegen sie je Fach und IST-Jahr um einen anderen Anteil höher, in OÖ noch einmal mehr
   (Zahlen: [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)). Niedergelassen und «insgesamt» zwischen diesen
   Gruppen nur mit Vorsicht vergleichen ([METHODIK.md](METHODIK.md), R8).
3. **Drei Länder planen in SVE statt ÄAVE** (Burgenland, Kärnten, Steiermark). Ihre Matrizen haben einen zweiten
   Block mit ÄAVE-Äquivalenten (`Block = aequivalent`). Vergleichbar mit anderen Ländern ist nur dieser Block;
   die Tabelle Versorgungsdichte verwendet ihn automatisch. Im Block `haupt` ist «spitalsambulant» in SVE gezählt
   (`Einheit = SVE`), die übrigen Zeilen in ÄAVE. Wer die Tabelle Planungsmatrizen selbst auswertet: `rsg2030/schema.py`
   (`bl_long`, `matrix_long`) wählt den Block je Land, aus den Daten abgeleitet, nicht als Liste von Ländern hinterlegt.
4. **Fächer nach ÖSG-Zuschnitt** (nur in der Tabelle Versorgungsdichte; die Tabelle Planungsmatrizen bleibt, wie
   gedruckt): AM enthält die ZAE aus SON/IDB spitalsambulant (in den Zeilen spitalsambulant und insgesamt), CH enthält
   KJC und PCH, IM enthält PUL, ZMK enthält KFO. PUL und KFO haben zusätzlich eine eigene Zeile gegen ihr eigenes
   Soll-Intervall. Wie jeder Wert entstanden ist, steht in der Spalte `Zuschnitt`. Details und Belege:
   [METHODIK.md](METHODIK.md), R4, R5 und R10.
   - **AM und IM, wo `Zuschnitt` «ZAE nicht getrennt ausgewiesen» sagt** (Wien; IST 2022 in Burgenland, Kärnten, OÖ,
     Steiermark): Der Richtwert zählt die ZAE zu AM. Dort stecken sie aber in den Fachspalten, vor allem IM (Beleg:
     RSG-Monitoring, [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)) – AM ist zu niedrig, IM zu hoch (wie
     viel, in Wien: METHODIK R5). AM und IM dort nur mit Vorsicht mit dem Soll-Intervall vergleichen; IST → PLAN enthält
     eine Umbuchung, kein reines Wachstum (METHODIK R5).
   - **Nicht über alle Fächer summieren:** In der Tabelle Versorgungsdichte enthält das Fach IM schon PUL und die Zeile
     ZMK schon KFO – eine Summe von `AAVE` (oder `VD`) über alle 17 Fächer zählt PUL und KFO doppelt, und weil KFO nur
     in manchen Ländern einen Wert hat, verzerrt das Ländervergleiche ungleich. Für eine Summe die Fächer PUL und KFO
     weglassen (so zählt auch der ÖSG, METHODIK.md R4). Auch dann ist es nicht die ganze ambulante Versorgung: NCH, AN,
     STR, RAD, NUK, PMR, PAT, LAB und SON/IDB außer der ZAE haben keinen Richtwert. Gesamtwerte stehen in der Tabelle
     Planungsmatrizen (Fachspalte `gesamt`; dort kommt jede ÄAVE einmal vor).
   - **Wo KFO steckt, ist je Land verschieden** – die Spalte `Zuschnitt` sagt es für jede Zelle. Sechs Länder
     (Burgenland, Kärnten, NÖ, Salzburg, Steiermark, Tirol) drucken eine eigene KFO-Spalte: `Zuschnitt` «ZMK + KFO»,
     dazu eine eigene KFO-Zeile. Oberösterreich nennt KFO nur in einer Fußnote (nächster Punkt). Vorarlberg und Wien
     haben keine KFO-Spalte und keine KFO-Zeile: `Zuschnitt` «ZMK (KFO nicht getrennt ausgewiesen)». Das heißt
     **enthalten, nur nicht einzeln gezeigt**, nicht «fehlt» – Wien schreibt es in Fußnote (5) («ZMK einschließlich
     54 SLS KFO»), Vorarlberg im Textteil («ZMK; einschließlich Kieferorthopädie, KFO», PDF-Seite 4). Die ZMK-Werte
     dieser beiden Länder sind also vollständig. Bei Wien kommt hinzu, dass dieselbe Fußnote auch
     «Zahnbehandler + Dentisten» zu ZMK rechnet; ob die anderen Länder das ebenso tun, sagen sie nicht
     ([offene_punkte.md](offene_punkte.md), «Steiermark»).
   - **KFO in Oberösterreich:** Das PDF nennt KFO nur in einer Fußnote zu ZMK, als **einen** Wert je Region (BL 38,2
     ÄAVE, gleich für IST und PLAN). Übernommen in `niedergelassen` (IST), `extramural` und `insgesamt`; die Aufteilung
     auf spitalsambulant, selbständige Ambulatorien, Kassenambulatorien und VGF/PVE gibt es nicht, und dass KFO
     niedergelassen mit Kassenvertrag ist, ist eine Annahme. Die 32 KFO-Planstellen derselben Fußnote stehen in den
     Stellen-Zeilen (IST je Träger, PLAN gemeinsame Sachleistungsstellen mit 100 % Maximalanteil;
     [METHODIK.md](METHODIK.md), R4). Dass es die Planstellen aller drei Träger sind, steht auf den Bezirksseiten
     derselben Anlage; der Maximalanteil und die PLAN-Zuordnung stehen nirgends und sind gelesen. In der Tabelle Versorgungsdichte steckt KFO in
     OÖ deshalb in `extramural` und `insgesamt`, nicht in `spitalsambulant` (Zuschnitt dort «ZMK (KFO nicht getrennt
     ausgewiesen)»). In der Tabelle Planungsmatrizen stehen die Werte mit `Quelle = korrigiert`, Regel `zusatz:…`.
5. **Keine Österreich-Werte in der Tabelle Versorgungsdichte.** Der ÖSG misst die Versorgungsdichte je
   Versorgungsregion; ein Österreich-IST würde zudem zwei Jahre mischen. Die Excel-Mappe (Blatt `AT_Gesamt`) enthält
   eine reine Summe der Länder. Wer Österreich-Werte rechnet, legt das in seiner Methodik fest – mit ÖSG-Bezug wäre
   «Österreich ohne Wien» ([METHODIK.md](METHODIK.md), «Österreich»).
6. **Kleine Regionen, schmale Soll-Intervalle.** In kleinen Versorgungsregionen verschiebt eine einzige ÄAVE die Dichte
   stark (z. B. Kinder- und Jugendpsychiatrie: Soll-Intervall 0,8–1,4 je 100.000; in Osttirol entspricht 1 ÄAVE ≈ 2,1).
   Dort sind Lage und Position nicht belastbar; der ÄAVE-Abstand zeigt, um wie wenig es oft geht (Beispiel VR 66 unter
   [Vergleich mit dem Soll-Intervall](#vergleich-mit-dem-soll-intervall-welche-zahl-für-welche-aussage)).
7. **VR-Werte sind gerundet.** Die Summe der Versorgungsregionen weicht vom Bundesland um bis zu ±0,2 ÄAVE ab
   (Wien: ganzzahlig, ±1–2).
8. **Fußnoten ändern die Bedeutung mancher Zahlen.** Jede Fußnote steht mit Einordnung im Verzeichnis
   [`fussnoten.csv`](../rsg2030/eingaben/2026/fussnoten.csv) (siehe [unten](#fußnoten)). Die wichtigsten:
   - **Oberösterreich, PLAN spitalsambulant:** Laut Fußnote wurde «von der Ausweisung eines neuen Planstandes 2030
     Abstand genommen und der IST-Stand 2022 fortgeschrieben», erhöht nur in Fächern, in denen ambulante
     Betreuungsplätze aufgebaut werden. PLAN spitalsambulant ist in OÖ also kein Plan, sondern das IST 2022 – das
     gilt auch für die Zeile `spitalsambulant` der Tabelle Versorgungsdichte.
   - **ZAE (zentrale ambulante Erstversorgung; Methodenband S.20):** stehen meist in SON/IDB spitalsambulant (Fußnote
     «spitalsambulant = ZAE»), sonst in den Fachspalten – Fallstrick 4.
   - **Wien, Planstellen gesamt:** ohne Bereinigung von Doppelzählungen (Zeile `planstellen_oegk_svs_bvaeb`).
9. **Mit dem RSG-Monitoring verknüpfen?** Spitalsambulant, in den Ambulatorien und bei den Wahlärzt:innen sind die
   IST-Werte der Verordnungen fast überall die des RSG-Monitorings der GÖG desselben Jahres. **Niedergelassen** liegen
   sie in allen Ländern darüber, je Fach und IST-Jahr um denselben Anteil (OÖ mehr) – wahrscheinlich ein anderer
   DAA-Stand (Fallstrick 2). Zeitreihen aus dem Monitoring und IST der Verordnungen daher nicht ohne
   Weiteres aneinanderhängen ([PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)).
10. **Zeilen der Tabelle Versorgungsdichte nicht addieren.** `spitalsambulant` + `extramural` = `insgesamt` (bis auf die
    Rundung der gedruckten Zahlen), und `pve` steckt in `insgesamt`. Eine Summe über `Zeile_ID` zählt also doppelt;
    immer erst nach einer Zeile filtern. Einzelne Teilzeilen:
    - **`pve` im PLAN ist ein Mindestwert** («zumindest»), im IST die tatsächliche Zahl; nur AM und KIJU. Wo im IST
      «-» steht (Tirol), ist der Wert 0.
    - **`spitalsambulant`** fehlt, wo die Matrix die Zelle leer druckt (Fach ohne Spitalsambulanz in der Region). Der
      ÖSG sagt zu den spitalsambulanten ÄAVE selbst, ihnen komme «nur eine eingeschränkte Aussagekraft» zu (METHODIK
      R2).
    - **`extramural`** enthält die niedergelassenen ÄAVE, mit dem DAA-Vorbehalt aus Fallstrick 2.
    - **ZAE in den Fachspalten** (Wien; IST 2022 in Burgenland, Kärnten, OÖ, Steiermark, siehe Fallstrick 4): Dort
      stecken die ZAE im IST in `spitalsambulant` der Fachspalten, vor allem IM; im PLAN stehen sie außer in Wien in
      SON/IDB und damit in AM. Ein Rückgang von IM `spitalsambulant` IST → PLAN ist dort zum Teil nur diese Umbuchung,
      kein Abbau.
    - Ein Soll-Intervall gibt es nur für `insgesamt` ([METHODIK.md](METHODIK.md), R10).
11. **Lage, Position und ÄAVE-Abstand richtig lesen.** Welche Zahl für welche Aussage, mit Beispielen:
    [Vergleich mit dem Soll-Intervall](#vergleich-mit-dem-soll-intervall-welche-zahl-für-welche-aussage). Dazu:
    - **Der ÖSG verlangt nur «im Intervall».** Die VD «soll in jeder Versorgungsregion … im angegebenen Intervall
      liegen» (Textband S.38). Innerhalb des Intervalls macht er keinen Unterschied.
    - **Ohne Wahlärzt:innen:** «unter» und «im» sind nach ÖSG nicht abschließend, «über» schon (Fallstrick 1).
    - **Ohne Patientenströme:** Die VD teilt durch die Wohnbevölkerung der Region. Der ÖSG verlangt die Bewertung
      «unter Berücksichtigung von regionalen Austauschbeziehungen» (Textband S.38), «inkl. Wechselwirkungen zwischen
      den Regionen wie z.B. Pendlerbewegungen» (S.37). Regionen, die ihr Umland mitversorgen, liegen deshalb eher
      höher, das Umland eher tiefer. Das gilt besonders auf Ebene der Versorgungsregionen.
    - **IST gegen die Norm 2030:** Die Soll-Intervalle gelten für 2030; ein IST-Wert daran gemessen zeigt den Abstand
      zur Norm 2030, nicht eine Verletzung im IST-Jahr.
12. **Bevölkerung der VR 64/65 weicht vom ÖSG ab.** Die VR-Bevölkerung ist die Summe der Bezirke laut
    GÖG-Gliederung; der ÖSG-Tabellenband nennt für die Oststeiermark (VR 64) 1.671 Einwohner mehr und für die
    West-/Südsteiermark (VR 65) 1.671 weniger (1.1.2021) – alle anderen 30 VR sind exakt gleich. Ursache ist der
    eingefrorene Gebietsstand 2019 der ÖSG-Gliederung: Die Gemeinde Murfeld wechselte mit 1.1.2020 vom Bezirk
    Südoststeiermark (VR 64) in den Bezirk Leibnitz (VR 65)
    ([METHODIK.md](METHODIK.md#bekannte-grenzen-und-offene-fragen), Punkt 7); die VD
    und die Position im Soll-Intervall dieser beiden Regionen tragen diese Unschärfe.

---

## `RSG_2030_Planungsmatrizen.csv`

Eine Zeile je Zelle. Eindeutiger Schlüssel: `Land, Ebene, Region_ID, Block, Abschnitt, Zeile_ID, Fach`.

| Spalte | Bedeutung |
|---|---|
| `Land` | Burgenland, Kärnten, NÖ, OÖ, Salzburg, Steiermark, Tirol, Vorarlberg, Wien |
| `Ebene` | `BL` (Bundesland) oder `VR` (Versorgungsregion) |
| `Region_ID`, `Region_Name` | bei BL: `Region_ID` = Landesname, `Region_Name` leer; bei VR die ÖSG-Nummer (11–93) und der ÖSG-Name |
| `Block` | `haupt` = Matrix in der Planungsgröße des Landes · `aequivalent` = Zusatzblock «sofern Planungsgröße nicht ÄAVE gemäß ÖSG» (nur Burgenland, Kärnten, Steiermark) |
| `Abschnitt` | `IST` oder `PLAN` |
| `Jahr` | IST-Jahr laut Matrix (2022 oder 2023) bzw. 2030 |
| `Zeile_ID` | Matrixzeile, siehe [Zeilen](#zeilen) |
| `Einheit` | `ÄAVE`, `SVE` (Standardversorgungseinheiten, ÖSG Textband S.235: Zeile «SVE spitalsambulant» im Block `haupt` von Burgenland, Kärnten, Steiermark – so beschriftet im PDF), `Stellen`, `Anzahl`, `Prozent`, `Faktor` |
| `Fach` | Fachspalte, Kürzel der ÖSG-Vorlage ohne Fußnotenzeichen: AM, AN, KIJU, KJC, KJP, CH, NCH, IM, GGH, NEU, PSY, DER, AU, HNO, URO, PCH, PUL, ORTR, MKG, ZMK, KFO, STR, RAD, NUK, PMR, PAT, LAB, SON/IDB – oder `gesamt` ([METHODIK.md](METHODIK.md), R4) |
| `Wert` | Zahl; leer = kein Wert (siehe [Zellbedeutung](#zellbedeutung)) |
| `Roh` | Text genau so, wie er im PDF steht («12,1», «-», «n.v.», «x») |
| `Rundung` | halbe Einheit der letzten Stelle («12,1» → 0,05); Toleranz der Prüfungen. Anzahlen sind exakt (0) |
| `Quelle` | woher der Wert kommt, siehe [Herkunft eines Werts](#herkunft-eines-werts-spalte-quelle) |
| `Regel` | bei `korrigiert`: die angewandte Regel aus `korrekturen.csv`; bei `abgeleitet`: die Rechnung (z. B. `summe:niedergelassen+selbst_amb+kassen_amb`) |
| `Zeile_PDF_roh`, `PDF`, `Seite` | Zeilenbeschriftung im PDF, Dateiname, Seite (1-basiert, wie im PDF-Viewer) |

Umfang: 41 Matrizen (9 Bundesländer, 32 Versorgungsregionen). Wie viele Zellen aus dem PDF, von Hand, korrigiert oder
abgeleitet sind, steht im Prüfbericht des Laufs (`daten_ergebnis/Pruefbericht.md`).

### Herkunft eines Werts (Spalte `Quelle`)

| `Quelle` | Bedeutung | `Roh` |
|---|---|---|
| `PDF` | so im PDF gelesen | Text aus dem PDF |
| `manuell` | Seite ohne Textebene (Bild): von Hand abgetippt, mit einer zweiten, KI-gestützten Lesung abgeglichen ([PRUEFUNG.md](PRUEFUNG.md), Ebene 2 und 3) | abgetippter Text |
| `korrigiert` | **weicht vom PDF ab** oder füllt eine Lücke im PDF – per Regel aus `korrekturen.csv`, mit Begründung (Lücke, Widerspruch, Fußnote …) | Text aus dem PDF (bzw. leer, wenn die Zelle im PDF fehlt) |
| `abgeleitet` | **steht für dieses Land nicht im PDF**, andere Länder weisen den Wert aber aus; aus PDF-Werten derselben Matrix gerechnet, damit dieselbe Größe überall unter derselben `Zeile_ID` steht. Kein PDF-Wert wird dabei geändert | was gedruckt war: leer oder «-» |

Heute abgeleitet – Rechnung in `rsg2030/ableitungen.py`:

- IST `extramural` in allen Ländern außer Wien (Summe der drei Teilzeilen).
- das **gesamt-%** der Zeilen «- davon maximal als vertragsärztliche Planstellen in %», wo es nicht gedruckt ist: das
  mit den Stellen gewichtete Mittel der Fach-% derselben Zeile, auf eine Nachkommastelle. So rechnen alle Länder, die
  es drucken (Prüfung `prozent_gesamt`). Nur wo jedes Fach mit Stellen ein % hat; sonst bleibt es leer (OÖ BL und
  VR 41, zusätzliche SVS-Stellen: % für URO fehlt).

### Zellbedeutung

| Im PDF | `Wert` |
|---|---|
| Zahl | die Zahl |
| «-» | **0** (nichts geplant/vorhanden) in ÄAVE-, Stellen- und Anzahl-Zeilen; in Prozent- und Faktor-Zeilen leer (kein Anteil, weil keine Stellen) |
| «-» in einer %-Zeile, wo darüber **Stellen > 0** stehen (Fachspalte) | **0 %** – ein Anteil muss dort stehen, «-» ist die Null der Matrix (Burgenland KJP: BL 0 %, VR 11/12 «-»; Steiermark CH, VR 66 KIJU). In der Spalte «gesamt» heißt «-» «nicht ausgerechnet»: dort steht das abgeleitete gesamt-% (siehe oben) |
| «n.v.» | leer – nicht verfügbar |
| «x» | leer – Anzahl nicht ausgewiesen |
| «-» / «0» in einer **optionalen Zeile ohne eine einzige Zahl > 0** (Wahlärzt:innen) | leer – nicht ausgefüllt (Regel `nicht_ausgewiesen`: Steiermark BL, Vorarlberg VR). In ausgefüllten Zeilen bleibt ein einzelnes «-» = 0 |
| leer / schraffiert | leer – nicht vorgesehen |

### Zeilen

Eine Größe heißt in IST und PLAN gleich; ob IST oder PLAN, steht in der Spalte `Abschnitt` (`Zeile_ID` hat keinen
Vorsatz `ist_`/`plan_`).

| Zeile_ID | Einheit | Abschnitt | Inhalt | Auswerten |
|---|---|---|---|---|
| `spitalsambulant` | ÄAVE (SVE) | IST/PLAN | ÄAVE spitalsambulant (bei SVE-Ländern im Block `haupt`: SVE, `Einheit = SVE`) | Tabelle Versorgungsdichte (im ÖSG-Zuschnitt) – Vorsicht: wo die ZAE stehen und OÖ PLAN = IST (Fallstrick 8) |
| `niedergelassen` | ÄAVE | IST | niedergelassene Ärzt:innen mit Kassenvertrag | Länder vergleichen (nur IST) |
| `selbst_amb` | ÄAVE | IST | selbständige Ambulatorien mit Kassenvertrag | Länder vergleichen (nur IST) |
| `kassen_amb` | ÄAVE | IST | Kassenambulatorien | Länder vergleichen (nur IST) |
| `extramural` | ÄAVE | IST/PLAN | **extramural** (im PDF «niedergelassene ÄrztInnen und in selbstständigen Ambulatorien … gesamt»): niedergelassen + selbständige Ambulatorien + Kassenambulatorien (alle mit Kassenvertrag), ohne Spitalsambulanzen = insgesamt − spitalsambulant. IST im PDF nur in Wien, sonst `abgeleitet` | Tabelle Versorgungsdichte (im ÖSG-Zuschnitt) |
| `insgesamt` | ÄAVE | IST/PLAN | **ÄAVE insgesamt (ohne Wahlärzt:innen)** – Grundlage der Kennzahlen | Tabelle Versorgungsdichte (im ÖSG-Zuschnitt, mit Soll-Intervall) |
| `vgf` | ÄAVE | IST/PLAN | **Teilmenge von `insgesamt`**: davon in Vergemeinschaftungsformen im extramuralen Bereich (IST: Gruppenpraxen, PVE, Ambulatorien; PLAN: PVE, Ambulatorien – nur OÖ und Steiermark) (Tabellenband S.231) | Teilmenge – nicht addieren; PLAN nur je Land |
| `pve` | ÄAVE | IST/PLAN | **Teilmenge von `vgf`** (PLAN: von `insgesamt`): davon in Primärversorgungseinheiten (Zentren und Netzwerke); im PLAN **«zumindest»**, also ein Mindestwert; Werte nur in AM und KIJU (Tabellenband S.231) | Tabelle Versorgungsdichte; Teilmenge – nicht addieren; PLAN ist ein Mindestwert |
| `wahl` | ÄAVE | IST | Wahlärzt:innen und selbständige Ambulatorien ohne Kassenvertrag – **nicht** in `insgesamt` enthalten (optionale Angabe, [siehe unten](#wahlärztinnen-zeile-wahl)) | nur je Land – nicht alle Länder füllen sie aus |
| `planstellen_oegk/_svs/_bvaeb` | Stellen | IST | vertragsärztliche Planstellen je Träger – **nicht über Träger addieren**: eine Stelle hat meist Verträge mit mehreren Trägern («die Werte dürfen nicht addiert werden», Steiermark Anlage 1 S.65, Glossar) | nur je Träger und Land |
| `planstellen_oegk_svs_bvaeb` | Stellen | IST | nur Wien: «ÖGK/SVS/BVAEB Planstellen gesamt», laut Fußnote 14 **ohne Bereinigung von Doppelzählungen**. Keine Summe der drei Träger-Zeilen (AM: ÖGK 800, SVS 829, BVAEB 813, gesamt 842) – nicht addieren | nur Beleg |
| `amb_standorte` | Anzahl | IST | Ambulatorien-Standorte | nur je Land |
| `slst_gemeinsam` | Stellen | PLAN | **gemeinsame Sachleistungsstellen aller Krankenversicherungsträger**: Planstellen und ärztliche VZÄ in Ambulatorien (Tabellenband S.232) | nur je Land; [Stellen lesen](#stellen-lesen) |
| `slst_eva` | Stellen | PLAN | **Teilmenge von `slst_gemeinsam`**: davon in Einrichtungen für Erstversorgung-Allgemeinmedizin (EVA; Textband S.67, S.76 – in Burgenland und Kärnten «Erstversorgungsambulanz») | Teilmenge – lückenhaft, nicht vergleichen |
| `slst_zus_oegk/_svs/_bvaeb` | Stellen | PLAN | zusätzliche trägerspezifische Sachleistungsstellen; `slst_zus_oegk` ist in allen Matrizen 0 oder «-» | nur je Träger und Land; [Stellen lesen](#stellen-lesen) |
| `…_max_vaep_prozent` | Prozent | PLAN | zur jeweils vorigen Stellen-Zeile: **wie viele dieser Stellen höchstens als Kassenpraxis** (vertragsärztliche Planstelle, niedergelassen) besetzt werden dürfen; der Rest ist für Ärzt:innen in Ambulatorien vorgesehen. 100 % = alle dürfen Kassenpraxis sein, 0 % = alle im Ambulatorium (Tabellenband S.232: Sachleistungsstellen «umfassen Planstellen für niedergelassene VertragsärztInnen und der geplanten ärztlichen Vollzeitäquivalente in Ambulatorien … Davon ist jeweils der Maximalanteil für vertragsärztliche Planstellen in Prozent auszuweisen»). gesamt = mit den Stellen gewichtetes Mittel der Fach-% | nur je Land, nie summieren |
| `umr_spitalsambulant`, `umr_niedergelassen`, `umr_selbst_amb`, `umr_kassen_amb`, `umr_wahl` | Faktor | IST/PLAN | Umrechnungsfaktoren SVE → ÄAVE (nur Block `aequivalent`), je Teilzeile: Name = `umr_` + Zeile_ID der Teilzeile; Abschnitt und Jahr laut Überschrift der Faktoren: meist «IST 2022», Steiermark BL «PLAN 2030» | nur Beleg (Rechenweg SVE → ÄAVE-Äquivalente) |
| `extramural_inkl_wahl`, `gastpat_*`, `slst_gesamt` | | | Wien-spezifische Zeilen | nur Beleg |

Reihenfolge wie in der ÖSG-Vorlage (Tabellenband S.239). «Auswerten»: *Länder vergleichen* = gleich definiert in
allen Ländern (Fallstricke beachten) · *nur je Land* = Definition oder Ausfüllung unterscheidet sich zwischen Ländern ·
*Teilmenge* = steckt in der genannten Zeile, nie dazuzählen · *nur Beleg* = zum Nachvollziehen, nicht zum Auswerten.

### Wahlärzt:innen (Zeile `wahl`)

Laut ÖSG optional (Tabellenband S.231), für PLAN nach ÖSG nie enthalten (Tabellenband S.232). Je Matrix:

| Land | Bundesland | Versorgungsregionen |
|---|---|---|
| Kärnten | Werte | keine Zeile (2 VR) |
| NÖ | Werte | Werte (5 VR) |
| OÖ | Werte | keine Zeile (6 VR) |
| Salzburg | Werte | Werte (2 VR) |
| Tirol | Werte | Werte (4 VR) |
| Wien | Werte | Werte (3 VR) |
| Steiermark | nicht ausgefüllt (im PDF nur «-», «n.v.») → leer | keine Zeile (6 VR) |
| Vorarlberg | keine Zeile | nicht ausgefüllt (im PDF nur «0», «n.v.») → leer |
| Burgenland | nicht ausgefüllt (im PDF nur «-», «n.v.») → leer | keine Zeile (2 VR) |
| **Summe** | **6 von 9 mit Werten** | **14 von 32 mit Werten** |

Oberösterreich weist ZMK ohne Kieferorthopädie aus; die Wahlärzt:innen in KFO nennt die OÖ-Fußnote nicht
([METHODIK.md](METHODIK.md), R4). `wahl` ZMK ist dort also unvollständig – um wie viel, sagt die Verordnung nicht
(Größenordnung: [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), Punkt 4).

---

### Stellen lesen

Die Stellen stehen nur in der Tabelle Planungsmatrizen, nicht in der Tabelle Versorgungsdichte: Ein Vergleich IST → PLAN
braucht Annahmen, die jede Auswertung selbst festlegen muss ([METHODIK.md](METHODIK.md), «Stellen»). Was beim Lesen
gilt:

- **IST und PLAN zählen Verschiedenes.** IST `planstellen_<träger>` sind vertragsärztliche Planstellen laut
  Stellenplan, in OÖ ausdrücklich besetzte und unbesetzte. PLAN `slst_*` sind Sachleistungsstellen: Planstellen
  **und** ärztliche VZÄ in Ambulatorien (Tabellenband S.232). Wien bewertet zusätzliche Sachleistungsstellen nach
  ihrer Versorgungswirksamkeit (Textteil S.19).
- **Gemeinsam und zusätzlich.** `slst_gemeinsam` steht den Versicherten aller Träger offen, `slst_zus_<träger>` nur
  denen eines Trägers (Steiermark, Glossar Anlage 1 S.65). Für einen Träger sind es also gemeinsam + zusätzlich; bei
  der ÖGK ist «zusätzlich» überall 0 oder «-». Dass IST `planstellen_<träger>` und PLAN gemeinsam + zusätzlich
  zueinander passen, ist eine Beobachtung, keine Regel (Zahlen: METHODIK, «Stellen»).
- **Nie über Träger addieren**, weder im IST noch im PLAN: Eine Stelle hat meist Verträge mit mehreren Trägern.
- **Die %-Zeile gehört zur Zeile darüber.** `slst_gemeinsam_max_vaep_prozent` sagt, wie viele der gemeinsamen Stellen
  höchstens Kassenpraxis sein dürfen, `slst_zus_svs_max_vaep_prozent` nur für die zusätzlichen SVS-Stellen
  (Tabellenband S.232: «jeweils»). Höchstzahl Kassenpraxen eines Trägers = gemeinsam × % + zusätzlich × %, je Fach
  gerechnet und erst danach summiert; das gesamt-% ist ein gewichtetes Mittel und dafür nicht geeignet.
- **Technische Fächer:** In Burgenland, Salzburg und Tirol steht an den technischen Fächern «Für Ambulatorien können
  derzeit keine Sachleistungsstellen ausgewiesen werden» (Fußnote); dort sind die Sachleistungsstellen nur Planstellen.
- **KFO in Oberösterreich:** Die 32 KFO-Planstellen stammen aus der Fußnote zu ZMK, nicht aus der Matrix
  (`Quelle = korrigiert`, Regel `zusatz:32` bzw. `wert:100` für den Maximalanteil). ZMK + KFO bedeutet damit bei den
  ÄAVE und bei den Stellen dasselbe; die Lesart ist nicht bestätigt ([offene_punkte.md](offene_punkte.md)).

### Fußnoten

Die Fußnoten der Matrixseiten stehen nicht in der Tabelle Planungsmatrizen, sondern mit Fundstelle im Verzeichnis
[`fussnoten.csv`](../rsg2030/eingaben/2026/fussnoten.csv): Land, Matrix, PDF, Seite, Zeichen («(4)», in Oberösterreich
«*ZMK»), Text wie gedruckt, Einordnung und Verweis.

| Einordnung | Bedeutung |
|---|---|
| Vorlage | Text der ÖSG-Vorlage, Platzhalter nicht mit Werten gefüllt – Bedeutung siehe unten |
| Hinweis | erläutert, ändert weder eine Zahl noch, was sie bedeutet |
| Teilmenge | nennt einen «davon»-Wert (z. B. EVA, Unfallchirurgie, PSD), der nicht als eigene Zelle übernommen wird |
| betrifft Werte | ändert Zahlen oder ihre Bedeutung – Verweis auf die Regel bzw. Doku-Stelle |
| Methodenfrage | offen, Verweis auf [offene_punkte.md](offene_punkte.md) |

**Was in den Teilmengen-Fußnoten steht** – diese Werte sind in den Zellen schon enthalten und stehen nicht einzeln in
der Tabelle: «davon in Unfallchirurgie (UC)» mit ÄAVE und Planstellen (Kärnten, NÖ, Salzburg, Tirol, Wien), «davon in
Akut-Ordinationen EVA», in NÖ auch mit Planstellen (BL PLAN 4, VR 34 und 35 je 2), und die Ambulatorien der
psychosozialen Versorgung: Kärnten «davon … ÄAVE in PSD-Ambulatorien», Burgenland «… werden mit den PLAN-VZÄ
(KJP = 6,625; PSY = 5,00) in den PLAN-Werten berücksichtigt», Steiermark «davon geplante ärztliche VZÄ (KJP = 4,00;
PSY = 15,50) für die sozialpsychiatrischen Ambulatorien», Wien «davon 32 SLS in KJP-PSD-Ambulatorien». Wer KJP und PSY
liest, sollte wissen, dass dort in diesen Ländern die ärztlichen VZÄ dieser Ambulatorien stecken.

**Fußnoten der ÖSG-Vorlage** (Tabellenband, Anhang 9 RSG-PM, S.239; hinterlegt in
`oesg_methodik/referenz/oesg_rsgpm_fussnoten.csv`). Die Länder übernehmen sie, oft mit anderer Nummer:

| Zeichen in der Vorlage | an | Text | Bedeutung für die Daten |
|---|---|---|---|
| (1) | NCH | in Regiomed nicht berücksichtigt | NCH-ÄAVE «werden nur im spitalsambulanten Bereich ausgewiesen» (Tabellenband S.232); kein Richtwert |
| (2) | KJC, PCH | zugeordnet zu CH | deren ÄAVE sind in CH enthalten (S.252: «ÄAVE für PCH sind unter der CH subsummiert»); in allen Ländern stehen bei KJC und PCH 0 ÄAVE (Prüfung `kjc_pch_in_ch`); die Kennzahlen zählen sie zu CH |
| (3) | ORTR | davon in Unfallchirurgie (UC) … | Teilmenge von ORTR |
| (4) | AM | davon in Akut-Ordinationen EVA … | Teilmenge von AM |
| (5) | SON/IDB | spitalsambulant = ZAE; … extramural = sonstige/interdisziplinäre Angebote | SON/IDB spitalsambulant sind die ZAE; der AM-Richtwert enthält sie (Textband S.39), die Kennzahlen zählen sie zu AM (METHODIK R5) |

Dass das Verzeichnis vollständig ist und jeder Text so auf seiner Seite steht, prüft `tests/test_fussnoten.py` am PDF;
die Einordnung jeder Fußnote, die nicht wörtlich der Vorlage entspricht, bestätigt ein Mensch (Freigabe, Blatt
«Fußnoten»).

## `RSG_2030_Versorgungsdichte.csv`

Eine Zeile je Region × Abschnitt × Zeile × Fach. Eindeutiger Schlüssel: `Ebene, Region_ID, Abschnitt, Zeile_ID, Fach`.
9 Bundesländer und 32 Versorgungsregionen, je IST und PLAN; die Zeilen `spitalsambulant`, `extramural`, `insgesamt`
mit den 17 Richtwert-Fächern, `pve` nur mit AM und KIJU. KFO nur, wo es eine eigene Spalte hat oder, in OÖ, aus der
Fußnote kommt; ein Fach fehlt, wenn die Matrix dort keinen Wert hat (spitalsambulant öfter, Fallstrick 10).

| Spalte | Bedeutung |
|---|---|
| `Datensatz` | immer `RSG 2030` (damit Tabellen anderer Datensätze dieselbe Form haben) |
| `Land`, `Ebene`, `Region_ID` | wie in der Tabelle Planungsmatrizen |
| `Abschnitt`, `Jahr` | IST (2022/2023) oder PLAN (2030) |
| `Zeile_ID` | `spitalsambulant`, `extramural`, `insgesamt` oder `pve` ([METHODIK.md](METHODIK.md), R10); nicht addieren (Fallstrick 10) |
| `Fach` | Richtwert-Zeile des ÖSG (Textband S.39), in deren Reihenfolge: AM, KIJU, KJP, CH, IM, PUL, GGH, NEU, PSY, DER, AU, HNO, URO, ORTR, MKG, ZMK, KFO |
| `Basis` | immer `Sachleistung` (ohne Wahlärzt:innen, siehe Fallstrick 1) |
| `AAVE` | ÄAVE der Zeile im ÖSG-Zuschnitt: AM = AM + ZAE (SON/IDB spitalsambulant; nur in spitalsambulant und insgesamt), CH = CH + KJC + PCH, IM = IM + PUL, ZMK = ZMK + KFO ([METHODIK.md](METHODIK.md), R4, R5); SVE-Länder: ÄAVE-Äquivalente |
| `Zuschnitt` | welche Spalten der Matrix eingegangen sind, z. B. «AM + ZAE», «ZMK (KFO nicht getrennt ausgewiesen)», «ZMK + KFO (KFO nicht in der Tabelle, per Korrekturregel)» (OÖ). Genannt sind die Spalten mit einem Wert > 0 und die, die in der Matrix fehlen |
| `Bevoelkerung` | Wohnbevölkerung am 1.1. – IST: des IST-Jahres des Landes; PLAN: 1.1.2030 laut Prognose ([METHODIK.md](METHODIK.md), R7); in allen Zeilen einer Region und eines Abschnitts gleich |
| `VD` | Versorgungsdichte = `AAVE / Bevoelkerung × 100.000` |
| `VDmin`, `VDmax` | Versorgungsdichte-Soll-Intervall (ÖSG) des Fachs, Planungshorizont 2030 (ÖSG Textband S.39); nur bei `insgesamt`, sonst leer |
| `Lage_im_Intervall` | `unter`, `im` oder `über` dem Soll-Intervall; genau auf VDmin oder VDmax = `im` |
| `Position_im_Intervall` | `(VD − VDmin) / (VDmax − VDmin)`: 0 = Untergrenze, 1 = Obergrenze, < 0 darunter, > 1 darüber |
| `AAVE_Abstand_Intervall` | `(VD − nächste Grenze) × Bevoelkerung / 100.000`: 0 im Soll-Intervall, negativ = so viele ÄAVE fehlen bis VDmin, positiv = so viele liegen über VDmax |

Die letzten drei sind **unsere Kennzahlen**, nicht aus dem ÖSG; nur bei `insgesamt`, sonst leer. Wann welche passt:
[Vergleich mit dem Soll-Intervall](#vergleich-mit-dem-soll-intervall-welche-zahl-für-welche-aussage).

Die Bevölkerung der Versorgungsregionen im PLAN ist eine Schätzung (Landesprognose × ÖROK-Anteil der Region), keine
amtliche Zahl. Die Regionen eines Landes summieren sich genau zum Landeswert.

## `RSG_2030_Stellen.csv`

Dasselbe wie die Tabelle Versorgungsdichte, nur für die **Stellen**: vertragsärztliche Planstellen (IST) und
Sachleistungsstellen (PLAN), zugeschnitten auf die Richtwert-Fächer des ÖSG – mit **derselben Funktion** wie die ÄAVE,
damit ein Fach in beiden Tabellen dasselbe bedeutet. Eine Zeile je Region × Abschnitt × Stellen-Zeile × Fach;
eindeutiger Schlüssel: `Ebene, Region_ID, Abschnitt, Zeile_ID, Fach`.

Wofür sie da ist: Die Stellen stehen in der Tabelle Planungsmatrizen je **Matrixspalte**. Wer Stellen und ÄAVE
gegenüberstellt, müsste den Zuschnitt sonst selbst nachbauen – und zwar genau so, sonst vergleicht er ZMK ohne KFO mit
ZMK inklusive KFO.

| Spalte | Bedeutung |
|---|---|
| `Datensatz`, `Land`, `Ebene`, `Region_ID`, `Abschnitt`, `Jahr` | wie in der Tabelle Versorgungsdichte |
| `Zeile_ID` | IST: `planstellen_oegk`, `planstellen_svs`, `planstellen_bvaeb`, `planstellen_oegk_svs_bvaeb` (nur Wien). PLAN: `slst_gemeinsam`, `slst_eva`, `slst_zus_oegk`, `slst_zus_svs`, `slst_zus_bvaeb`, `slst_gesamt` (nur Wien). Bedeutung: [Stellen lesen](#stellen-lesen) |
| `Fach` | dieselbe Richtwert-Zeile wie in der Tabelle Versorgungsdichte – **nicht** die gedruckte Matrixspalte |
| `Stellen` | Stellen des Fachs im ÖSG-Zuschnitt: CH = CH + KJC + PCH, IM = IM + PUL, ZMK = ZMK + KFO. **AM ist hier nur die Spalte AM** – ohne ZAE, anders als bei den ÄAVE (siehe unten) |
| `Zuschnitt` | welche Matrixspalten eingegangen sind, z. B. «ZMK + KFO»; genannt sind die Spalten mit einem Wert > 0 und die, die in der Matrix fehlen |
| `Max_VAEP_Stellen` | davon höchstens vertragsärztliche Planstellen: Stellen × Maximalanteil **je Matrixspalte**, erst dann summiert. Leer, wo die Vorlage keinen Maximalanteil vorsieht (alle IST-Zeilen, `slst_eva`) |
| `Max_VAEP_Prozent` | `Max_VAEP_Stellen / Stellen × 100` – ein gewichtetes Mittel, **nie** ein Mittel aus Prozentsätzen. Leer, wenn die Zeile 0 Stellen hat |

**Drei Dinge, die beim Summieren schiefgehen:**

- **IST nicht addieren, PLAN schon.** Dieselbe Planstelle hat meist Verträge mit mehreren Trägern und steht in
  mehreren `planstellen_…`-Zeilen; «die Werte dürfen nicht addiert werden» (Tabellenband S.231). Die
  PLAN-Sachleistungsstellen dagegen sind verschiedene Stellen – die Vorlage nennt sie «Gemeinsame
  Sachleistungsstellen aller KV-Träger» und «**zusätzliche** ÖGK-/SVS-/BVAEB-Sachleistungsstellen», und Wiens
  gedruckte Gesamtzeile ist in allen 27 Fachspalten genau ihre Summe.
- **`slst_eva` ist eine Teilmenge** von `slst_gemeinsam` («- davon in EVA»), nicht dazuzählen.
- **PUL und KFO nicht mitsummieren:** Sie stecken schon in IM bzw. ZMK (wie in der Tabelle Versorgungsdichte,
  Fallstrick 4). Und: Die Fächer ohne Richtwert (NCH, AN, STR, RAD, NUK, PMR, PAT, LAB, SON/IDB) sind in dieser
  Tabelle **nicht** enthalten; die Summe über alle Fächer ist deshalb kleiner als die gedruckte Spalte `gesamt`.
  Dass dabei nichts still wegfällt, prüft `tests/test_stellen.py` gegen genau diese Spalte.

**Warum AM hier anders zugeschnitten ist als bei den ÄAVE:** Der AM-Richtwert enthält die ZAE (Textband S.39,
Legende **), und in der Tabelle Versorgungsdichte zählen sie deshalb zu AM – aber nur in den Zeilen `spitalsambulant`
und `insgesamt`. Sachleistungsstellen bilden den extramuralen Bereich ab (Tabellenband S.232), ZAE sind
spitalsambulant (Vorlage (Tabellenband S.239), Fußnote (5)). In einer Stellen-Zeile gehört SON/IDB daher nicht zu AM.
Betroffen ist nur Tirol: 8,05 Stellen in SON/IDB (Anlage S.1), die dort bleiben.

**Der `Zuschnitt`-Text kann sich zwischen den beiden Tabellen unterscheiden**, obwohl dieselben Spalten summiert
werden: Genannt werden die Spalten mit einem Wert > 0. In Vorarlberg hat PCH im PLAN 0,0 ÄAVE, aber 1
Sachleistungsstelle – dort steht bei den ÄAVE «CH», bei den Stellen «CH + PCH».

## Excel-Mappe `RSG_2030_Planungsmatrizen.xlsx`

Zum Lesen, nicht zum Weiterrechnen (dafür die CSV-Dateien):

| Blatt | Inhalt |
|---|---|
| `Lies mich` | kurze Erklärung der Blätter, für alle, die nur die Mappe öffnen |
| `BL_<Land>`, `VR_<Nr>` | jede Matrix wieder als Tabelle wie im PDF, mit den Werten nach der Korrektur (der Text aus dem PDF steht in der CSV-Spalte `Roh`); `Summe_Fachspalten` und `Gesamt_Delta` = «gesamt» minus Summe der Fachspalten. Ein kleines Delta ist meist Rundung im PDF: Die Länder runden «gesamt» und die Fächer je für sich (Prüfung `zeilensumme` in `_Checks`) |
| `AT_Gesamt` | Summe der neun Länder je Zeile und Fach – **IST aus zwei Jahren** (2022: 5 Länder, 2023: 4). `Gesamt_Delta` ist die Summe der Deltas der Länder; diese heben sich teils auf, das Delta je Land steht im Blatt des Landes. Eine leere Zelle eines Landes zählt wie 0, eine Zelle kann also eine Teilsumme sein (z. B. Wahlärzt:innen: Burgenland und Steiermark ohne Angabe) |
| `_Checks` | jede Prüfung mit Ergebnis (ok / bekannt / Abweichung) |
| `_Befunde_roh` | was die Prüfungen am unkorrigierten PDF finden |
| `_Korrekturen` | jede angewandte Regel mit betroffenen Zellen |
| `_Auslesen` | Hinweise und Fehler beim Auslesen und beim Abgleich der Eingaben (meist Seitenzahlen, Störtext) |
| `_Meta` | Umfang und Stand |

## Laufprotokolle

`Laufprotokoll_daten.json` und `Laufprotokoll_versorgungsdichte.json` halten je Lauf fest: Zeit, Paketversion, Git-Stand
(wenn aus einem Klon), Python- und Paketversionen, SHA-256 jeder Ausgabe und ob sie der veröffentlichten Version
entspricht (`Abgleich_Version`). `"Git_sauber": false` heißt: Lauf mit nicht committeten Änderungen.
