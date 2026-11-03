# Webseite

Eine Webseite zeigt die Tabelle Versorgungsdichte (`RSG_2030_Versorgungsdichte.csv`) zum Nachsehen: je
Versorgungsregion und Fach, ob die Sachleistung unter, im oder über dem Versorgungsdichte-Soll-Intervall (ÖSG) liegt.
Sie ist eine **Darstellung der Tabelle mit Lesehilfen**: Die Werte stehen unverändert in der Tabelle; Farbstufen,
Schraffur, Anteilsbalken, die Sätze in Worten und die Vorbehaltstexte sind Festlegungen der Darstellung, hier
begründet («Darstellungsregeln», «Entscheidungen»). Die Vorbehalte kommen aus [DATEN.md](DATEN.md#fallstricke) und
urteilen nicht über sie hinaus. Anders als die Excel-Mappe, die die Matrizen so zeigt, wie sie gedruckt sind, liest die
Seite die Zahlen also vor.

Zu jedem gezeigten Wert sagt sie außerdem, **woher er kommt**: PDF, Seite, Zeile und Spalten der Matrix, der Text wie
gedruckt und, wo korrigiert wurde, die Regel mit Begründung. Dieser Teil **zitiert** die Tabelle Planungsmatrizen und
`korrekturen.csv` – er formuliert nichts um und rechnet nichts nach.

**Veröffentlicht unter <https://maxpli.github.io/rsg-2030-verordnungen/>**, mit den Daten des aktuellen Release.
Offene Punkte stehen in [offene_punkte.md](offene_punkte.md#webseite).

---

## Was die Seite zeigt

Zeile `insgesamt` der Tabelle Versorgungsdichte, umschaltbar zwischen IST und PLAN 2030 und zwischen
Versorgungsregionen und Bundesländern.

| Teil | Inhalt |
|---|---|
| Anteilsbalken | wie viele Zellen der Matrix unter, im und über dem Soll-Intervall liegen; Fälle unter 1 ÄAVE Abstand schraffiert |
| Matrix | Regionen × Fächer, Farbe = Lage zum Soll-Intervall |
| Detailspalte | eine Region und ein Fach: VD, ÄAVE, Bevölkerung, Lage, Position und ÄAVE-Abstand für IST und PLAN, ein Satz in Worten («Bis zur Untergrenze fehlen … ÄAVE Sachleistung») und die Vorbehalte, die für diese Zelle gelten |
| Positions-Plot | ein Fach, alle Regionen: Position im Soll-Intervall, IST → PLAN, dazu der ÄAVE-Abstand |
| Kachelkarte | jede Region als gleich große Kachel, grob nach Lage angeordnet, Landesgrenzen als Linien |
| Herkunft («Woher kommt diese Zahl?») | zugeklappt: eine Zeile. Aufgeklappt: PDF, Seite und die Zeile der Matrix, wie sie gedruckt ist; je eingegangener Matrixspalte der Text wie gedruckt, der übernommene Wert und die Herkunft (ausgelesen / von Hand erfasst / Korrekturregel); bei den drei Ländern, die in SVE planen, dazu «Block der ÄAVE-Äquivalente»; darunter jede genannte Regel mit Art und Begründung, wörtlich aus `korrekturen.csv`; Link auf die Verordnung im RIS |
| Über diese Daten | was der Datensatz außerdem enthält, Downloads, wie die Daten abgesichert sind, Zitieren und Fehler melden; alle Links auf das Release, aus dem die Daten der Seite stammen |

Über allem steht dauerhaft, wie «unter» zu lesen ist (Fallstricke 1 und 11): ohne Wahlärzt:innen, ohne
Patientenströme, innerhalb des Intervalls kein Unterschied.

## Was die Seite nicht tut

- **Sie rechnet nichts nach ÖSG-Methode.** VD, Lage, Position und ÄAVE-Abstand kommen aus der Tabelle. Die Seite
  leitet daraus nur die Farbstufe ab (siehe unten) und zählt Zellen für den Anteilsbalken.
- **Sie legt die Herkunft nicht aus.** Rohtexte, Zeilenbeschriftungen und Begründungen stehen da, wie sie in der
  Verordnung bzw. in `korrekturen.csv` stehen. Dass die gezeigten Spalten genau die sind, aus denen der Wert entstand,
  prüft der Bau (siehe «Wer prüft was»); summiert wird dafür nichts Neues.
- **Keine Österreich-Werte** (Fallstrick 5) und keine Summen über Fächer (Fallstricke 4 und 10).
- **Keine Daten von außerhalb** des Datensatzes und keine Bewertungen, die nicht in der Doku stehen.

## Darstellungsregeln

| Was | Regel |
|---|---|
| Farbe | `Lage_im_Intervall`: unter = rot, im = grau, über = blau |
| Stufe außerhalb | Abstand zur Grenze in Intervallbreiten, aus `Position_im_Intervall`: unter ¼, unter ½, ab ½. Für «unter» ist der Abstand −Position, für «über» Position − 1 |
| Im Intervall | eine Farbe, keine Stufen: Der ÖSG macht innerhalb des Intervalls keinen Unterschied (Textband S.38; Fallstrick 11) |
| Schraffur | `AAVE_Abstand_Intervall` kleiner als 1 ÄAVE (Fallstrick 6) |
| PUL und KFO | eigene Spalten, kursiv, als Teil von IM bzw. ZMK gekennzeichnet; im Anteilsbalken mitgezählt, weil der ÖSG beide mit eigenem Soll-Intervall bewertet (Textband S.38–39). Nicht über Fächer addieren (Fallstrick 4) |
| Kein Wert | leere Zelle mit Strich (z. B. KFO in Wien und Vorarlberg, wo KFO in ZMK steckt) |
| Positions-Plot | Achse von −1,5 bis 3; Werte darüber am Rand mit «›». Über dem Band zwei Zeilen: VDmin und VDmax als VD, darunter die Position −1 bis 3 (`Position_im_Intervall`). Je Zeile ein Maßstab, damit die Position nicht als VD gelesen wird; beide stehen oben, damit man sie auch bei 32 VR sieht. Die Lesehilfe («0 = VDmin, 1 = VDmax …») steht als Text unter dem Bild, nicht als Beschriftung darin: Text in einer Grafik bricht nicht um und wäre am Handy an beiden Enden abgeschnitten |
| Rohtext der Herkunft | unverändert, wie gedruckt («191,8», «-», «n.v.»); nie durch die Zahlformatierung der Seite. Was «-» und «n.v.» bedeuten, steht als Satz dabei (DATEN.md, «Zellbedeutung») |
| Werte der Herkunft | exakt, mindestens eine Nachkommastelle wie in den Matrizen – anders als sonst auf der Seite, wo ÄAVE fürs Lesen auf eine Stelle gerundet sind. In dieser Ansicht soll der Wert im PDF wiederzufinden sein |
| Zeile der Matrix | `Zeile_PDF_roh` wörtlich. Fehlt sie, ist das selbst eine Auskunft: «manuell erfasst» = Bildseite ohne Textebene, leer = die Zeile ist im PDF nicht gedruckt (der Wert entsteht erst aus einer Regel) |
| Block der Matrix | bei Burgenland, Kärnten und der Steiermark steht «Block der ÄAVE-Äquivalente» dabei, und die Detailspalte sagt als Vorbehalt, dass nur dieser Block mit den anderen Ländern vergleichbar ist (Fallstrick 3). Ohne das stünde «ÄAVE-Ä» im Zitat der Zeilenbeschriftung unerklärt da |
| Link auf die Quelle | zwei Links: «Seite 11 öffnen» springt in die PDF-Datei auf dem OGD-Dateiserver (`#page=11`), «Verordnung im RIS» auf die Seite des Dokuments im Portal, mit Kundmachung. Beide Adressen sind aus `quellen.csv` abgeleitet (Dokumentnummer, Dateiname), nicht gespeichert |
| Seitenzahl | steht **auch als Text** da, nicht nur im Link: `#page=` ist eine Übereinkunft der PDF-Betrachter, kein Standard des Web. Kennt ein Betrachter sie nicht, öffnet sich die Datei auf Seite 1 – dann muss die Zahl lesbar sein |
| keine Markierung der Zahl im PDF | `#search=` markiert in den meisten Betrachtern nichts und in den übrigen oft die falsche Zelle: Der Rohtext einer gezeigten Zelle ist auf seiner PDF-Seite meist **nicht** eindeutig (nachzurechnen mit `python -m rsg2030.scripts.rohtext_eindeutig`; «-» steht auf einer Seite hunderte Mal). Eine falsche Markierung wäre schlechter als keine. Statt zu markieren, nennt die Seite Zeile und Spalte, in denen die Zahl steht |
| Prüfsummen der Fußzeile | eine Zeile für beide Tabellen, das Release einmal genannt – sie kommen aus demselben. Die Prüfsummen auf zwölf Zeichen gekürzt wie in der Konsole, dahinter `SHA256SUMS.txt` des Release. Zwölf Zeichen sagen, **welche** Datei gezeigt wird; **belegen** kann die Seite sie nicht – eine Prüfsumme neben den Daten, die sie prüfen soll, ist kein Beweis. Der Beleg liegt im Release und in `erwartete_ausgaben.csv`, und dafür braucht man den Link, nicht die Zeichen auf der Seite. Zweimal 64 Zeichen kosteten am Handy vier Zeilen |
| Farben | Nachbarstufen müssen sich deutlich unterscheiden, auch bei Farbsehschwäche (Protanopie, Deuteranopie): Abstand ΔE (OKLab × 100) mindestens 8. Ein Test rechnet das aus den Farben der Seite nach |

## Entscheidungen

Jede Entscheidung mit Grund, damit sie sich später nachvollziehen oder bewusst ändern lässt.

1. **Keine Flächenkarte als Hauptansicht.** Auf einer Flächenkarte bestimmen große, dünn besiedelte Regionen das Bild;
   die drei Wiener Regionen, die bevölkerungsreichsten, wären kaum zu sehen. Gerade kleine Regionen haben die
   unsichersten Werte (Fallstrick 6). Eine eingefärbte Karte legt außerdem «unterversorgt» nahe, was die Daten nicht
   tragen (Fallstricke 1 und 11), und zeigt nur ein Fach auf einmal.
2. **Matrix als Hauptansicht**, dazu Detailspalte, Positions-Plot und Kachelkarte. Die Matrix zeigt das Muster über
   alle Fächer; der Positions-Plot ist die Ansicht, die DATEN.md für Vergleiche über Fächer empfiehlt («die Position
   als Achse»); die Kachelkarte dient nur der Orientierung.
3. **Drei Stufen außerhalb des Intervalls** statt nur unter/im/über: zeigt, ob eine Region knapp oder weit
   danebenliegt. Die Grenzen ¼ und ½ sind eine Festlegung für die Darstellung, keine ÖSG-Regel.
4. **Schraffur unter 1 ÄAVE.** DATEN.md nennt den ÄAVE-Abstand als Einordnung, aber keine Grenze; 1 ÄAVE ist eine
   Festlegung für die Darstellung.
5. **Bundesländer mit Soll-Vergleich.** Der ÖSG misst je Versorgungsregion; die Tabelle enthält die Werte auch je
   Land, und die Seite zeigt sie wie die Tabelle.
6. **PUL und KFO bleiben eigene Spalten.** Der ÖSG gibt beiden ein eigenes Soll-Intervall (Textband S.39). Bewusst
   so, obwohl KFO uneinheitlich ausgewiesen ist (METHODIK.md, R4: in Wien und Vorarlberg in ZMK, in OÖ nur aus einer
   Fußnote).
7. **Farben.** Heller Modus: helle Pastelltöne, sehr helles Grau für «im Intervall»; gewählt aus vier Varianten,
   weil die Seite frisch wirken und trotzdem jede Stufe unterscheidbar sein soll. Dunkler Modus: eigener Farbsatz mit
   derselben Anforderung. Das Grau ist kräftig genug, dass die Zellen im Intervall als Fläche sichtbar sind.
8. **Anteilsbalken.** Auf einen Blick soll stimmen, wie viel der Matrix im Intervall liegt; ohne Balken zieht die
   farbige Hälfte alle Aufmerksamkeit auf sich.
9. **Handy.** Kein Tooltip (ohne Maus bliebe er stehen); ein Tippen springt zur Detailspalte, ein Knopf führt zurück;
   die Werkzeugleiste klebt nicht oben, weil sie umgebrochen ein Drittel des Bildschirms belegte. Positions-Plot und
   Kachelkarte werden nur neu gezeichnet, wenn sich ihre Breite ändert: iOS meldet eine Größenänderung auch, wenn
   beim Scrollen bloß die Adressleiste ein- und ausfährt. Baute die Seite die Grafiken dabei neu auf, zeichnete
   Safari sie nur halb fertig, und einzelne Namen und Zahlen fehlten, bis man die Seite wieder bewegte. Die
   Datenerkennung von iOS ist abgeschaltet (`format-detection`): Sie las Zeilen wie «61 Graz» als Adresse,
   unterstrich sie gestrichelt und fing das Tippen auf die Zeile ab.
10. **Kachelkarte:** Steiermark direkt unter Ober- und Niederösterreich, Kärnten unter Salzburg und Steiermark,
    Osttirol abgesetzt neben Kärnten. Wo das Raster nicht reicht, liegt eine Nachbarschaft ungenau.
11. **Im Datensatz-Repo statt in einem eigenen.** Die Seite stellt den Datensatz dar und bildet keine neuen
    Kennzahlen. Im selben Repo lassen sich die Vorbehalte im selben Commit nachziehen wie die Daten (Regel «Vorbehalte
    folgen den Daten» in CLAUDE.md). In ein eigenes Repo gehörte sie, sobald sie Daten von außerhalb, neue Kennzahlen
    oder Bewertungen über die Fallstricke hinaus zeigte.
12. **Herkunft als eigenes Panel in voller Breite**, unter Matrix und Detailspalte, nicht in der Detailspalte.
    Die Detailspalte klebt beim Scrollen (`position: sticky`); aufgeklappt wäre sie höher als der Bildschirm, und ihr
    Ende nicht mehr erreichbar. In voller Breite liest die Begründung einer Regel in rund fünf statt zwölf Zeilen, und
    wer von der Matrix zum Positions-Plot scrollt, geht an der Zeile vorbei. Zugeklappt kostet sie eine Zeile; der
    Zustand bleibt gespeichert wie die Schraffur.
13. **Begründungen aus `korrekturen.csv` im Repo**, nicht aus einer veröffentlichten Datei: Die Long-CSV nennt je
    Zelle nur den Namen der Regel. Dass die Begründung zu den gezeigten Zahlen gehört, sichert die bestehende
    Prüfsummen-Kontrolle – eine Regeländerung, die Daten ändert, passt nicht mehr zu `erwartete_ausgaben.csv`, und der
    Bau bricht ab. Die Zuordnung Zelle → Regel steht in `rsg2030/korrekturen.py` (`regel_fuer_zelle`) und nicht in
    `web.py`: Nur dort steht, wie eine Regel ihre Zellen wählt («+» in `Zeile_ID`, «*» in Matrix und Fach).
14. **Veröffentlichung aus dem Release.** Ein eigener Workflow (`webseite.yml`) baut die Seite nach jedem
    erfolgreichen Lauf des Release-Workflows und wenn sich die Seite auf `main` ändert. Er rechnet die Daten nicht
    neu, sondern lädt die CSV des aktuellen Release und prüft sie gegen dessen `SHA256SUMS.txt`. Passt die Seite nicht
    zu den Daten (z. B. fehlende Spalte), bricht er ab, und die bisherige Seite bleibt. Die Fußzeile nennt Datenstand
    (Release, Prüfsumme) und Stand der Seite (Commit). Für Änderungen an der Seite braucht es kein neues Release.
15. **Wer die Seite erstellt hat, steht in der Fußzeile**, mit den Vorbehalten im selben Satz: ohne Auftrag,
    inoffizielle Aufbereitung amtlicher Daten – maßgeblich sind die Verordnungen im RIS –, Angaben ohne Gewähr,
    Fehler bitte melden. Die Seite liegt unter einer eigenen Adresse, nicht beim Repo; wer sie ohne das README
    öffnet, muss sie dort einordnen können. Dazu die Links auf Impressum und Datenschutz, die eine veröffentlichte
    Seite braucht. Mehr nicht: kein Logo, kein Werbetext, keine Kennzahl und kein Urteil, das nicht in der Doku
    steht. Die drei Links trägt die Fußzeile wie alle anderen mit `noreferrer`, und die Seite lädt weiterhin nichts
    von fremden Servern («Wer prüft was»). Derselbe Satz steht im README («Versionen und Zitieren»).

## Aufbau

```
web/                  die Seite: index.html, app.js, style.css
  fonts/                IBM Plex, selbst ausgeliefert (Lizenz SIL OFL, fonts/README.md)
  kacheln.csv           je Region Spalte und Zeile der Kachelkarte und die Beschriftung der Kachel (VR und BL)
  faecher.csv           Fächer in der Reihenfolge der Spalten, Name, «Teil von» (PUL → IM, KFO → ZMK)
rsg2030/web.py        «python -m rsg2030 web»: Tabellen Versorgungsdichte und Planungsmatrizen → data.json,
                        Seite nach daten_ergebnis/web/; `baue_herkunft` baut den Herkunfts-Teil
rsg2030/korrekturen.py  `regel_fuer_zelle`: welche Regel aus korrekturen.csv eine korrigierte Zelle erklärt
rsg2030/scripts/rohtext_eindeutig.py   belegt, warum die Seite die Zahl im PDF nicht markiert
tests/test_web.py     Kacheln, Fächer, Vorbehalte, Farben, data.json, Herkunft (siehe «Wer prüft was»)
.github/workflows/webseite.yml   bauen und auf GitHub Pages veröffentlichen
```

Die fertige Seite liegt wie alle Ergebnisse nicht in git. Die Seite lädt `data.json` und rechnet nichts nach; jede
Angabe hat eine Quelle: Werte und Soll-Intervalle aus der Tabelle Versorgungsdichte, Rohtexte, PDF, Seite und
Zeilenbeschriftung aus der Tabelle Planungsmatrizen, Art und Begründung einer Regel aus `korrekturen.csv`, die Adresse
der Verordnung aus der Dokumentnummer in `quellen/quellen.csv`, Namen der Regionen und Länder aus `oesg_regionen.csv`,
Namen der Fächer aus `web/faecher.csv`, Lage der Kacheln aus `web/kacheln.csv`. Kopf und Fußzeile nennen Release,
beide Prüfsummen (gekürzt, siehe Darstellungsregeln) und den Commit aus `data.json`. Wer die Seite erstellt hat,
die Vorbehalte dazu und die Links auf Impressum und Datenschutz sind fester Text der Seite, keine Angabe aus den
Daten (Entscheidung 15).

## Selbst bauen und ansehen

```bash
.venv/bin/python -m rsg2030 web                          # braucht RSG_2030_Versorgungsdichte.csv und
                                                         # RSG_2030_Planungsmatrizen.csv in daten_ergebnis/
.venv/bin/python -m http.server -d daten_ergebnis/web    # dann http://localhost:8000 im Browser
```

Die Tabellen entstehen mit `python -m rsg2030 alles`; es reichen auch die Dateien des Release in `daten_ergebnis/`.
Gebaut wird nur, wenn **beide** Byte für Byte der Version des Pakets entsprechen (`rsg2030/erwartete_ausgaben.csv`):
Nur dann stimmt «Release …» auf der Seite, und nur dann gehören die Begründungen aus `korrekturen.csv` zu den
gezeigten Zahlen. Die Seite direkt als Datei zu öffnen geht nicht, weil der Browser `data.json`
dann nicht laden darf; dafür der kleine Server.

## Wer prüft was

| Was schiefgehen kann | Wer es findet |
|---|---|
| falsche oder veränderte Tabelle | `python -m rsg2030 web`: Prüfsumme beider Tabellen gegen `erwartete_ausgaben.csv`; sonst wird nicht gebaut |
| die gezeigte Herkunft gehört nicht zum gezeigten Wert (Spalte fehlt oder eine zu viel) | `python -m rsg2030 web` bricht ab: Die Summe der gezeigten Teile muss den veröffentlichten ÄAVE-Wert ergeben, Zelle für Zelle; Test mit einer kleinen Matrix, in der ein Teil verstellt ist |
| falsches PDF oder falsche Seite genannt | Bau bricht ab, wenn PDF und Seite der benutzten Zeilen je Matrix und Abschnitt nicht eindeutig sind; Test dafür |
| Seite formatiert den Rohtext um und zeigt etwas anderes als das Dokument | Test (ganze Suite): jeder Rohtext, Wert und jede `Quelle` in `data.json` steht zeichengleich in der Tabelle Planungsmatrizen |
| korrigierte Zelle ohne Begründung, oder falsche Regel zugeordnet | Bau bricht ab, wenn eine Zelle mit `Quelle = korrigiert` nicht genau eine Regel findet; Test (ganze Suite): jede genannte Regel steht mit dieser Art und Begründung in `korrekturen.csv` |
| zwei Regeln mit demselben Namen verwechselt (Kärnten: `plus:6.3` ist in VR 22 eine Lücke, im Land ihre Folge) | Test: zwei Regeln gleichen Namens in verschiedenen Regionen müssen zu verschiedenen Begründungen führen |
| Begründung passt nicht zu den gezeigten Zahlen (Regel auf main neuer als das Release) | die Prüfsumme: eine datenwirksame Regeländerung ohne neues Release passt nicht zu `erwartete_ausgaben.csv`, der Bau bricht ab |
| unbekannte `Quelle` einer Zelle, für die die Seite keinen Text hat | Bau bricht ab; Test dafür |
| Link ins PDF führt ins Leere oder auf eine andere Fassung | `python -m rsg2030 waechter --quellen` (monatlich) lädt jede Verordnungs-PDF unter genau der verlinkten Adresse und vergleicht die Prüfsumme mit dem Register. Ohne das brächen alle Links auf einmal und still, denn die RIS-Prüfung sieht nur die Dokumentnummern |
| PDF fehlt im Quellenregister | Bau bricht ab, wenn ein PDF nicht als RSG-Verordnung in `quellen.csv` steht; Test dafür |
| Sprung auf die Seite greift im Browser nicht | ein Mensch vor der Veröffentlichung; die Seitenzahl steht als Text daneben, damit das kein Beinbruch ist. Das RIS-Portal antwortet Rechenzentren nicht, die CI kann es nicht aufrufen |
| Region fehlt in der Kachelkarte oder zwei Regionen auf einem Feld | Test: `kacheln.csv` enthält genau die VR und Länder aus `oesg_regionen.csv`, jedes Feld einmal |
| Fach fehlt, falscher Name oder falsches «Teil von» | Test: `faecher.csv` enthält genau die Richtwertzeilen mit Soll-Intervall; «Teil von» wie `ZUSCHNITT` in `oesg_methodik/faecher.py` |
| Seite passt nicht mehr zur Tabelle (Spalte, Fach oder Region neu oder weg) | `python -m rsg2030 web` bricht mit Meldung ab; Tests dafür |
| Zahl auf der Seite weicht von der Tabelle ab | Test (ganze Suite): `data.json` gegen die Tabelle |
| ein Vorbehalt verweist auf einen Fallstrick, den es nicht mehr gibt | Test: jeder Vorbehalt nennt seinen Fallstrick, und den gibt es in DATEN.md |
| Farbstufen nicht unterscheidbar | Test: Abstände benachbarter Stufen aus `style.css` nachgerechnet, normal und bei Protanopie und Deuteranopie, hell und dunkel; dunkle Farben gleich, ob über die Systemeinstellung oder den Schalter |
| Seite gibt etwas an fremde Server (z. B. Schriften von Google: IP-Adresse jeder Besucherin dorthin) | Tests: keine Schriften, Skripte oder Stile von außen, jede Schrift der CSS liegt in `web/fonts/`; jeder Link nach außen trägt `noreferrer`, gibt also nicht weiter, von welcher Seite jemand kam |
| Link auf Lösungswerk, Impressum oder Datenschutz führt ins Leere | der Herausgeber: Die drei Adressen führen auf die eigene Website. Kein Test ruft sie auf, denn weder die Seite noch ihr Bau sollen fremde Server befragen |
| Seite lädt nicht, Fehler im Skript, Seite am Handy breiter als der Bildschirm | ein Mensch vor der Veröffentlichung; später ein Test im Browser |
| ein Vorbehalt ist fachlich falsch oder missverständlich formuliert | der Herausgeber |
