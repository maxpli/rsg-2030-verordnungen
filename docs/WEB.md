# Webseite

Eine Webseite zeigt die Tabelle Versorgungsdichte (`RSG_2030_Versorgungsdichte.csv`) zum Nachsehen: je
Versorgungsregion und Fach, ob die Sachleistung unter, im oder über dem Versorgungsdichte-Soll-Intervall (ÖSG) liegt.
Wie die Excel-Mappe ist sie eine **Ansicht des Datensatzes**: Sie zeigt nur, was in den veröffentlichten Dateien steht,
und übernimmt die Vorbehalte aus [DATEN.md](DATEN.md#fallstricke).

**Stand:** Seite, Befehl, Tests und Workflow sind im Repo; veröffentlicht ist sie noch nicht. Offene Punkte stehen in
[offene_punkte.md](offene_punkte.md#webseite).

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
| Über diese Daten | was der Datensatz außerdem enthält, Downloads, wie die Daten abgesichert sind, Zitieren und Fehler melden; alle Links auf das Release, aus dem die Daten der Seite stammen |

Über allem steht dauerhaft, wie «unter» zu lesen ist (Fallstricke 1 und 11): ohne Wahlärzt:innen, ohne
Patientenströme, innerhalb des Intervalls kein Unterschied.

## Was die Seite nicht tut

- **Sie rechnet nichts nach ÖSG-Methode.** VD, Lage, Position und ÄAVE-Abstand kommen aus der Tabelle. Die Seite
  leitet daraus nur die Farbstufe ab (siehe unten) und zählt Zellen für den Anteilsbalken.
- **Keine Österreich-Werte** (Fallstrick 5) und keine Summen über Fächer (Fallstricke 4 und 10).
- **Keine Daten von außerhalb** des Datensatzes und keine Bewertungen, die nicht in der Doku stehen.

## Darstellungsregeln

| Was | Regel |
|---|---|
| Farbe | `Lage_im_Intervall`: unter = rot, im = grau, über = blau |
| Stufe außerhalb | Abstand zur Grenze in Intervallbreiten, aus `Position_im_Intervall`: unter ¼, unter ½, ab ½. Für «unter» ist der Abstand −Position, für «über» Position − 1 |
| Im Intervall | eine Farbe, keine Stufen: Der ÖSG macht innerhalb des Intervalls keinen Unterschied (Textband S.36; Fallstrick 11) |
| Schraffur | `AAVE_Abstand_Intervall` kleiner als 1 ÄAVE (Fallstrick 6) |
| PUL und KFO | eigene Spalten, kursiv, als Teil von IM bzw. ZMK gekennzeichnet; im Anteilsbalken mitgezählt, weil der ÖSG beide mit eigenem Soll-Intervall bewertet (Textband S.36–37). Nicht über Fächer addieren (Fallstrick 4) |
| Kein Wert | leere Zelle mit Strich (z. B. KFO in Wien und Vorarlberg, wo KFO in ZMK steckt) |
| Positions-Plot | Achse von −1,5 bis 3; Werte darüber am Rand mit «›» |
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
6. **PUL und KFO bleiben eigene Spalten.** Der ÖSG gibt beiden ein eigenes Soll-Intervall (Textband S.37). Bewusst
   so, obwohl KFO uneinheitlich ausgewiesen ist (METHODIK.md, R4: in Wien und Vorarlberg in ZMK, in OÖ nur aus einer
   Fußnote).
7. **Farben.** Heller Modus: helle Pastelltöne, sehr helles Grau für «im Intervall»; gewählt aus vier Varianten,
   weil die Seite frisch wirken und trotzdem jede Stufe unterscheidbar sein soll. Dunkler Modus: eigener Farbsatz mit
   derselben Anforderung. Das Grau ist kräftig genug, dass die Zellen im Intervall als Fläche sichtbar sind.
8. **Anteilsbalken.** Auf einen Blick soll stimmen, wie viel der Matrix im Intervall liegt; ohne Balken zieht die
   farbige Hälfte alle Aufmerksamkeit auf sich.
9. **Handy.** Kein Tooltip (ohne Maus bliebe er stehen); ein Tippen springt zur Detailspalte, ein Knopf führt zurück;
   die Werkzeugleiste klebt nicht oben, weil sie umgebrochen ein Drittel des Bildschirms belegte.
10. **Kachelkarte:** Steiermark direkt unter Ober- und Niederösterreich, Kärnten unter Salzburg und Steiermark,
    Osttirol abgesetzt neben Kärnten. Wo das Raster nicht reicht, liegt eine Nachbarschaft ungenau.
11. **Im Datensatz-Repo statt in einem eigenen.** Die Seite ist eine Ansicht des Datensatzes wie die Excel-Mappe. Im
    selben Repo lassen sich die Vorbehalte im selben Commit nachziehen wie die Daten (Regel «Vorbehalte folgen den
    Daten» in CLAUDE.md). In ein eigenes Repo gehörte sie erst, wenn sie Daten von außerhalb oder Analysen zeigte.
12. **Veröffentlichung aus dem Release.** Ein eigener Workflow (`webseite.yml`) baut die Seite nach jedem
    erfolgreichen Lauf des Release-Workflows und wenn sich die Seite auf `main` ändert. Er rechnet die Daten nicht
    neu, sondern lädt die CSV des aktuellen Release und prüft sie gegen dessen `SHA256SUMS.txt`. Passt die Seite nicht
    zu den Daten (z. B. fehlende Spalte), bricht er ab, und die bisherige Seite bleibt. Die Fußzeile nennt Datenstand
    (Release, Prüfsumme) und Stand der Seite (Commit). Für Änderungen an der Seite braucht es kein neues Release.

## Aufbau

```
web/                  die Seite: index.html, app.js, style.css
  fonts/                IBM Plex, selbst ausgeliefert (Lizenz SIL OFL, fonts/README.md)
  kacheln.csv           je Region Spalte und Zeile der Kachelkarte und die Beschriftung der Kachel (VR und BL)
  faecher.csv           Fächer in der Reihenfolge der Spalten, Name, «Teil von» (PUL → IM, KFO → ZMK)
rsg2030/web.py        «python -m rsg2030 web»: Tabelle Versorgungsdichte → data.json, Seite nach daten_ergebnis/web/
tests/test_web.py     Kacheln, Fächer, Vorbehalte, Farben, data.json (siehe «Wer prüft was»)
.github/workflows/webseite.yml   bauen und auf GitHub Pages veröffentlichen
```

Die fertige Seite liegt wie alle Ergebnisse nicht in git. Die Seite lädt `data.json` und rechnet nichts nach; jede
Angabe hat eine Quelle: Werte und Soll-Intervalle aus der Tabelle Versorgungsdichte, Namen der Regionen und Länder aus
`oesg_regionen.csv`, Namen der Fächer aus `web/faecher.csv`, Lage der Kacheln aus `web/kacheln.csv`. Kopf und
Fußzeile nennen Release, Prüfsumme und Commit aus `data.json`.

## Selbst bauen und ansehen

```bash
.venv/bin/python -m rsg2030 web                          # braucht daten_ergebnis/RSG_2030_Versorgungsdichte.csv
.venv/bin/python -m http.server -d daten_ergebnis/web    # dann http://localhost:8000 im Browser
```

Die Tabelle entsteht mit `python -m rsg2030 alles`; es reicht auch die Datei des Release in `daten_ergebnis/`.
Gebaut wird nur, wenn sie Byte für Byte der Version des Pakets entspricht (`rsg2030/erwartete_ausgaben.csv`): Nur
dann stimmt «Release …» auf der Seite. Die Seite direkt als Datei zu öffnen geht nicht, weil der Browser `data.json`
dann nicht laden darf; dafür der kleine Server.

## Wer prüft was

| Was schiefgehen kann | Wer es findet |
|---|---|
| falsche oder veränderte Tabelle | `python -m rsg2030 web`: Prüfsumme gegen `erwartete_ausgaben.csv`; sonst wird nicht gebaut |
| Region fehlt in der Kachelkarte oder zwei Regionen auf einem Feld | Test: `kacheln.csv` enthält genau die VR und Länder aus `oesg_regionen.csv`, jedes Feld einmal |
| Fach fehlt, falscher Name oder falsches «Teil von» | Test: `faecher.csv` enthält genau die Richtwertzeilen mit Soll-Intervall; «Teil von» wie `ZUSCHNITT` in `oesg_methodik/faecher.py` |
| Seite passt nicht mehr zur Tabelle (Spalte, Fach oder Region neu oder weg) | `python -m rsg2030 web` bricht mit Meldung ab; Tests dafür |
| Zahl auf der Seite weicht von der Tabelle ab | Test (ganze Suite): `data.json` gegen die Tabelle |
| ein Vorbehalt verweist auf einen Fallstrick, den es nicht mehr gibt | Test: jeder Vorbehalt nennt seinen Fallstrick, und den gibt es in DATEN.md |
| Farbstufen nicht unterscheidbar | Test: Abstände benachbarter Stufen aus `style.css` nachgerechnet, normal und bei Protanopie und Deuteranopie, hell und dunkel; dunkle Farben gleich, ob über die Systemeinstellung oder den Schalter |
| Seite lädt etwas von fremden Servern (z. B. Schriften von Google: IP-Adresse jeder Besucherin dorthin) | Test: keine Schriften, Skripte oder Stile von außen; jede Schrift der CSS liegt in `web/fonts/` |
| Seite lädt nicht, Fehler im Skript, Seite am Handy breiter als der Bildschirm | ein Mensch vor der Veröffentlichung; später ein Test im Browser |
| ein Vorbehalt ist fachlich falsch oder missverständlich formuliert | der Herausgeber |
