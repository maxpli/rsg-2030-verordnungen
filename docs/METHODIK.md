# Methodik: ÖSG-Regeln und Kennzahlen

Diese Datei hält fest, **was der Österreichische Strukturplan Gesundheit (ÖSG) zu den Größen sagt, mit denen hier
gerechnet wird**, und **was daraus folgt**. Jede Regel hat eine Quelle mit Seite. Seitenangaben beziehen sich auf die
Seite im PDF (1-basiert). Beim Textband stimmt sie mit der gedruckten Seitenzahl überein; der Tabellenband zählt in
den Anhängen eigens (z. B. «RSG-PM / Seite 1 von 12»); im Methodenband ist die gedruckte Seitenzahl um 10 kleiner
(Methodenband S.18 = gedruckt Seite 8).

**Quellen** (nach `python -m rsg2030 download` unter `daten_original/oesg/`; Herkunft und SHA-256 im Register
`rsg2030/quellen/quellen.csv`)

| Kürzel | Dokument |
|---|---|
| Textband | ÖSG 2023 – Textband, Stand 10.10.2025; im RIS kundgemacht als ÖSG-Gutachten 5/2025 (`SPG_AT_OSG_G_20251010_5_2025`, Hauptdokument) |
| Tabellenband | ÖSG 2023 – Tabellenband, Stand 10.10.2025, Anlage desselben RIS-Dokuments (Anhang 9 = RSG-Planungsmatrix) |
| Methodenband | Methodenband zum ÖSG 2023 – Wartung 2025 (nur bei der GÖG, nicht im RIS) |

Im Code steckt die ÖSG-Methodik im Paket `oesg_methodik/` – unabhängig vom Datensatz RSG 2030 (`rsg2030/`), damit
sie später auch für andere Datensätze dienen kann.

---

## Begriffe

| Begriff | Bedeutung | Quelle |
|---|---|---|
| **ÄAVE** | ärztliche ambulante Versorgungseinheit: durchschnittliches ärztliches Leistungsvolumen je Fach im Regiomed-System der Sozialversicherung. Eine ÄAVE entspricht grundsätzlich einer durchschnittlich arbeitenden Kassenärztin bzw. einem Kassenarzt. Keine Kopfzahl. Bei Spitalsambulanzen über ärztliche VZÄ in nicht bettenführenden Kostenstellen. Regelwerk je Sektor: R2a | Tabellenband S.12–13; Textband S.227; Methodenband S.26 |
| **Regiomed** | Datensystem des Dachverbands der Sozialversicherungsträger (DVSV), aus dem die ÄAVE stammen | Textband S.37 |
| **DAA** | «durchschnittlich arbeitende Ärztin/Arzt», Bezugsgröße der ÄAVE-Berechnung im Kassenbereich | Methodenband S.17 |
| **Sachleistung** | ambulanter Bereich mit Kassenvertrag: niedergelassene Ärzt:innen und Gruppenpraxen mit Kassenvertrag, selbständige Ambulatorien mit Kassenvertrag, Kassenambulatorien **und Spitalsambulanzen**. Nicht zu verwechseln mit den *Sachleistungsstellen*: Die planen nur den extramuralen Teil (Planstellen und Ambulatorien, Tabellenband S.232; Tirol, Anlage S.1, Fußnote (8): «Sachleistungsstellen sollen die Versorgung im niedergelassenen Bereich sowie in selbständigen Ambulatorien … abbilden») | Textband S.15 |
| **Wahlärzt:innen** | niedergelassen, ohne Vertrag mit einer Krankenkasse (ausgenommen KFA/KUF), mit mindestens einer Privatordination; Fach = Erstfach laut Ärzteliste | Textband S.236 |
| **SVE** | Standardversorgungseinheit: Planungsgröße einiger Länder statt ÄAVE; ein Umrechnungsschlüssel auf ÄAVE je Fach ist anzugeben | Textband S.37, S.78 |
| **VD** | Versorgungsdichte = ÄAVE je 100.000 Einwohner:innen der Wohnbevölkerung | Textband S.38–39 |
| **VDmin / VDmax** | Grenzen des Versorgungsdichte-Soll-Intervalls (kurz: Soll-Intervall) je Fach, Planungshorizont 2030 | Textband S.39 |
| **Vertragsärztliche Planstellen** | IST: Anzahl der Planstellen je KV-Träger laut Stellenplan; eine Stelle hat meist Verträge mit mehreren Trägern («die Werte dürfen nicht addiert werden»); OÖ: besetzte und unbesetzte Stellen | Tabellenband S.231; Steiermark Anlage 1 S.65; OÖ Anlage S.10, Fußnote |
| **Sachleistungsstellen** | PLAN: aus den PLAN-ÄAVE abgeleitete Stellen, «Planstellen für niedergelassene VertragsärztInnen und der geplanten ärztlichen Vollzeitäquivalente in Ambulatorien»; gemeinsame Stellen aller KV-Träger und zusätzliche einzelner Träger, «jeweils» mit dem Maximalanteil für vertragsärztliche Planstellen in Prozent; EVA als Teilmenge der gemeinsamen | Tabellenband S.232 |

---

## Regeln

### R1 – VD für den Vergleich mit dem Soll-Intervall enthält Wahlärzt:innen

> VD Versorgungsdichte – ÄAVE (inkl. „abrechnungsrelevante“ WahlärztInnen) pro 100.000 EinwohnerInnen der
> Wohnbevölkerung — *Textband S.39, Legende*

Die Soll-Intervalle (VDmin/VDmax) wurden mit Wahlärzt:innen berechnet. Eine VD nur aus der Sachleistung liegt
systematisch darunter.

**Gleichzeitig gilt für PLAN:**

> In der Darstellung des PLAN-Stands ÄAVE insgesamt sind WahlärztInnen und selbstständige Ambulatorien ohne
> Kassenvertrag nicht enthalten, da diese nicht der Versorgungsplanung unterliegen. — *Tabellenband S.232*

Für PLAN 2030 gibt es also in den RSG keine Wahlärzt:innen. Im IST sind sie in der Matrix nur «optional»
(Tabellenband S.231; Textband S.76). Für die Planung selbst gilt aber:

> Daher sind bei der integrativen Versorgungsplanung als Rahmenbedingungen jedenfalls mit zu berücksichtigen:
> • Die Versorgungswirksamkeit von WahlärztInnen, WahltherapeutInnen, Sanatorien und sonstigen Wahleinrichtungen,
> sofern von diesen sozialversicherungsrechtlich erstattungsfähige Leistungen erbracht werden — *Textband S.15*

Der ÖSG erwartet also nicht, dass die Sachleistung allein im Soll-Intervall liegt, sondern Sachleistung und
Wahlärzt:innen zusammen. Wie viel die Wahlärzt:innen 2030 beitragen, sagt er nicht.

**Entscheidung: Die Kennzahlen rechnen nur mit der Sachleistung, keine VD inkl. Wahlärzt:innen.**
- **PLAN:** Die PLAN-ÄAVE enthalten nach ÖSG keine Wahlärzt:innen (Zitat oben). Für 2030 gibt es nur die Sachleistung.
- **IST:** Die Wahlärzt:innen sind optional und nur in 6 von 9 Bundesländern und 14 von 32 Versorgungsregionen
  ausgewiesen ([DATEN.md](DATEN.md#wahlärztinnen-zeile-wahl)). Damit lassen sich weder die Länder untereinander
  noch IST und PLAN vergleichen.

Wer die Kennzahlen mit den Soll-Intervallen vergleicht, vergleicht also **strenger** als die ÖSG-Definition und sollte
das in seiner Methodik nennen. Die Kennzahlen beantworten die Frage «Reicht die Sachleistung allein bis ins
Soll-Intervall?». Daraus folgt eine **Asymmetrie**: «über» gilt auch nach ÖSG, weil Wahlärzt:innen die VD nur erhöhen;
«unter» und «im» sind nach ÖSG nicht abschließend – Wahlärzt:innen können eine Lücke füllen oder eine VD über VDmax
heben. Die Zeile `wahl` bleibt in der Tabelle Planungsmatrizen für eigene Auswertungen.

### R2 – Sachleistung = Zeile «insgesamt», Spitalsambulanzen gehören dazu

Laut ÖSG zählen die Spitalsambulanzen zur Sachleistung (Textband S.15). Die Zeile «ÄAVE insgesamt» der RSG-Matrix
ist spitalsambulant + niedergelassen mit Kassenvertrag + selbständige Ambulatorien mit Kassenvertrag +
Kassenambulatorien (Tabellenband S.231).

Einschränkung laut ÖSG: Den spitalsambulanten ÄAVE «kommt nur eine eingeschränkte Aussagekraft zu», weil
Spitalsambulanz und extramuraler Bereich unterschiedlich arbeiten (Textband S.38, Fußnote 39).

### R2a – Woraus eine ÄAVE entsteht

Das maßgebliche Regelwerk steht im **Tabellenband, Anhang 5 – PM, S.12–13** («Regelwerk zur Berechnung ärztlicher
ambulanter Versorgungseinheiten für den gesamten ambulanten Bereich pro Fachrichtung 2021»). Es zählt je
Versorgungssektor **verschieden**:

| Sektor | Grundlage | Fundstelle |
|---|---|---|
| **niedergelassene Vertragspartner** | **Quartalserstpatient:innen** aus e-card-Konsultationen, geteilt durch den österreichweiten Durchschnitt eines ganzjährigen Durchschnittsarztes | S.12, A1–A3 |
| Wahlärzt:innen | Ärztekostenstatistik und gemeldete Kostenerstattungen; dazu Vertragspartner mit reinem GU/VU-Vertrag | S.12–13, B1–B2 |
| **Spitalsambulanzen** | **ärztliche Vollzeitäquivalente** der nicht bettenführenden Kostenstellen × Anteil der ambulanten an allen Frequenzen; UC inkl. UKH | S.13, C1–C3 |
| eigene Einrichtungen der KV-Träger | jährliche Erhebung der ÄAVE durch die Träger | S.13, D1 |
| Institute (selbständige Ambulatorien mit Kassenvertrag) | abgerechnete Beträge je Fach und Bezirk, geteilt durch den «abgerechneten Betrag pro Arzt»; bei Allergieambulatorien stattdessen die tatsächlichen VZÄ | S.13, E1 |

**Quartalserstpatient:in** = «der erste Kontakt eines Patienten/einer Patientin bei einem Vertragspartner eines
Fachgebietes pro Quartal» (S.12, A1). Weitere Kontakte desselben Menschen im selben Quartal zählen nicht mit;
Konsultationshäufigkeit und Betreuungsaufwand gehen also nicht ein. Der Durchschnittsarzt aus A2 ist eine Einzelpraxis
mit ganzjährigem ÖGK-Vertrag, statistische Ausreißer ausgenommen (S.12, A2; Auswahlkriterien auch Methodenband S.17).

**Die Einheit ist in sich nicht einheitlich.** Extramural misst sie Patientenköpfe je Quartal, spitalsambulant
ärztliche Vollzeitäquivalente, bei Instituten abgerechnete Beträge. Der ÖSG hält dazu selbst fest, den
spitalsambulanten ÄAVE komme «nur eine eingeschränkte Aussagekraft» zu (Textband S.38, Fußnote 39, siehe R2);
S.13, C1–C3 zeigt, warum. Eine Zeile «insgesamt» addiert damit drei verschieden konstruierte Größen. Für den
Vergleich mit dem Soll-Intervall verlangt der ÖSG trotzdem die Summe (R3).

### R3 – So entstehen die Soll-Intervalle

- Basis: Regiomed **2021**, **Österreich ohne Wien** (Wien als Großstadt nicht vergleichbar). *Methodenband S.18,
  Fußnote 1; Textband S.38: «Auf Basis der errechneten Versorgungsdichte im Bundesdurchschnitt (ohne Wien)»*
- Schritte: VD 2021 je Fach → ÄAVE 2030 mit Bevölkerung 2030 → plus Umlagerung stationär → spitalsambulant →
  neuer Mittelwert 2030. *Methodenband S.18*
- Soll-Intervall = Mittelwert 2030 **±30 %**: «Die oberen und unteren Grenzen der Planungsrichtwerte‐Intervalle 2030 …
  ergeben sich durch die bereits bisher verwendete Bandbreite von +/–30 Prozent (ausgehend vom in Schritt 4
  ermittelten Mittelwert zum Planungsrichtwerte‐Intervall 2030).» *Methodenband S.19, Schritt 5.* Nachgerechnet: AM
  VDmin 34,9 / VDmax 64,8 → Mitte 49,85, ±30 % ergibt genau diese Grenzen. Die Mitte ist also **nicht** VD2021 (48,7).
- **Widerspruch in den Unterlagen:** Textband S.38 («Auf Basis der errechneten Versorgungsdichte im Bundesdurchschnitt
  (ohne Wien) wurde durch Heranziehen einer Bandbreite von +/-30 % das Versorgungsdichte-Soll-Intervall ermittelt»)
  und Methodenband S.13, Tabelle 1.1 («Bandbreitenmodell (+/–30 % um BdoW)») lesen sich, als läge VD2021 in der Mitte.
  Die gedruckten Grenzen passen nur zu Schritt 5: mit VD2021 als Mitte wäre VDmin bei AM 34,1, gedruckt ist 34,9. Wir
  folgen Schritt 5.
- **Gedruckt sind nur die Grenzen, gerundet auf eine Nachkommastelle.** Den Mittelwert 2030 druckt der ÖSG nicht. Die
  Grenzen passen zu «Mittelwert ± 30 %», genau ± 30 % um ihren Mittelpunkt sind sie aber nicht: bei KJP (0,8–1,4)
  rund ± 27 %. Ein Test prüft beides (`tests/test_oesg_methodik.py`,
  `test_soll_intervall_ist_mitte_plus_minus_30_prozent`).
- Die VD «soll in jeder Versorgungsregion (unter Berücksichtigung von regionalen Austauschbeziehungen) im angegebenen
  Intervall liegen» (*Textband S.38*).
- Soll-Intervalle gelten für den Planungshorizont 2030. Ein IST-Wert daran gemessen heißt: «wo stehen wir gemessen an
  der Norm 2030».

**Drei Kennzahlen zum Soll-Intervall**, alle **unsere**, nicht aus dem ÖSG, nur bei `insgesamt`. Sie setzen nur an den
gedruckten Grenzen VDmin und VDmax an, nie an der Mitte, und widersprechen sich deshalb nie (Test):
- **Lage** (Spalte `Lage_im_Intervall`): `unter`, `im` oder `über`; eine VD genau auf einer Grenze liegt `im`
  Intervall. Das ist die Aussage, die der ÖSG verlangt: Die VD soll «im angegebenen Intervall liegen» (Textband S.38).
- **Position** (Spalte `Position_im_Intervall`) = (VD − VDmin) / (VDmax − VDmin): 0 = Untergrenze, 1 = Obergrenze,
  < 0 darunter, > 1 darüber. Sie macht die Fächer vergleichbar und zeigt auch innerhalb, wie nah eine Region einer
  Grenze ist. Innerhalb des Intervalls macht der ÖSG keinen Unterschied.
- **ÄAVE-Abstand** (Spalte `AAVE_Abstand_Intervall`) = (VD − nächste Grenze) × Bevölkerung / 100.000: 0 im Intervall,
  negativ = so viele ÄAVE fehlen bis VDmin, positiv = so viele liegen über VDmax. Die Größe in der Einheit, in der die
  RSG planen.

Alle drei messen die Sachleistung allein (R1): «über» gilt auch nach ÖSG, «unter» und «im» nicht abschließend. Wann
welche Zahl passt, mit Beispielen: [DATEN.md](DATEN.md#vergleich-mit-dem-soll-intervall-welche-zahl-für-welche-aussage).

Der Begriff «Versorgungsdichte-Soll-Intervall» stammt aus dem Textband (S.38, Legende S.37); der Methodenband nennt
dasselbe «Planungsrichtwerte-Intervall» (S.18–19).

### Österreich – keine eigene Ebene in den Kennzahlen

**Was der ÖSG sagt:**
- Das Soll-Intervall gilt **je Versorgungsregion** (Textband S.38, Zitat bei R3). Eine Versorgungsdichte für ganz
  Österreich ist keine Planungsgröße des ÖSG.
- Ein Bundesdurchschnitt kommt nur als Ausgangspunkt der Soll-Intervalle vor, und zwar **ohne Wien** (Textband S.38;
  Legende VD2021 «ohne Wien», Textband S.39; Methodenband S.18).

**Dazu kommt:** Die IST-Jahre der Länder unterscheiden sich (2022: Burgenland, Kärnten, OÖ, Steiermark, Wien;
2023: NÖ, Salzburg, Tirol, Vorarlberg). Eine Österreich-Summe im IST ist kein Stand zu einem Stichtag.

**Entscheidung:** Die Kennzahlen haben die Ebenen Bundesland und Versorgungsregion, **keine
Österreich-Ebene**. Die Excel-Mappe enthält die Summe der Länder (Blatt `AT_Gesamt`, mit Hinweis auf die IST-Jahre).
Wer Österreich-Werte braucht, rechnet sie in der eigenen Analyse und legt dort fest, wie; mit ÖSG-Bezug wäre
«Österreich ohne Wien».

### R4 – Fächer zusammenfassen

**Namen der Spalten.** Die Tabelle Planungsmatrizen verwendet die Kürzel der ÖSG-Vorlage der RSG-Planungsmatrix
(Tabellenband, Anhang 9, S.239: «AM(4) AN KIJU KJC(2) KJP CH NCH(1) IM GGH NEU PSY DER AU HNO URO PCH(2) PUL ORTR(3) MKG
ZMK STR RAD NUK PMR PAT LAB SON/IDB(5) gesamt»), ohne die Fußnotenzeichen; dazu KFO, das sechs Länder als eigene Spalte
führen. Was die Fußnoten der Vorlage bedeuten: [DATEN.md](DATEN.md#fußnoten).

**Zuschnitt für den Richtwert.** Die Richtwerttabelle (Textband S.39) schneidet manche Fächer anders zu als die
Spalten der Matrix. Für den Vergleich zählen die Kennzahlen die Spalten so zusammen, wie der Richtwert sie enthält:

| Richtwert-Zeile (Textband S.39) | Spalten der Matrix | Beleg |
|---|---|---|
| AM | AM + ZAE (SON/IDB spitalsambulant) | R5 |
| CH | CH + KJC + PCH | Vorlage (Tabellenband S.239), Fußnote (2) an KJC und PCH: «zugeordnet zu CH»; Tabellenband S.232: «ÄAVE für PCH sind unter der CH subsummiert und werden nur in Bezug auf die vertragsärztlichen Planstellen der KV-Träger im IST-Stand ausgewiesen.» In der Vorlage sind die ÄAVE-Zellen von KJC und PCH mit «-» vorbelegt |
| IM | IM + PUL | Unterzeile «- davon Pulmologie (PUL) / Innere Medizin-Pneumologie (IM-PUL)»; in der Matrix getrennte Spalten |
| PUL | PUL | eigener Richtwert der Unterzeile |
| ORTR | ORTR | Fußnote 2: «Summe aus UC, OR und den im spitalsambulanten Bereich dem Fachbereich ORTR zugeordneten ÄAVE»; die RSG-2030-Matrizen haben keine eigenen OR/UC-Spalten. Die Spalte ORTR enthält in allen Ländern Orthopädie und Unfallchirurgie (Abgleich mit dem RSG-Monitoring, [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)); OÖ sagt es in der Fußnote «inkl. Unfallkrankenhaus Linz» nur ausdrücklich |
| ZMK | ZMK + KFO | Unterzeile «- davon mit kieferorthopädischem Schwerpunkt»; KFO je Land siehe unten |
| KFO | KFO | eigenes Soll-Intervall der Unterzeile (2,8–5,1); nur wo KFO eine eigene Spalte hat oder aus der Fußnote kommt (OÖ) |
| KJP | KJP | Richtwert «in Anlehnung an die Bedarfsplanungsrichtlinie in Deutschland» (Fußnote 1) |
| KIJU, GGH, NEU, PSY, DER, AU, HNO, URO, MKG | gleichnamige Spalte | |
| KJC, NCH, PCH | – | kein Richtwert («*»); KJC und PCH gehen in CH ein, NCH «in Regiomed nicht berücksichtigt» (Vorlage, Fußnote (1)) |
| RAD, LAB, NUK, PAT, PMR | – | keine Richtwerte, nicht im Regiomed-Modell (Textband S.39; Methodenband S.26) |
| AN, STR, SON/IDB | – | keine Richtwertzeile; SON/IDB spitalsambulant geht als ZAE in AM ein (R5) |

Damit gibt es Kennzahlen für **17 Fächer**: die 16 Fächer mit eigener Spalte und Richtwert und KFO als Unterzeile von
ZMK (wie PUL bei IM). Umsetzung: `oesg_methodik/faecher.py` (`ZUSCHNITT`, `summe_im_zuschnitt`, `zuschnitt`). Die Spalte
`Zuschnitt` der Kennzahlen sagt je Zeile, welche Spalten eingegangen sind (z. B. «AM + ZAE», «ZMK (KFO nicht getrennt
ausgewiesen)»).

**PUL und KFO sind Teilmengen, keine weiteren Fächer.** Die beiden Unterzeilen stehen auf S.37 als «- davon …»: ihre
ÄAVE sind in IM bzw. ZMK schon enthalten. Eine Summe über alle 17 Kennzahl-Zeilen zählt sie doppelt. Eine
ausdrückliche Regel zu Summen über Fächer steht weder im Textband noch im Methodenband; die Planungsgrundlagenmatrix
des ÖSG (Tabellenband, Anhang 5, S.15–60, «Ambulante ärztliche Versorgung») zeigt aber, wie der ÖSG zählt:

- KFO gehört zu ZMK: Fußnote 5 «ZMK inkl. Dr.med.dent, Dentisten und KFO»; KFO steht daneben als eigene Spalte.
- Die Spalte «insg.» der Zeile «Summe ÄAVE im ambulanten Bereich (exkl. WÄ)» ist die Summe der Fachspalten **ohne**
  KFO (Österreich S.15: Summe mit KFO 14.728,4, ohne KFO 14.518,4 = «insg.»).
- IM und PUL sind dort getrennte Spalten und gehen beide in «insg.» ein; IM enthält dort also PUL nicht. Das ist
  derselbe Zuschnitt wie in der RSG-Planungsmatrix und der Grund für IM = IM + PUL.
- Ebenso dort Fußnote 3 «CH inkl. KJC und PCH» (KJC und PCH ohne Werte) – wie CH = CH + KJC + PCH hier.

Die RSG-Verordnungen selbst sagen nichts zu Summen über Fächer; ihre Spalte «gesamt» ist die Zeilensumme der
Matrixspalten, in der jede ÄAVE einmal vorkommt (KFO als eigene Spalte neben ZMK, wo es sie gibt).

**KJC und PCH ohne eigene ÄAVE.** In allen Ländern stehen bei KJC und PCH in jeder ÄAVE-Zeile 0 bzw. «-»; Werte gibt es
nur bei Planstellen und Sachleistungsstellen, wie im Tabellenband S.232 beschrieben. Die Summe CH + KJC + PCH ändert
heute also nichts. Sie sichert den Vergleich, falls ein Land KJC oder PCH doch getrennt ausweist; die Prüfung
`kjc_pch_in_ch` meldet dann eine Abweichung, und es ist zu klären, ob der Wert in CH schon enthalten ist.

**ZMK und KFO je Land.** Die Länder weisen KFO unterschiedlich aus; für ZMK nach ÖSG (ZMK inkl. KFO) muss KFO überall
genau einmal enthalten sein:

| Land | KFO in der Matrix | ZMK + KFO in der Tabelle Planungsmatrizen | Beleg |
|---|---|---|---|
| Bgld, Ktn, NÖ, Sbg, Stmk, Tirol | eigene Spalte KFO | ZMK + KFO | Matrix |
| Wien | keine Spalte, in ZMK enthalten | ZMK | Fußnote (5): «ZMK einschließlich 54 SLS KFO» (Anlage S.33–36) |
| Vorarlberg | keine Spalte, in ZMK enthalten | ZMK | Textteil S.4: «Zahn-, Mund- und Kieferheilkunde (ZMK; einschließlich Kieferorthopädie, KFO)» |
| **OÖ** | keine Spalte, **nicht** in ZMK; nur in der Fußnote zu «ZMK*» | ZMK + KFO aus der Fußnote, ÄAVE **und** Stellen (Korrekturregeln `zusatz:`/`wert:`, Art «Fußnote») | Anlage S.10 (BL), S.12–27 (VR) |

**OÖ im Detail.** Fußnote S.10: «ZMK – exkl.: zahnärztliches Notdienstzentrum Linz und eine Vorgriffstelle in Steyr;
zusätzlich KFO: IST 2022 und Plan 2030: 38,2 ÄAVE bzw. 32 vertragskieferorthopädische Planstellen SV». Je VR steht
dieselbe Angabe mit eigenen Zahlen (VR 41: 11,5 / 9; 42: 3,3 / 5; 43: 5,9 / 5; 44: 5,8 / 3; 45: 7,6 / 5; 46: 4,2 / 5;
Σ 38,3 ÄAVE / 32 Planstellen). «ZMK» und «gesamt» der Matrix enthalten KFO nicht (gesamt = Summe der Fachspalten).

So gelesen und übernommen:
- **Ein Wert für IST und PLAN:** «IST 2022 und Plan 2030: 38,2 ÄAVE» = 38,2 ÄAVE in beiden Abschnitten (KFO bleibt
  gleich). «bzw.» verbindet die beiden Größen ÄAVE und Planstellen, nicht IST und PLAN.
- **Zeilen:** KFO-Zelle in `insgesamt` und in der Zeile der Niedergelassenen (IST `niedergelassen`, PLAN
  `extramural`), «gesamt» dieser Zeilen + Wert. Annahme: KFO ist extramural mit Kassenvertrag; die Fußnote
  nennt den Sektor nicht.
- **Stellen:** Die «32 vertragskieferorthopädischen Planstellen SV» stehen seit 2026.2 ebenfalls in den Daten: im
  IST in jeder Träger-Zeile (ÖGK, SVS, BVAEB), im PLAN in den gemeinsamen Sachleistungsstellen, Maximalanteil
  vertragsärztlicher Planstellen 100 %; «gesamt» dieser Zeilen + 32.
  **Die Träger nennt die Verordnung selbst** – nicht in der Matrix-Fußnote, aber auf den Bezirksseiten derselben
  Anlage (S.13, 16, 19, 22, 25, 28): «ZMK – zuzügl. in Kieferorthopädie (KFO): *n* vertragskieferorthopädische
  Planstellen: **ÖGK, SVS, BVAEB**», für jeden der 18 Bezirke. Die Bezirkswerte ergeben je Seite genau die Zahl der
  VR-Fußnote (9, 5, 5, 3, 5, 5) und zusammen die 32 des Bundeslands (Test:
  `tests/test_fussnoten.py::test_ooe_kfo_planstellen_stehen_auf_den_bezirksseiten`). Dieselbe Zeile unterscheidet
  «zuzügl.» von «davon in Unfallchirurgie (UC)» – die Verordnung trennt also zusätzlich von enthalten.
  **Nicht aus dem Dokument** kommen zwei Punkte: die PLAN-Zuordnung zu den gemeinsamen Sachleistungsstellen, gelesen
  aus «SV» ohne Träger und aus dem Muster der sechs Länder mit eigener KFO-Spalte, die KFO dort vollständig führen
  (zusätzliche je Träger überall 0); und die 100 %, weil die Fußnote von *Planstellen* spricht und das der
  vertragsärztliche Teil der Sachleistungsstellen ist (Tabellenband S.232) – die sechs Länder drucken 75–100 %.
  Bestätigt ist beides nicht ([offene_punkte.md](offene_punkte.md)).
- **Nicht doppelt gezählt:** Dass KFO nicht schon in den gedruckten ZMK-Werten steckt, sagt die Verordnung mit
  «zusätzlich» und «zuzügl.» (siehe oben) und bestätigt der Abgleich mit dem RSG-Monitoring, das ZMK «inkl. KFO»
  führt: ÖGK-Planstellen 381 gegenüber 414, mit den 32 dann 413, wie in den anderen Ländern auf 0 bis 2 Stellen.
  Gegenprobe Wien, dessen Fußnote (5) «ZMK einschließlich 54 SLS KFO» sagt: Dort stimmen die ZMK-Planstellen ohne
  jede Ergänzung (697 gegenüber 697). Die Lage ist mit mehreren unabhängigen Indizien belegt, von denen keines für
  sich entscheidet – welches was zeigt und was nicht, steht in
  [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), «Steckt KFO schon in der gedruckten ZMK-Spalte?».
- **Nicht übernommen:** Wahlärzt:innen in KFO (nicht angegeben).
- **Nicht ergänzt:** ZMK ohne «zahnärztliches Notdienstzentrum Linz» (BL, VR 41) und ohne «eine Vorgriffstelle in
  Steyr» (BL, VR 44). Die Fußnote beziffert beides nicht, also bleibt es draußen; ZMK in OÖ ist dort minimal zu
  niedrig (eine Stelle bzw. ein Notdienst gegenüber mehreren hundert ÄAVE). Eine Vorgriffstelle wird – allgemein,
  nicht aus den Unterlagen – im Vorgriff auf eine künftige Planstelle besetzt (z. B. überlappende Praxisübergabe).
- Wirkung: OÖ ZMK BL IST 534,6 → 572,8 ÄAVE (VD 35,5 → 38,1), PLAN 606,6 → 644,8 (39,0 → 41,5); VR entsprechend.
  Bei den Stellen kommt je Träger-Zeile und in den gemeinsamen Sachleistungsstellen eine KFO-Zelle mit 32 dazu
  (BL IST ÖGK gesamt 1.520,1 → 1.552,1; PLAN gemeinsam 1.711,5 → 1.743,5).

**KFO als eigene Kennzahl:** gegen die Unterzeile «- davon mit kieferorthopädischem
Schwerpunkt» (2,8–5,1), nur wo KFO eine eigene Spalte hat oder, in OÖ, aus der Fußnote kommt; in Wien und Vorarlberg
gibt es keine KFO-Zeile, weil KFO in ZMK steckt. Lesehilfe: Das Soll-Intervall enthält Wahlärzt:innen (R1). Salzburg
weist im IST nur 0,2 ÄAVE KFO mit Kassenvertrag aus (Wahlärzt:innen 7,5), im PLAN 12,0.

### R5 – Allgemeinmedizin enthält die ZAE

**Was der ÖSG sagt.**
- Methodenband S.20: «Zur Verdeutlichung der an Bedeutung gewinnenden Funktion von Zentralen Aufnahme- und
  Erstversorgungseinheiten (ZAE) im Bereich des spitalsambulanten Leistungserbringung wurde für das Jahr 2030 das
  diesbezügliche Potenzial für ZAE-relevante spitalsambulante ÄAVE errechnet und aufgrund der Funktion
  ‹Erstversorgung auf allgemeinmedizinischem Niveau› im Fachbereich ‹Allgemeinmedizin› ergänzt».
- Textband S.39, Legende zur Richtwerttabelle: «** Im Bereich der AM inkl. ZAE (in RSG-PM: SON/IDB) und EVA in der
  Funktion von Akutordinationen».
- Vorlage der RSG-Planungsmatrix (Tabellenband S.239), Fußnote (5) an SON/IDB: «spitalsambulant = ZAE; ggf. (zzgl)
  EVA : ÄAVE IST x, PLAN x» und «extramural = sonstige/interdisziplinäre Angebote».

**Regel:** In den Kennzahlen ist **AM = Spalte AM + SON/IDB spitalsambulant** (in den
Zeilen insgesamt und spitalsambulant; extramural und pve ohne ZAE, R10). SON/IDB
extramural («sonstige/interdisziplinäre Angebote») geht nicht ein. EVA steht nach der Vorlage in AM («davon in
Akut-Ordinationen EVA», Fußnote (4)) und ist damit schon enthalten. Die Tabelle Planungsmatrizen bleibt, wie gedruckt:
Die ZAE stehen dort weiter in SON/IDB. Umsetzung: `oesg_methodik/faecher.py` (`ZAE`, `ZAE_QUELLE`),
`rsg2030/analyse_eingang.py`.

**Wo die Länder die ZAE führen** (BL-Matrix, Fußnoten im Verzeichnis `fussnoten.csv`). Wo sie nicht in SON/IDB stehen,
zeigt das RSG-Monitoring der GÖG, wo sie stecken ([PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)):
Spitalsambulant sind die IST-Werte der Verordnungen dort die Werte desselben Jahres, und das Monitoring weist die ZAE
erst ab Datenjahr 2023 getrennt aus – bis 2022 stecken sie in den Fachspalten, vor allem in IM. Zahlen in Klammern: ZAE
laut Monitoring 2023, in ÄAVE.

| Land | Fußnote (Seite) | SON/IDB spitalsambulant IST / PLAN | ZAE außerhalb von SON/IDB |
|---|---|---|---|
| Burgenland | (5) «spitalsambulant=ZAE; ggf. (zzgl) EVA:ÄAVE IST 2022, PLAN 2030» (Anlage 1 S.1) | 0 / 8,3 | IST 2022: in den Fachspalten, vor allem IM (6,7) |
| Kärnten | (4) «spitalsambulant=ZAE: Plan 2030 in ÄAVE» (Anhang S.97) | nicht ausgewiesen / 18,9 | IST 2022: in den Fachspalten, vor allem IM (18,1) |
| NÖ | (5) «spitalsambulant = ZAE; ggf. (zzgl) EVA : ÄAVE IST 0, PLAN n.v.» (Anlage S.1) | 0 / 44,6 | IST 2023: in der Spalte AM (AM spitalsambulant 44,1) |
| OÖ | «AM spitalsambulant – ÄAVE werden gemäß ÖSG Verordnung ab 2023 unter SON/IDB ausgewiesen» (Anlage S.10) | 0 / 25,1 | IST 2022: 24,4 in der Spalte AM, die übrigen in den Fachspalten (zusammen 42,5). PLAN ebenso nur zum Teil: PLAN spitalsambulant ist IST 2022 fortgeschrieben (DATEN.md, Fallstrick 8), SON/IDB 25,1 entspricht der AM-Spalte 2022 |
| Salzburg | (7) «spitalsambulant = ZAE» (Anlage S.1) | 16,8 / 17,4 | – |
| Steiermark | (5) Text der Vorlage (Anlage 1 S.1) | nur in SVE (4,4), ÄAVE-Ä «n.v.» / 26,3 | IST 2022: in den Fachspalten, vor allem IM (23,4); die SVE umgerechnet zählten doppelt (R6) |
| Tirol | (7) «spitalsambulant = ZAE, davon 4,8 VZÄ in der AM, 1 VZÄ in der KIJU und 2,25 VZÄ in der ORTR …» (Anlage S.1) | 14,1 / 16,3 | – |
| Vorarlberg | (5) Text der Vorlage (Anlage S.1) | nicht ausgewiesen / 0 | IST 2023: keine ZAE laut Monitoring. PLAN: in der Spalte AM (der Textteil zählt die ZAE zur AM, S.15; AM spitalsambulant 9,0) |
| Wien | (4) «spitalsambulant = ZAE (ca. 130 VZÄ im SOLL aus den verschiedenen Fächern (AM, IM))» (Anlage S.33) | 0 / 0 | IST 2022 und PLAN: in den Fachspalten, vor allem IM (88,1). PLAN (AM 15, IM 374) baut auf IST 2022 auf: Die «ca. 130 VZÄ» sind in den Fachspalten enthalten, nicht zusätzlich |

**Was das heißt.**
- Wo die ZAE in SON/IDB stehen, enthält die AM-Kennzahl sie jetzt, wie der Richtwert. Wirkung auf die VD AM im PLAN
  (BL): Burgenland 61,9 → 64,6; Kärnten 47,8 → 51,2; NÖ 47,5 → 50,0; OÖ 51,7 → 53,3; Salzburg 48,4 → 51,4;
  Steiermark 49,3 → 51,4; Tirol 49,2 → 51,3. Im IST: Salzburg 44,7 → 47,6; Tirol 46,2 → 48,1. In NÖ und OÖ sähe der
  Schritt IST → PLAN ohne diese Regel zu klein aus, weil die ZAE im IST in der Spalte AM stehen, im PLAN in SON/IDB
  (NÖ 47,1 → 47,5 statt → 50,0).
- **Wo die ZAE in den Fachspalten stecken** (`Zuschnitt` «AM (ZAE nicht getrennt ausgewiesen)»), ist AM zu niedrig und
  IM zu hoch gegenüber dem ÖSG-Zuschnitt: Für die Richtwerte hat der ÖSG die ZAE-ÄAVE «aus den in Regiomed zugewiesenen
  Fachbereichen herausgelöst» – «vorrangig ‹Innere Medizin›», deren ÄAVE «entsprechend reduziert» wurden – und der AM
  zugerechnet (*Methodenband S.20*). In Wien geht es um rund 90 ÄAVE (Wien-IM über dem Soll-Intervall liegt zum Teil
  daran). Im Schritt IST → PLAN ist ein Teil des AM-Anstiegs und des IM-Rückgangs nur diese Umbuchung (Burgenland IM
  26,6 → 20,7, Kärnten 75,4 → 69,6). Die Werte bleiben, wie gedruckt; das Monitoring dient nur als Beleg.
- **Tirol** nennt in der Fußnote zur ZAE «davon 4,8 VZÄ in der AM, 1 VZÄ in der KIJU und 2,25 VZÄ in der ORTR durch L-ZK
  als zusätzliche SLS der SV anrechenbar» (Anlage S.1; je VR eigene Zahlen). Das betrifft die Anrechnung von Ärzt:innen
  der ZAE als Sachleistungsstellen, keine Aufteilung der ZAE-ÄAVE auf Fächer: VZÄ sind Personal, keine ÄAVE, und die
  genannten 8,05 VZÄ sind nur ein Teil der ZAE (IST 14,1, PLAN 16,3 ÄAVE). Die ZAE gehen nach Textband S.39 ganz in AM;
  KIJU und ORTR bleiben, wie gedruckt. Das ist unsere Lesart, nicht bestätigt (Rückfrage,
  [offene_punkte.md](offene_punkte.md#unklare-angaben-in-den-verordnungen)): Wären die VZÄ als Anteil der ZAE-Versorgung
  je Fach gemeint, gehörten in Tirol BL etwa 1 ÄAVE zu KIJU (67,2) und 2,25 zu ORTR (75,6) statt zu AM (370,8 IST) – je
  Fach rund 1–3 %.

### R6 – SVE-Länder: ÄAVE-Äquivalente verwenden

Wer mit SVE plant, muss die Werte je Fach auf ÄAVE umrechnen (Textband S.37, S.78). In RSG 2030 betrifft das
Burgenland, Kärnten, Steiermark: Block `aequivalent` der Tabelle Planungsmatrizen. Umsetzung: `rsg2030/schema.py`
(`massgeblicher_block`, `bl_long`, `matrix_long`), abgeleitet aus den Daten.

**Was SVE und ÄAVE sind.** ÄAVE messen die Versorgungswirksamkeit im Verhältnis zu einem «durchschnittlich
arbeitenden Arzt» (DAA): dem Durchschnitt der Vertragsärzt:innen eines Fachs mit Einzelpraxis, ganzjährigem kurativem
Vertrag, mindestens einer kurativen Konsultation pro Quartal und Vertrag mindestens mit der ÖGK, um statistische
Ausreißer bereinigt (*Methodenband S.17*, «neue Regiomed-Methode»). SVE legt der ÖSG nicht fest: «alternative
Planungsgrößen, die ggf. in den RSG anstatt ÄAVE verwendet und definiert werden» (*Tabellenband S.249*). Nur Kärnten
beschreibt seine: Bezugsgröße ist die durchschnittliche Versorgungswirksamkeit einer ganzjährigen
Kassen-Einzelordination des Fachs, gemessen in Kontakten, um Ausreißer bereinigt; «Sowohl eine SVE als auch eine ÄAVE
entsprechen grundsätzlich einem durchschnittlich arbeitenden Arzt bzw. Ärztin». SVE werden nur für die
Spitalsambulanzen verwendet, extramural gelten die ÄAVE aus Regiomed; umgerechnet wird «je Versorgungsregion»: «SVE
2030 × Umrechnungsfaktor 2022 = ÄAVE-Ä 2030» (*Kärnten Anhang S.30*). Burgenland und Steiermark definieren SVE nicht;
ihre Matrizen sind gleich aufgebaut (SVE nur spitalsambulant, Faktoren je Region und Fach).

**Was der ÖSG verlangt** (*Tabellenband S.234*). Wer statt ÄAVE andere Planungsgrößen verwendet, gibt «je Sektor und je
Fachrichtung für die IST-Werte einen Umrechnungsschlüssel» an; «unter Anwendung dieser Umrechnungsfaktoren sind für die
PLAN-Werte ÄAVE-Äquivalente als Näherungswerte für den Vergleich mit den ÖSG-Planungsrichtwerten auszuweisen». Laut
Vorlage (Tabellenband S.239) gibt es keinen Faktor für RAD, NUK, PMR, PAT, LAB («n.v.»). Was ein Faktor ist, sagt die Steiermark im
Glossar ihrer Anlage 1 (S.65): «Bei den spitalsambulanten ÄrztInnen basiert der Faktor auf dem Verhältnis der für die
RSG-Planung pro Fach ermittelten SVE zu den in Regiomed ausgewiesenen ÄAVE im selben Bundesland und Datenjahr.»
Extramural sind SVE und ÄAVE «weitgehend methodisch angepasst», der Faktor ist dort 1 bzw. nicht angegeben («-»).

**Was die Kennzahlen nehmen.** Die **ÄAVE-Äquivalente, wie sie im PDF stehen** – nicht SVE × Faktor. Das gilt auch, wo
SVE und Faktor gedruckt sind, die ÄAVE-Ä aber «n.v.»: Steiermark IST SON/IDB (ZAE). Die IST-ÄAVE-Ä sind Regiomed 2022,
und dort stecken die ZAE noch in den Fachspalten (R5); umgerechnet zählten sie doppelt. Die Umrechnungsfaktoren stehen
in der Tabelle Planungsmatrizen (Zeilen `umr_*`).

**Wie geprüft wird.** Die Prüfung `faktor_aequivalente` rechnet den ganzen ÄAVE-Ä-Block nach: ÄAVE-Ä = Wert im Block
`haupt` × Faktor seines Sektors, in IST und PLAN; Zeilen ohne Faktor (schon in ÄAVE) müssen in beiden Blöcken gleich
sein. Haben alle Regionen eigene Faktoren, ist das Bundesland die Summe der umgerechneten Regionen – das Verhältnis
ÄAVE-Ä ÷ SVE auf BL-Ebene verschiebt sich dann mit dem Mix der Regionen und passt nicht zum BL-Faktor (Kärnten PLAN
CH: 10,2 × 3,06 + 4,9 × 1,81 = 40,04, nicht 15,1 × 2,67 = 40,3). Die BL-Ebene prüft dann «Σ VR = BL» – und im
Abschnitt, in dem der BL-Faktor steht, zusätzlich den BL-Faktor selbst (nächster Absatz).

**Warum es den BL-Faktor trotzdem gibt.** Er ist die Pflichtangabe des ÖSG, «auf Ebene des Bundeslandes … für die
IST-Werte» (S.254). Für IST ist er exakt – das Verhältnis ÄAVE-Ä ÷ SVE des Landes, also das mit den IST-SVE gewichtete
Mittel der Regionsfaktoren (Burgenland und Kärnten: SVE × BL-Faktor = ÄAVE-Ä in jedem Fach; die Steiermark ebenso im
PLAN, wo ihr BL-Faktor steht – geprüft von `faktor_aequivalente`). Für PLAN nennt der ÖSG die
Umrechnung selbst einen «Näherungswert»; die Länder rechnen genauer, Region für Region, und weichen deshalb auf BL-Ebene
leicht vom BL-Faktor ab.

Die drei Länder geben die Faktoren unterschiedlich an – Abschnitt laut Überschrift der Faktoren, nachgerechnet
(spitalsambulant, je Fach):

| Land | Überschrift | passt zu | Lesart |
|---|---|---|---|
| Burgenland | «… IST 2022» | IST und PLAN, außer PLAN IM (VR 11, VR 12) und AU | PLAN IM mit anderen, nicht gedruckten Faktoren gerechnet; AU hat nur einen BL-Faktor, der nicht passt – entgegen S.254 (bekannte Abweichung, Rückfrage) |
| Kärnten | BL «IST 2022», VR 21 «IST 2022 und 2030» | IST und PLAN | ein Faktor je Fach und Region für beide Jahre; BL = Summe der Regionen |
| Steiermark, Versorgungsregionen | «… IST 2022» | IST und PLAN | ein Faktor je Fach und Region für beide Jahre |
| Steiermark, Bundesland | «… **PLAN 2030**» | nur PLAN | der BL-Faktor ist das Verhältnis ÄAVE-Ä ÷ SVE der PLAN-Werte des Landes, also das mit den PLAN-SVE gewichtete Mittel der VR-Faktoren; im IST passt er deshalb nicht. Die BL-Äquivalente im IST sind die Summe der Regionen (geprüft) |

Die Steiermark zeigt auf der BL-Seite also den PLAN-Faktor, entgegen dem Wortlaut «für die IST-Werte» (S.254) –
inhaltlich dieselbe Rechnung; warum, sagt die Verordnung nicht.

### R7 – Bevölkerung: Wohnbevölkerung zum 1.1.

Ziel: **dieselbe Bevölkerungsbasis wie der ÖSG**, weil die VD an den Versorgungsdichte-Soll-Intervallen des ÖSG gemessen
wird.

**Was der ÖSG sagt**

- Wohnbevölkerung 2021 = 8.932.664 (ohne Wien 7.011.715), 2030 = 9.347.316 (ohne Wien 7.282.458); Quellen
  Statistik Austria, Bevölkerungsstatistik 2021 und Bevölkerungsprognose «Aktualisierung November 2022».
  *Textband S.39.* Beides sind Stände zum 1.1. (der Wert 2030 steht in Statistik Austria, Statistische Nachrichten
  1/2023, Tabelle 9 «Bevölkerung zum 01.01.»).
- Kleinräumig: «… für Jahre ohne aktualisierte kleinräumige ÖROK-Prognose wird die Grobabschätzung der
  Bevölkerungsentwicklung auf Gemeindeebene durch ein GÖG-eigenes Näherungsverfahren berechnet (dabei wird die
  jeweils aktuelle Bevölkerungsprognose der Statistik Austria auf Bundesländer-Ebene unter Heranziehung aktuellen
  ÖROK-Prognose auf kleinräumige Gliederungsebenen hinunter projiziert)»; dieselbe Fußnote: «verwendet werden
  Jahresenddaten». *Methodenband S.13, Fußnote \*\*\*\*\**
- Methodenband, Textband und Tabellenband beschreiben das Verfahren nur im Prinzip. Welche Rechenschritte es genau
  hat, steht dort nicht. Eine Veröffentlichung an anderer Stelle haben wir nicht gesucht.

**Was hier gemacht wird**

| | Quelle | Verhältnis zum ÖSG |
|---|---|---|
| IST, BL und VR | Statistik Austria Open Data, «Bevölkerungsstand zu Jahresbeginn» (`OGD_bevstandjbab2002_BevStand_<Jahr>`, je Gemeinde; Bezirk = erste drei Stellen der Gemeindekennziffer, Wien: Gemeindebezirke), 1.1. des IST-Jahres der jeweiligen Matrix; VR = Summe ihrer Bezirke laut `oesg_methodik/referenz/oesg_regionen.csv` | **gleich:** 1.1.2021 ergibt genau 8.932.664 bzw. 7.011.715 (Test) |
| PLAN 2030, BL | Statistik Austria Open Data, **Bevölkerungsprognose 2025**, Hauptszenario, «Bevölkerung zum Jahresanfang» 2030 (`OGD_bevjahresanf_PR_BEVJA_10`), Summe über Alter und Geschlecht | **Abweichung:** neuere Prognose als im ÖSG (siehe unten) |
| PLAN 2030, VR | Anteil der VR an ihrem Land 2030 laut **ÖROK-Prognose 2021** × BL-Wert 2030 | **gleiches Prinzip** wie Methodenband S.13; VR summieren sich genau zum BL |

**Warum für PLAN BL nicht die ÖSG-Prognose (November 2022)?** Seither sind neuere Prognosen erschienen; verwendet wird
die neueste. Die Werte je Bundesland zum 1.1.2030 aus der Prognose 2022 haben wir außerdem nicht frei zugänglich
gefunden: Im Bericht ([Statistische Nachrichten
1/2023](https://www.statistik.at/fileadmin/pages/414/Bev_BPR2022_01_2023_Teil_1.pdf), Tabelle 7) stehen je Land nur
Jahresdurchschnitte, zum 1.1. nur der Österreich-Wert (Tabelle 9). Ob eine kostenpflichtige Publikation sie enthält,
haben wir nicht geprüft. Unterschied für Österreich:

| 1.1.2030 | Prognose 2025 (verwendet) | Prognose 2022 (ÖSG) | Abweichung |
|---|---:|---:|---:|
| Österreich | 9.321.070 (Test) | 9.347.316 (Textband S.39) | −0,28 % |

Begründung: Die Soll-Intervalle sind Dichten. Für «liegt die Planung 2030 im Soll-Intervall?» ist die neueste Prognose
die beste Schätzung der Bevölkerung 2030.

**Prognose-Jahrgang je Datenversion.** Statistik Austria veröffentlicht die Bevölkerungsprognose jährlich, zuletzt im
November (Prognose 2025: 10.–12.11.2025). Ein neuer Jahrgang erscheint im Open-Data-Portal vermutlich als neuer
Datensatz (die Reihe «Bevölkerung zum Jahresanfang» hatte schon die Nummern 1 bis 8, heute 10); denkbar ist auch, dass
die bestehende Datei ersetzt wird. Festlegung:
- Eine Datenversion verwendet **genau einen Prognose-Jahrgang** – heute die Prognose 2025. Welcher, legt das Register
  fest (Adresse und Prüfsumme); wird die Datei online ersetzt, lädt `download` die geprüfte Fassung aus dem Archiv.
- Der Code nimmt das Hauptszenario der registrierten Datei (Spalte `F-S..V1`, die Zahl ist der Jahrgang) und nennt den
  Jahrgang im Log und im Laufprotokoll (`Prognose_Jahrgang`).
- Ein neuer Jahrgang ist eine **Datenänderung**: neue Version mit CHANGELOG-Eintrag (Wirkung auf Bevölkerung und
  Kennzahlen je Land). Erscheint der neue Jahrgang unter neuer Adresse, erkennt das kein Wächter – deshalb steht der
  Termin in PIPELINE.md («Termine, die kein Wächter erkennt»); wird die Datei unter derselben Adresse ersetzt, meldet
  es die monatliche Quellen-Prüfung des Wächters.
- Wer die Daten verwendet, nennt die Version ([CITATION.cff](../CITATION.cff)); ein neuer Jahrgang kommt erst mit einer
  neuen Version.

**Aufteilung auf die Versorgungsregionen.** Umgesetzt ist die direkte Lesart des Methodenbands:

```
Bevölkerung VR 2030 = Anteil der VR an ihrem Land 2030 laut ÖROK × Bevölkerung Land 2030 laut Statistik Austria
```

Die ÖROK-Prognose (121 Prognoseregionen) wird über die Bezirks-Gesamtzeilen auf Bezirke zurückgeführt (geteilte
Bezirke nicht doppelt; «Eisenstadt-Umgebung / Rust» liegt vollständig in VR 11).

Von der ÖROK-Prognose werden **nur die Anteile** der Regionen an ihrem Land verwendet, nicht ihre absoluten Zahlen. Das
ist wichtig, weil die ÖROK selbst darauf hinweist, «dass die Ergebnisse der ÖROK-Prognose nicht kohärent sind mit der
jährlichen Prognose von STATISTIK AUSTRIA für Österreich und die Bundesländer» (ÖROK, Seite «ÖROK-Bevölkerungsprognose
2021», Anmerkungen zur Methodik). Die Landessumme kommt deshalb immer aus der Prognose von Statistik Austria.

**Was die Länder in ihren RSG 2030 angeben** (soweit veröffentlicht):

| Land | Bevölkerung 2030 | Quelle laut RSG |
|---|---|---|
| Kärnten | 559.783 (VR 21: 339.930; VR 22: 219.853) | ÖROK-Prognose 2021 über die Landesstatistik (Anhang, S.19 und S.26) |
| Vorarlberg | 421.445 (VR 81: 238.456; VR 82: 182.989) | Statistik Austria + ÖROK (Textteil, S.5–6); VR-Aufteilung = ÖROK-Anteil wie hier |
| Tirol | – | «Bevölkerungsprognosen 2030 der Statistik Austria und der ÖROK» (Erläuternde Bemerkungen, S.5) |
| übrige Länder | – | in den veröffentlichten Unterlagen nicht angegeben |

Die Länder verwenden also dieselbe Logik (Statistik Austria + ÖROK), aber unterschiedliche Prognosejahrgänge; für
einen einheitlichen Vergleich aller neun Länder wird eine gemeinsame Basis verwendet.

Code: `oesg_methodik/bevoelkerung.py` (`bevoelkerung_fuer`, `bevoelkerung_bl_ist`, `bevoelkerung_prognose`,
`bevoelkerung_vr`).

### R8 – ÄAVE-Methode je Datenjahr

| Datenjahr | Methode | Quelle |
|---|---|---|
| bis 2020 | «Regiomed-alt»: DAA aus Ärzt:innen mit Vertrag mit allen Kassen, ≥ 1 Konsultation pro Jahr, keine Ausreißer-Bereinigung | Methodenband S.17 |
| 2021, 2022 | «Regiomed-neu»: Vertrag mindestens mit ÖGK, ≥ 1 Konsultation pro Quartal, Ausreißer-Bereinigung; DAA jährlich | Methodenband S.17–18 |
| ab 2023 | wie neu, aber im niedergelassenen Kassenbereich fest der **DAA 2022**; Aktualisierung in fünf Jahren geplant | Methodenband S.18 |

Für RSG 2030 hieße das: Die IST-Jahre 2022 und 2023 beruhen beide auf «Regiomed-neu», 2023 mit dem festen DAA 2022; die
Soll-Intervalle beruhen auf 2021, ebenfalls «neu». **Die Daten zeigen aber unterschiedliche DAA-Stände bei den
niedergelassenen ÄAVE:** Gegen das RSG-Monitoring, das laut S.18 beide Jahre mit dem DAA 2022 rechnet, liegen die
Verordnungen je Fach und IST-Jahr in allen Ländern um praktisch denselben Anteil höher – mit anderen Anteilen für IST
2022 und IST 2023, und in OÖ rund 5 Prozentpunkte mehr als in den übrigen Ländern mit IST 2022
([PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)). Spitalsambulant, Ambulatorien und Wahlärzt:innen sind
nicht betroffen. Wahrscheinlich sind die niedergelassenen ÄAVE also je IST-Jahr und in OÖ mit einem anderen DAA
gerechnet; bestätigt ist das nicht (Bekannte Grenzen 4).

**Wahlärzt:innen:** Ihre ÄAVE beruhen auf den bei der Kasse eingereichten Rechnungen (Kostenerstattung) und werden
ebenfalls über den DAA umgerechnet. Das ist eine fachliche Auskunft (nicht veröffentlicht); der Methodenband nennt
den Wahlarztbereich in diesem Zusammenhang nicht ausdrücklich.

### R9 – Versorgungsaufträge nur für die Sachleistung

Versorgungsaufträge gibt es nur für Kassenärzt:innen, Ambulatorien mit Kassenvertrag, Kassenambulatorien und
Spitalsambulanzen von Fonds-KA/UKH; Wahlärzt:innen und Ambulatorien ohne Kassenvertrag nicht (Textband S.78).
Ihre Versorgungswirksamkeit ist «als Rahmenbedingung» mitzuberücksichtigen (Textband S.15).

### R10 – Teilzeilen: spitalsambulant, extramural, PVE

**Was der ÖSG sagt.**
- Die Matrix gliedert die ÄAVE im IST nach spitalsambulant, niedergelassen, selbständige Ambulatorien,
  Kassenambulatorien und insgesamt, dazu die Teilmengen VGF und PVE (Tabellenband S.231); im PLAN nach spitalsambulant,
  «niedergelassenen ÄrztInnen (mit Kassenvertrag) und in selbständigen Ambulatorien tätigen ÄrztInnen … gesamt» und
  insgesamt (S.252). In beiden Abschnitten gibt es also spitalsambulant, extramural (im IST die Summe der drei
  extramuralen Zeilen, [DATEN.md](DATEN.md#zeilen)) und insgesamt.
- PVE: «In der Allgemeinmedizin (AM) und der Kinder- und Jugendheilkunde (KIJU) ist im IST-Stand … und im PLAN-Stand …
  die tatsächliche (IST-Stand) bzw. die Mindestanzahl (PLAN-Stand) der ÄAVE … in Primärversorgungseinheiten (PVE)
  auszuweisen» (S.251).
- ZAE sind spitalsambulant: Vorlage (Tabellenband S.239), Fußnote (5) «spitalsambulant = ZAE».
- Die Soll-Intervalle sind «Planungsrichtwerte für den gesamten ambulanten Bereich» (Textband S.39), berechnet aus den
  ÄAVE «im gesamten ambulanten Versorgungsbereich» (S.36). Für einzelne Sektoren oder für PVE gibt es keinen Richtwert.

**Regel:** Die Tabelle Versorgungsdichte enthält je Region, Abschnitt und Fach die Zeilen
**spitalsambulant, extramural, insgesamt** und, nur für AM und KIJU, **pve** – alle im Zuschnitt von R4:
- Die ZAE gehören zu spitalsambulant und damit zu insgesamt, nicht zu extramural oder pve. AM spitalsambulant =
  Spalte AM + SON/IDB spitalsambulant; AM extramural und AM pve = Spalte AM. So gilt auch im Zuschnitt
  spitalsambulant + extramural = insgesamt (Test).
- Ist die AM-Zelle spitalsambulant leer gedruckt, die ZAE aber nicht (Burgenland VR 11 und 12, PLAN), ist AM
  spitalsambulant = ZAE.
- VD für jede Zeile, **Soll-Intervall nur bei insgesamt**.
- PLAN pve ist ein **Mindestwert**; IST pve ist eine Teilmenge der VGF, PLAN pve eine Teilmenge von insgesamt.

Nicht aufgenommen: die IST-Teilzeilen niedergelassen, selbständige Ambulatorien und Kassenambulatorien (nur IST;
extramural fasst sie zusammen), VGF (im PLAN nur in OÖ und der Steiermark), Wahlärzt:innen (R1) und die Stellen
(nächster Abschnitt). Sie bleiben in der Tabelle Planungsmatrizen. Umsetzung: `oesg_methodik/eingang.py` (`ZEILEN`,
`PVE_FAECHER`), `oesg_methodik/faecher.py` (`ZAE_ZEILEN`, `teile`), `oesg_methodik/dichte.py`.

### Stellen – nicht in der Tabelle Versorgungsdichte

**Was der ÖSG sagt.** IST: «Anzahl der vertragsärztlichen Planstellen je KV-Träger» (Tabellenband S.231). PLAN:
Sachleistungsstellen, «Planstellen für niedergelassene VertragsärztInnen und der geplanten ärztlichen
Vollzeitäquivalente in Ambulatorien», «für gemeinsame Sachleistungsstellen aller KV-Träger und für die zusätzlichen
Sachleistungsstellen einzelner KV-Träger. Davon ist jeweils der Maximalanteil für vertragsärztliche Planstellen in
Prozent auszuweisen» (S.252). Als endgültig sieht der ÖSG das nicht: In der Liste der Matrix-Inhalte spricht er
vom «Vorliegen einer detaillierten Definition von Sachleistungsstellen» als etwas Künftigem (Textband S.76, bei der
optionalen Zeile «ÄAVE gesamt»).

**Was die Länder dazu sagen.**
- Steiermark, Glossar (Anlage 1 S.65): vertragsärztliche Planstellen sind «Planstellen des jeweiligen
  Krankenversicherungsträgers …, die Werte dürfen nicht addiert werden»; Sachleistungsstellen «entspricht der Summe von
  Planstellen des niedergelassenen Bereichs und der VZÄ in selbständige Ambulatorien mit Kassenvertrag und kasseneigene
  Ambulatorien; Zuordnung zu KV-Träger(n) abhängig von Zugänglichkeit für Versicherte des/der KV-Träger».
- Tirol (Erläuternde Bemerkungen S.8): neue Sachleistungsstellen und unbesetzte Planstellen werden «dem IST 2023
  addiert, um einen vollständigen PLAN 2030 zu erhalten». Die Steiermark (Erläuterungen S.5): AM-Planstellen sollen
  «auf 614 Sachleistungsstellen angehoben werden» (IST 603 ÖGK-Planstellen).
- Wien (Textteil S.19): Zusätzliche Sachleistungsstellen werden nach ihrer Versorgungswirksamkeit bewertet
  (Quartalserstpatient:innen je Stelle, «Aufwertungsfaktor» für PVE). Eine Wiener Sachleistungsstelle ist also nicht
  unbedingt eine Stelle im Sinn einer IST-Planstelle.
- Burgenland, Salzburg, Tirol (Fußnote an den technischen Fächern): «Für Ambulatorien können derzeit keine
  Sachleistungsstellen ausgewiesen werden.»

**Lesart je Träger.** Gemeinsame Stellen stehen den Versicherten aller Träger offen, zusätzliche nur denen eines
Trägers (Glossar Steiermark). PLAN je Träger wäre dann gemeinsam + zusätzlich, verglichen mit den IST-Planstellen
desselben Trägers. Die Daten stützen das: Die zusätzlichen ÖGK-Sachleistungsstellen sind in allen Matrizen 0 oder «-»,
und IST SVS minus IST ÖGK ist ungefähr die Zahl der zusätzlichen SVS-Stellen im PLAN (AM, Bundesland):

| Land | IST SVS − ÖGK | PLAN zus. SVS | IST BVAEB − ÖGK | PLAN zus. BVAEB |
|---|---:|---:|---:|---:|
| Burgenland | 3 | 3 | 1 | 1 |
| Kärnten | 10 | 10 | 8 | 8 |
| NÖ | 22 | 20 | 7 | 7 |
| Steiermark | 17 | 19 | 6 | 6 |
| Tirol | 20 | 22 | 13 | 13 |
| Wien | 29 | 33 | 13 | 13 |

Das ist eine Beobachtung, keine Regel aus dem ÖSG.

**Entscheidung: keine Stellen in der Tabelle Versorgungsdichte.** Ein Vergleich IST → PLAN braucht mehrere Annahmen:
die Lesart je Träger; dass Sachleistungsstellen (mit Ambulatorien-VZÄ, in Wien bewertet) mit Planstellen vergleichbar
sind; dass die Obergrenze für Kassenpraxen (Stellen × Maximalanteil, je Zeile und Fach, erst danach summiert) ein Plan
ist; dass die IST-Planstellen unbesetzte Stellen enthalten. Das ist eine Auswertung, keine Lesung. Die Stellen bleiben
in der Tabelle Planungsmatrizen; wie man sie liest: [DATEN.md](DATEN.md#stellen-lesen).

---

## Wie die Kennzahlen entstehen

```
Tabelle Planungsmatrizen ─ ÄAVE-Zeilen spitalsambulant, extramural, insgesamt, pve; ÖSG-Fächerzuschnitt (R2, R4–R6, R10) ─→ ÄAVE-Eingang
                         ─ + Bevölkerung (R7) ─→ VD = ÄAVE ÷ Bevölkerung × 100.000
                         ─ + Richtwerte (R3, Textband S.39), nur Zeile insgesamt ─→ Lage, Position, ÄAVE-Abstand
```

1. **ÄAVE-Eingang** (`rsg2030/analyse_eingang.py` → Vertrag `oesg_methodik/eingang.py`): eine Zeile je Region ×
   Abschnitt × Jahr × Zeile × Fach, Basis `Sachleistung`, mit `Zuschnitt`. Der Vertrag lehnt unbekannte Zeilen, Fächer,
   Ebenen, Basen, PVE außerhalb von AM und KIJU, leere Werte und doppelte Schlüssel ab; die Zeilen müssen in ÄAVE sein
   (SVE-Länder: Block der Äquivalente, R6).
2. **Bevölkerung** (`oesg_methodik/bevoelkerung.bevoelkerung_fuer`): je Region nach R7, für alle Zeilen gleich.
3. **VD, Lage, Position und ÄAVE-Abstand zum Soll-Intervall** (`oesg_methodik/dichte.kennzahlen`), Richtwerte aus
   `oesg_methodik/referenz/oesg_planungsrichtwerte.csv` (aus Textband S.39; `tests/test_referenz.py` prüft jeden Wert
   am PDF).

Fehlt ein Wert, bleibt die Zeile weg und wird nicht geschätzt. Spalten:
[DATEN.md](DATEN.md#rsg_2030_versorgungsdichtecsv).

---

## Bekannte Grenzen und offene Fragen

1. **Wahlärzt:innen im PLAN:** Die PLAN-ÄAVE enthalten sie nach ÖSG nicht (R1). Eine VD «nach ÖSG-Definition» für 2030
   bräuchte eine Annahme (z. B. IST-Wahlärzt:innen mit gleicher Zahl oder gleicher Dichte fortschreiben). Bewusst
   nicht Teil der Kennzahlen; das ist Sache einer Analyse.
2. **«Abrechnungsrelevante» Wahlärzt:innen:** Die Matrixzeile umfasst «Wahlärzt:innen und selbständige Ambulatorien ohne
   Kassenvertrag». Ob das genau den «abrechnungsrelevanten» Wahlärzt:innen aus R1 entspricht, ist offen.
3. **ZAE:** In den Kennzahlen zu AM gezählt, wo sie in SON/IDB stehen (R5). Wo ein Land sie nicht getrennt ausweist
   (Wien; IST 2022 mehrerer Länder), stecken sie in den Fachspalten, vor allem IM – AM ist dort zu niedrig, IM zu hoch,
   nicht bezifferbar aus der Verordnung (R5; Spalte `Zuschnitt`: «AM (ZAE nicht getrennt ausgewiesen)»).
4. **DAA-Stand der niedergelassenen ÄAVE** (R8): Zwischen den Ländern mit IST 2022 und IST 2023 und für OÖ
   wahrscheinlich verschieden – je Fach um bis zu rund 7 Prozentpunkte. Niedergelassene ÄAVE (und damit «insgesamt»)
   zwischen diesen Gruppen nur mit Vorsicht vergleichen; welcher Stand zu den Soll-Intervallen (Regiomed 2021) passt,
   ist offen.
5. **Quellen ändern sich online:** Statistik Austria ersetzt Dateien unter derselben URL (z. B. «Bevölkerung zu
   Jahresbeginn», «erstellt am 29.06.2026»). Dann weicht die Prüfsumme ab und das Register ist bewusst nachzuziehen –
   samt neuer Version, falls sich Kennzahlen ändern. Der jüngste Stichtag einer Zeitreihe kann «vorläufig» sein.
6. **Austauschbeziehungen** (R3): Der ÖSG will die Lage «unter Berücksichtigung von regionalen
   Austauschbeziehungen» bewertet sehen (Textband S.38). Patientenströme stecken nicht in den Kennzahlen; dafür
   bräuchte es eigene Daten. Lage, Position und ÄAVE-Abstand sind deshalb ein erster Blick, keine Bewertung im Sinn des
   ÖSG ([DATEN.md](DATEN.md#fallstricke), Fallstrick 11).

---

## Pflege

- Neue ÖSG-Erkenntnis oder Entscheidung → hier eintragen, mit Dokument und Seite, im selben Commit wie die
  Code-Änderung.
- Neue Spalte oder Zeile in den Daten → in [DATEN.md](DATEN.md) beschreiben.
- Was eine Analyse aus den Kennzahlen auswählt oder zusätzlich rechnet, gehört in die Methodik der Analyse, nicht hier.
