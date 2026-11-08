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

**Veröffentlicht unter <https://rsg.loesungswerk.at/>**, mit den Daten des aktuellen Release.
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
| Kein Wert: Herkunft trotzdem | Die Klappe «Woher kommt diese Zahl?» nennt **auch ohne Wert** PDF, Seite und die Verordnung im RIS – nur so lässt sich nachsehen, dass in der Matrix wirklich nichts steht. Dazu ein Satz, woran es liegt: das Fach steckt im Elternfach (Zuschnitt sagt «… nicht getrennt ausgewiesen»), die Matrix hat die Spalte nicht (Kärnten, MKG – Fallstrick 13) oder die Zelle ist leer. Die Texte stehen in `darstellung.py` (`KEIN_WERT`), die Zuordnung je Zelle in `data.json` |
| Positions-Plot | Achse von −1,5 bis 3; Werte darüber am Rand mit «›». Über dem Band zwei Zeilen: VDmin und VDmax als VD, darunter die Position −1 bis 3 (`Position_im_Intervall`). Je Zeile ein Maßstab, damit die Position nicht als VD gelesen wird; beide stehen oben, damit man sie auch bei 32 VR sieht. Die Lesehilfe («0 = VDmin, 1 = VDmax …») steht als Text unter dem Bild, nicht als Beschriftung darin: Text in einer Grafik bricht nicht um und wäre am Handy an beiden Enden abgeschnitten |
| Rohtext der Herkunft | unverändert, wie gedruckt («191,8», «-», «n.v.»); nie durch die Zahlformatierung der Seite. Was «-» und «n.v.» bedeuten, steht als Satz dabei (DATEN.md, «Zellbedeutung») |
| Werte der Herkunft | exakt, mindestens eine Nachkommastelle wie in den Matrizen – anders als sonst auf der Seite, wo ÄAVE fürs Lesen auf eine Stelle gerundet sind. In dieser Ansicht soll der Wert im PDF wiederzufinden sein |
| Zeile der Matrix | `Zeile_PDF_roh` wörtlich. Fehlt sie, ist das selbst eine Auskunft: «manuell erfasst» = Bildseite ohne Textebene, leer = die Zeile ist im PDF nicht gedruckt (der Wert entsteht erst aus einer Regel) |
| Block der Matrix | bei Burgenland, Kärnten und der Steiermark steht «Block der ÄAVE-Äquivalente» dabei, und die Detailspalte sagt als Vorbehalt, dass nur dieser Block mit den anderen Ländern vergleichbar ist (Fallstrick 3). Ohne das stünde «ÄAVE-Ä» im Zitat der Zeilenbeschriftung unerklärt da |
| Link auf die Quelle | zwei Links: «Seite 11 öffnen» springt in die PDF-Datei auf dem OGD-Dateiserver (`#page=11`), «Verordnung im RIS» auf die Seite des Dokuments im Portal, mit Kundmachung. Beide Adressen sind aus `quellen.csv` abgeleitet (Dokumentnummer, Dateiname), nicht gespeichert |
| Seitenzahl | steht **auch als Text** da, nicht nur im Link: `#page=` ist eine Übereinkunft der PDF-Betrachter, kein Standard des Web. Kennt ein Betrachter sie nicht, öffnet sich die Datei auf Seite 1 – dann muss die Zahl lesbar sein |
| keine Markierung der Zahl im PDF | `#search=` markiert in den meisten Betrachtern nichts und in den übrigen oft die falsche Zelle: Der Rohtext einer gezeigten Zelle ist auf seiner PDF-Seite meist **nicht** eindeutig (nachzurechnen mit `python -m rsg2030.scripts.rohtext_eindeutig`; «-» steht auf einer Seite hunderte Mal). Eine falsche Markierung wäre schlechter als keine. Statt zu markieren, nennt die Seite Zeile und Spalte, in denen die Zahl steht |
| Keine Prüfsummen in der Fußzeile, aber der Commit | Das Release nennt die Fußzeile als Link «Release …», Prüfsummen nicht. Zwölf Zeichen einer Prüfsumme sagen, **welche** Datei gezeigt wird; **belegen** kann die Seite sie nicht – eine Prüfsumme neben den Daten, die sie prüfen soll, ist kein Beweis. Der Beleg liegt im Release (`SHA256SUMS.txt`, Prüfbericht) und in `erwartete_ausgaben.csv`, und dafür braucht man den Link, nicht die Zeichen auf der Seite. In `data.json` (`meta`) stehen sie weiter. **Der Commit steht da**, kurz und verlinkt, hinter «Angaben ohne Gewähr» («Stand der Seite: 8657f10»): Die Seite ändert sich auch ohne neues Release (Entscheidung 14), und bei einer Fehlermeldung, einem Screenshot oder einem Zitat sagt er, welcher Text dabeistand |
| Farben | Nachbarstufen müssen sich deutlich unterscheiden, auch bei Farbsehschwäche (Protanopie, Deuteranopie): Abstand ΔE (OKLab × 100) mindestens 8. Ein Test rechnet das aus den Farben der Seite nach |

## Lesefassung: statische Seiten

Neben dem Dashboard erzeugt `python -m rsg2030 lesefassung` **59 Seiten ohne JavaScript**, in denen jede Zahl als
Text im HTML steht. Grund: In den Verordnungs-PDFs sind die Zahlen für Suchmaschinen und Abrufsysteme unerreichbar
(Querformat, teils Bildseiten ohne Textebene), und auf dem Dashboard entstehen sie erst im Browser. Der Mehrwert
gegenüber den PDFs ist nicht die Abschrift, sondern der Vergleich: Versorgungsdichte, Lage zum Soll-Intervall und
ÄAVE-Abstand stehen in keinem veröffentlichten Dokument.

| Adresse | Inhalt |
|---|---|
| `/daten/` | der Einstieg: wofür der Datensatz da ist, der Hauptvorbehalt in einem Halbsatz (die ganze Lesehilfe steht bei den Zahlen, nicht vor dem Verzeichnis), Verzeichnis der Regionen (je Bundesland) und der Fächer (mit Soll-Intervall), Downloads, die neun Verordnungen, «Bewusst weggelassen» (je Punkt zuerst, was fehlt, dann in einem Satz warum – keine Verneinung unter der Überschrift); am Ende alle 537 Zeilen «insgesamt» in einer zugeklappten Tabelle, mit denselben Spalten wie die Tabelle Versorgungsdichte einer Region und derselben Lesehilfe darunter – ein Abrufsystem liest meist nur eine Seite und kann eine Frage über alle Regionen nur hier mit einem Abruf beantworten – und der **einzige** `Dataset`-Eintrag des Werks |
| `/bl/<kurz>/` | 9 Bundesländer: Eckdaten mit den Versorgungsregionen, Quelle, die drei Tabellen (Versorgungsdichte, ÄAVE, Sachleistungsstellen), Apparat |
| `/vr/<nr>/` | 32 Versorgungsregionen: dasselbe, in den Eckdaten die Bezirke und der Hinweis, dass auf Ebene der Region geplant wird |
| `/fach/<id>/` | 17 Fächer: das Soll-Intervall mit Link auf die Seite im ÖSG-Textband (S.39, auf dem Dateiserver des RIS; der ÖSG wird nur verlinkt), dann dieselben drei Tabellen gekippt, je Versorgungsregion eine Zeile |
| `/sitemap.xml` | alle Seiten |

**Die Adressen sind endgültig.** GitHub Pages kann einzelne Seiten nicht umleiten (nur die alte Adresse als Ganzes auf die eigene Domain), deshalb Nummern und Kürzel statt Namen: Eine
Versorgungsregion kann umbenannt werden, ihre Nummer nicht. Die Kürzel der Länder stehen als Liste in
`lesefassung.py`, nicht als Umschrift-Regel – damit sie sich nicht still ändern können.

### Darstellungsregeln der Lesefassung

| Was | Regel |
|---|---|
| Zwei Wege, eine Aufgabe je Weg | **Nachschlagen** (diese Seiten): «Was gilt für meine Region, mein Fach?» – eine Tabelle mit Quelle, ohne Farben, ohne Vergleich über viele Regionen. **Vergleichen** (Dashboard): Muster über alle Regionen und Fächer. Beide stehen auf jeder Seite oben nebeneinander («Nachschlagen: Regionen und Fächer», «Vergleichen: interaktive Matrix»). **Der Weg geht vor allem in eine Richtung:** Die Seiten führen ins Dashboard (mit `?region=` und `?fach=`); das Dashboard verlinkt die Seiten nur einmal, unauffällig, als letzter Absatz unter «Über diese Daten», fest im HTML. Wer im Dashboard ist, findet dort zu jeder Zelle mehr als auf der Seite (Lage im IST, Herkunft je Wert); was nur auf den Seiten steht (Sachleistungsstellen, eine Region als Zahlentabelle), rechtfertigt keinen Link bei jeder Zelle, und für alles Weitere gibt es die CSV-Dateien des Release. Dieser eine Link ist für Suchmaschinen da: Links von außen zeigen aufs Dashboard, und ohne Link von dort kennt eine Suchmaschine die Seiten nur aus der Sitemap; Crawler ohne JavaScript sehen nur das HTML, deshalb steht er nicht in `app.js`. Ob die Stellen ins Dashboard kommen: [offene_punkte.md](offene_punkte.md), Webseite 7. **Das Dashboard bleibt auf der Wurzel** (`/`): Wer einen Link geschickt bekommt, will die Matrix sehen, und gefunden werden sollen die Einzelseiten, nicht die Startseite; ein Umzug bräche geteilte Links mit `?region=`. Es trägt `canonical` auf die Wurzel, damit die Links der Seiten mit `?region=…&fach=…` nicht als eigene Seiten zählen |
| Kopf einer Seite | Brotkrumen (`RSG 2030 › Steiermark › Graz`, auch als `BreadcrumbList`), die Überschrift ist der Name («Graz (VR 61)»), darunter **eine** Zeile Eckdaten (Bundesland, Bezirke, Wohnbevölkerung), die weiteren Regionen des Landes und **eine** Zeile Quelle (Verordnung, Seite, RIS) |
| Breite und Klappen | Text höchstens 70 Zeichen breit, überall – im Inhalt, in den Klappen, in der Fußzeile –, nur Tabellen und Verzeichnisse breiter. Klappen (Herkunft, Anhang) als Liste mit dünnen Linien, nicht als graue Flächen: Sie sind Nebensache und sollen nicht schwerer wirken als die Tabellen |
| Aufbau | **Weniger ist hier mehr: Die Tabellen sind die Antwort.** Kopf, Eckdaten, Quelle; dann **drei Tabellen, je eine Einheit**: Versorgungsdichte, ÄAVE, Sachleistungsstellen – je mit Überschrift (ohne Jahr, wo IST und PLAN darin stehen; «PLAN 2030» bei den Stellen, die es nur im PLAN gibt), Spaltenköpfe immer mit «IST 2022/2023» bzw. «PLAN 2030» und dem, was man zum Lesen braucht, direkt darunter. Zum Aufklappen nur noch die Herkunft: Fußnoten, Korrekturen, Abweichungen, offene Fragen – zugeklappt, aber im HTML und damit indexierbar. Eine frühere Fassung hatte große Zählzahlen, einen Antwortsatz, einen Kasten, Begriffe und je Fach einen Satz; das wiederholte die Tabelle in Prosa und las sich wie generierter Text. Eine spätere mischte ÄAVE, VD und Stellen in einer Tabelle und versteckte das IST |
| Was auf die Seite gehört | **Text nur dort, wo die Tabelle etwas nicht sagen kann** – nicht Text über unsere Entscheidungen. Warum die IST-Planstellen fehlen, warum es keine Österreich-Zahl gibt, wie die VR-Bevölkerung geschätzt ist: Das steht in METHODIK.md. Unter jeder Tabelle steht eine Lesehilfe: was VD, ÄAVE und Sachleistungsstellen sind (Wortlaut des Glossars in METHODIK.md), dass nur die Sachleistung gezählt ist, ohne Wahlärzt:innen, und dass der ÖSG im Intervall keinen Unterschied macht |
| Interaktiv vergleichen | ein Link **oben in der Bereichsleiste**, nicht als Kasten im Text, mit vorbelegtem Zustand (`?region=41`, `?fach=PSY`). Der Schlüssel `slug` steht in `data.json` und ist derselbe wie in den Adressen. Ohne Parameter verhält sich das Dashboard wie vorher, und es schreibt die Adresse nie |
| Vorbehalte bei der Tabelle | Die Vorbehalte, die für Zellen **dieser** Tabelle gelten, stehen direkt darunter, **jeder einmal**; an den Zeilen, für die er gilt, eine hochgestellte Zahl. Was für jede Zeile gilt (auf einer Regionsseite z. B. «ohne Patientenströme», «plant in SVE»), steht ohne Zahl. Texte wörtlich aus `darstellung.py`. «Teil von» entfällt hier, das sagt der Satz zu PUL und KFO unter jeder Tabelle. Unter der Tabelle statt in einem Kasten darüber: Wer eine Tabelle zitiert, nimmt den Text darunter eher mit |
| Links nach außen | `target="_blank" rel="noopener noreferrer"` wie im Dashboard: Ein Sprung in eine 200-seitige PDF oder ins RIS-Portal soll die Seite nicht ersetzen, und niemand erfährt, von welcher Seite jemand kam. Interne Links (Region, Fach, Index, Dashboard) bleiben im selben Fenster und tragen kein `rel` |
| Tabellenbeschriftung | jede Tabelle hat eine `<caption>`, die Region bzw. Fach, Abschnitt und Bezugsgröße nennt: Daran benennen Bildschirmleser und Text-Extraktoren die Tabelle |
| Tabelle Versorgungsdichte | je Fach (bzw. je Versorgungsregion) **VD IST, VD PLAN 2030, Soll-Intervall, Lage zum Soll-Intervall PLAN 2030**. IST und PLAN nebeneinander, damit man eine Veränderung sieht, ohne eine Differenz zu rechnen – beide Werte stehen so in der Tabelle. Darunter, dass das Soll-Intervall für 2030 gilt und der IST-Wert daran gemessen den Abstand zur Norm zeigt (Fallstrick 11); auf der Fachseite, welches Land welches IST-Jahr hat. Die Beschriftung nennt Region bzw. Fach und «Sachleistung», damit die Tabelle auch allein zitiert verständlich ist |
| Keine Farben | «unter» und «über» stehen kräftig, «im» zurückhaltend – über die Schrift, nicht über eine Farbe; das Wort trägt die Aussage. Die Lage steht als Wort in der Tabelle: «unter», «im», «über», neben der Spalte «Soll-Intervall» – ausgeschrieben («unter dem Soll-Intervall») brach sie in jeder Zeile um und verdoppelte die Höhe der Tabelle. In den Sätzen steht sie ausgeschrieben. Ohne Farbe braucht es keine Farbprüfung, und der Text bleibt vollständig, wenn ihn eine Maschine liest |
| Zuschnitt | ein Zeichen (◆) an den betroffenen Zeilen, aufgelöst in einer Zeile unter der Tabelle – je Tabelle eigens, weil AM bei den ÄAVE die ZAE enthält und bei den Stellen nicht (DATEN.md, «Warum AM hier anders zugeschnitten ist») |
| Stellen: Spalten mit lauter 0 | Eine Spalte «zusätzlich ÖGK/SVS/BVAEB», in der für **jedes** Fach der Region 0 steht, entfällt; ein Satz unter der Tabelle nennt den Träger und dass dort 0 steht. Die Information bleibt, und die Tabelle passt am Handy ohne Scrollen. Die gemeinsamen Stellen stehen immer da |
| Stellen | **eigene Tabelle, nicht als Spalte neben den ÄAVE.** Die ÄAVE zählen die ganze Sachleistung einschließlich der Spitalsambulanzen, die Sachleistungsstellen planen nur den niedergelassenen Bereich und die Ambulatorien – «nicht zu verwechseln» (METHODIK.md, «Begriffe»). Nebeneinander lädt das zum Verrechnen ein («211,5 ÄAVE, 185 Stellen»). Darunter steht das als Satz, dazu, dass AM bei den Stellen ohne ZAE gezählt ist (DATEN.md, Tabelle Stellen), und auf den Wiener Seiten, dass Wien zusätzliche Stellen nach ihrer Versorgungswirksamkeit bewertet. **Nur PLAN 2030**: IST-Planstellen und PLAN-Sachleistungsstellen zählen Verschiedenes; der Vergleich bräuchte Annahmen (METHODIK.md, «Stellen»). Gemeinsame und zusätzliche Sachleistungsstellen sind verschiedene Stellen und dürfen addiert werden, anders als die IST-Planstellen (DATEN.md, Tabelle Stellen); die Seite sagt das, rechnet die Summe aber nicht selbst – sie steht nicht in der veröffentlichten Tabelle (außer Wiens gedruckter Gesamtzeile). **Ohne die Obergrenze für vertragsärztliche Planstellen** («davon maximal …»): Die Matrix druckt sie je Träger-Zeile. Eine Spalte nur für die gemeinsamen Stellen liest man als Obergrenze für alle, eine für alle wäre eine eigene Rechnung. Sie steht in der Tabelle Stellen (`Max_VAEP_Stellen`) Regions- und Fachseite zeigen dieselben Spalten: gemeinsam und zusätzlich je Träger, eine Spalte mit lauter 0 (ÖGK) entfällt. Nur die gemeinsamen Stellen zu zeigen, verzerrte den Vergleich der Regionen dort, wo ein Land viele trägerspezifische Stellen plant |
| Keine Grafik | Die Seiten zeigen Zahlen und Wörter, keine Grafik; das Bild (Hanteldiagramm) zeigt das Dashboard, verlinkt oben auf jeder Seite. Versucht und verworfen: eine kleine Hantel je Zeile mit der Achse des Dashboards. Sie wiederholte Lage und Zahlen daneben, das Intervall war darin nur ein schmaler Streifen, und sie verwischte die Teilung «nachschlagen hier, vergleichen dort» |
| Zahlen auf der Seite | ÄAVE, VD, Stellen und ÄAVE-Abstand mit **einer Nachkommastelle**, auch bei KJP und MKG: Der ÖSG druckt die Soll-Intervalle mit einer Stelle (0,8–1,4; Textband S.39), und genauer als die Quelle tut die Seite nicht. **Eine Stelle mehr**, wo die Rundung sonst etwas Falsches sagte: ein Wert ungleich 0 fiele auf «0,0» (Salzburg, KFO, IST: «0,04»); eine VD fiele genau auf VDmin oder VDmax, liegt aber außerhalb («1,59» statt «1,6» neben «1,6–3,0» und «unterhalb», Burgenland-Nord, PUL, PLAN). **Genau 0 als «0»**: «0,0» sähe aus wie «gerundet fast nichts», gemeint ist «nichts geplant» (in der Matrix «-»). Dieselbe Regel in Lesefassung und Dashboard (Detailspalte, Tooltip, Positions-Plot): `darstellung.lesbar` und `lesbar` in `app.js`; ein Test rechnet beide mit denselben Fällen, einer prüft jede Zelle der Seiten. Die Werte der Herkunft bleiben exakt (oben, «Werte der Herkunft») |
| Tabelle ÄAVE | je Fach **ÄAVE IST, ÄAVE PLAN 2030, Abstand PLAN 2030 zum Soll-Intervall**. Die ÄAVE sind, was in der Verordnung steht («Seite … öffnen» führt zu ihnen), deshalb sichtbar und nicht zum Aufklappen. Der Abstand ist in ÄAVE angegeben und steht bei seiner Einheit. Lage und Abstand stehen damit in zwei Tabellen; DATEN.md («Vergleich mit dem Soll-Intervall») will sie zusammen gelesen haben – die heiklen Fälle an der Grenze trägt deshalb die Zahl am Fach in der ersten Tabelle («weniger als 1 ÄAVE vom Intervall entfernt»). Rundet der Abstand auf 0,0, stehen zwei Nachkommastellen da («−0,02»): «−0,0» sähe aus wie ein Fehler, «0» hieße «im Intervall». Die Lage im IST zeigt nur das Dashboard |
| «Planstellen» im Titel | Der Titel nennt «Planstellen und Versorgungsdichte», weil das die gesuchten Begriffe sind; im Text steht die Beschriftung der Verordnung («Sachleistungsstellen»), dazu der Beleg, dass Niederösterreich diesen Teil seiner Matrix mit «PLAN Kassenstellen 2030» überschreibt |
| Bezirksnamen | in der Eckdatenzeile, mit dem Zusatz «geplant wird je Versorgungsregion, nicht je Bezirk» – es gibt keine Bezirkszahlen |
| Fußnoten | **gezählt, mit Link auf die Seite im PDF, nicht als Liste**: «Die Verordnung druckt zu dieser Matrix 7 Fußnoten (Seite 3: öffnen). Was davon die Werte hier betrifft, steht in den Hinweisen unter der Tabelle Versorgungsdichte.» – mit Link dorthin; «Vorbehalt» ist unser Wort in der Doku, auf der Seite hat die Liste keinen solchen Titel. Wo das Verzeichnis keine Fußnote der Matrix als wertrelevant einordnet, sagt der Satz das («Nach dem Fußnotenverzeichnis des Datensatzes ändert keine davon eine Zahl dieser Tabellen oder ihre Bedeutung»), damit niemand unter der Tabelle vergeblich sucht; ein Test prüft, dass die Fassung zum Verzeichnis passt. Wo ein Zeichen wie (2) im PDF hängt, steht nicht in `fussnoten.csv`; als Liste ohne Bezug waren die meisten nicht zuzuordnen – Mustertext der ÖSG-Vorlage («Vorlage»), Vertragsdetails («Hinweis»), «davon …»-Angaben («Teilmenge»). Ein Satz wie «zugeordnet zu CH» ohne Bezug lädt auch eine Zusammenfassung zum Falschzitieren ein. Was die Werte betrifft («betrifft Werte», «Methodenfrage»), steht schon bei der Tabelle: als Vorbehalt (ZAE, KFO in OÖ, Wien ZMK, OÖ spitalsambulant), im Zuschnitt («AM + ZAE») oder unter «Offene Fragen». Ein Test hält das für jede dieser Fußnoten fest. Im PDF stehen die Zeichen an ihrem Platz; das Verzeichnis mit Einordnung ist `fussnoten.csv` |
| Offene Fragen | **nur als Verweis**, nie als Text auf der Seite. Die Unsicherheit ist unsere, nicht die des Landes («Hier lässt sich aus der Verordnung allein nicht entscheiden, wie ein Wert gemeint ist», offene_punkte.md). Aufgezählt auf einer Seite, die den Namen des Landes in der Überschrift trägt, wäre eine Frage ein Befund gegen das Land – ein Urteil über die Fallstricke hinaus. Was eine Zahl wirklich betrifft, steht ohnehin als Vorbehalt oder Korrekturregel da |
| Prosa | so wenig wie möglich und ausschließlich vorlagengesteuert, jeder Satz aus den Daten abgeleitet. Keine Seite mit eigenem Text |
| Strukturierte Daten | **Ein `Dataset` für den Datensatz, auf `/daten/`** – auch über loesungswerk.at hinweg (offene_punkte.md, Webseite 6): mehrere Einträge für denselben Datensatz konkurrieren miteinander. Version, Datum (`CITATION.cff`) und Downloads kommen aus dem Release, die Downloads stehen in `RELEASE_DATEIEN`, ein Test prüft sie gegen `release.yml`. Jede Seite ist `WebPage`, Teil der `WebSite` `rsg.loesungswerk.at`. `/daten/` hat den Datensatz als `mainEntity`; Region, Land und Fach zeigen nur einen Ausschnitt daraus und verweisen mit `isBasedOn` darauf – ihr Thema ist die Region, nicht der ganze Datensatz. Urheber und Herausgeber: die Person mit derselben Kennung wie auf loesungswerk.at (`https://loesungswerk.at/#max-plischke`), ausgeschrieben, weil Google `@id` über Seiten hinweg nicht auflöst. JSON-LD wird aus Python-Daten erzeugt (`json.dumps`), nicht von Hand zusammengesetzt; ein Test parst jeden Block |
| Verbotene Urteile | «unterversorg…», «Versorgungsmangel», «Versorgungslücke», «Ärztemangel» brechen den Bau ab – auch in einer Verneinung, denn die geht beim Zusammenfassen verloren. «Lücke» allein ist erlaubt: So heißt die *Art* einer Korrekturregel |
| Sitemap: `lastmod` | der Tag der Veröffentlichung des Release, aus `CITATION.cff` – das einzige Datum, das eine echte Änderung der Seiten bedeutet. Das Baudatum wäre falsch: Es behauptete bei jedem Lauf eine Änderung, und ein `lastmod` in Höhe von «jetzt» wird ignoriert. Passt die Version in `CITATION.cff` nicht zur Paketversion, bleibt das Datum weg – lieber keine Angabe als eine falsche |
| Schrift und Tabellen | IBM Plex wie im Dashboard, aus `fonts/` neben den Seiten (`lesefassung` kopiert den Ordner selbst, falls `web` nicht lief); Zahlen in Plex Mono. Die erste Tabellenspalte bleibt beim seitlichen Scrollen stehen, ein Schatten am rechten Rand zeigt, dass es weitergeht (ohne Skript). Die Beschriftung der Tabelle bricht in Bildschirmbreite um. Ein stehender Tabellenkopf geht nicht: Ein seitlich scrollender Bereich ist auch senkrecht ein eigener (offene_punkte.md, Webseite) |
| Reihenfolge der Befehle | `web` baut das Dashboard, `lesefassung` die Seiten, beide nach `daten_ergebnis/web/`. `web` räumt nur seine eigenen Dateien weg, nicht das Verzeichnis – sonst nähme ein Lauf die 59 Seiten mit |

### Wer prüft was (Lesefassung)

| Was schiefgehen kann | Wer es findet |
|---|---|
| eine Vorlage passt nicht auf die Daten (16 statt 17 Fächer, fehlende Zeile) | Bau bricht ab: kein `{0}`, kein `nan`, kein `None` im HTML; Test über alle 59 Seiten |
| ein Urteil, das die Daten nicht tragen | Bau bricht ab (verbotene Wortstämme); Test |
| ein Vorbehalt fehlt dort, wo er gilt | Test: jede Seite nennt «nur die Sachleistung», «ohne Wahlärzt:innen» und «im Intervall kein Unterschied»; jede Regionstabelle den Zuschnitt und die Teilmengen, jede SVE-Matrix den Block der ÄAVE-Äquivalente |
| eine Zahl weicht von der Tabelle ab | Test: jede ÄAVE- und VD-Zahl der Zeile «insgesamt» steht zeichengleich auf der Seite (über 1.000 Werte) |
| Fußnote, die Werte betrifft, fehlt auf der Seite | Test: jede Fußnote «betrifft Werte» oder «Methodenfrage» ist auf der Seite ihrer Matrix berücksichtigt (Vorbehalt, Zuschnitt oder Link auf die offenen Punkte), je Art des Verweises ein Merkmal; ein Verweis neuer Art lässt den Test scheitern |
| Korrekturregel umformuliert oder der falschen Matrix zugeordnet | Test: jede Begründung steht zeichengleich aus `korrekturen.csv` auf der Seite ihrer Matrix |
| Fußnotenzahl falsch, ein Fußnotentext steht doch auf der Seite, oder der Satz verweist auf Hinweise, die es nicht gibt | Test: Zahl wie im Verzeichnis, kein Text über 40 Zeichen aus `fussnoten.csv` im HTML; der Verweis auf die Hinweise nur, wo eine Fußnote «betrifft Werte» oder «Methodenfrage» ist, sonst der Satz, dass keine es tut |
| eine Zahl ist gerundet irreführend (VD auf der Grenze, obwohl außerhalb; «0,0» für einen Wert ungleich 0; «0,00» für genau 0) | Test: die Fälle aus `tests/test_web.py` gegen `darstellung.lesbar`; jede Zelle mit Lage «unter» oder «über» auf allen Seiten; genau 0 steht nur als «0» |
| die Fußzeile läuft vom Dashboard weg | Test: jede Seite trägt zeichengleich den Text aus `darstellung.fusszeile` |
| `Dataset` unvollständig, oder ein Download, den das Release nicht hat | Test: Pflichtfelder (Name, Beschreibung, Lizenz, Urheber, Version, Größen, Downloads); jede Datei der `distribution` steht in der Liste, die `release.yml` ans Release hängt |
| JSON-LD ungültig, oder eine Seite hängt nicht am Datensatz | Test: jeder Block wird geparst; jede Seite ist Teil der `WebSite`, `/daten/` hat den Datensatz als `mainEntity`, alle anderen `isBasedOn` |
| der ÖSG-Link führt auf eine andere Datei oder Seite | Test: Seite wie in der Spalte «Quelle» der Richtwerte, Datei die, die `quellen.csv` als Textband führt; der Link steht auf jeder Fachseite |
| `robots.txt` nennt die Sitemap nicht oder sperrt etwas | Test |
| die Adresse der Seiten ändert sich still | Test: `BASIS_STANDARD` ist `https://rsg.loesungswerk.at` – indexierte Seiten verlören sonst ihren Platz |
| Vorbehaltstexte laufen vom Dashboard weg | Test: kein Vorbehaltstext steht in `lesefassung.py` – alle kommen aus `darstellung.py` |
| eine Seite ist nicht auffindbar | Test: jede Seite ist von `/daten/` verlinkt und steht in der Sitemap; jede hat Titel, `<h1>`, `description` und `canonical`; jede außer `/daten/` hat Brotkrumen; das Dashboard verlinkt `/daten/` fest im HTML |
| ein Vorbehalt fehlt unter der Tabelle, steht doppelt, oder eine Zahl an einer Zeile führt ins Leere | Test: jeder Vorbehalt der Region steht genau einmal unter der Tabelle, und die Zahlen an den Zeilen sind genau die darunter |
| «−0,0» oder eine andere Null mit Vorzeichen in einer Tabelle | Test: auf keiner Seite |
| die Seite verliert den Weg ins Dashboard | Test: jede Seite trägt die Bereichsleiste mit beiden Wegen, Region und Fach mit vorbelegtem Zustand |
| ein Fragetext aus offene_punkte.md landet auf einer Seite, oder die Sprungmarke führt ins Leere | Test: kein Fragetext im HTML; wo ein Verweis steht, gibt es die Überschrift in offene_punkte.md, und die Sprungmarke passt dazu |
| `lastmod` behauptet eine Änderung, die es nicht gab | Test: entweder trägt jede Adresse das Datum aus `CITATION.cff`, oder keine trägt eines |
| eine Adresse ändert sich und bricht alle Links | Test: Adressen sind Nummern und Kürzel nach festem Muster |
| die Seite lädt etwas von fremden Servern, oder ein Link verrät die Herkunft | Test: kein `<script>` außer JSON-LD, nur bekannte Ziele, jeder Link nach außen mit `target="_blank" rel="noopener noreferrer"` – und jeder interne Link **ohne** `target` |
| die Seiten sind unverständlich oder im Ton falsch | der Herausgeber: drei Seiten lesen (eine Region, ein Fach, die Indexseite), am Desktop und am Handy |

## Wörter für das Soll-Intervall

Für Dashboard und Lesefassung gleich, damit neue Texte nicht auseinanderlaufen. Grundlage: Der ÖSG nennt das
Intervall «Versorgungsdichte-Soll-Intervall» (Textband S.38, Legende S.37) und seine Grenzen in der Tabelle der
Richtwerte «VDmin» und «VDmax» (Textband S.39); das Glossar in METHODIK.md verbindet beide.

| Gemeint ist | Wort | Beispiele |
|---|---|---|
| das Intervall als Ganzes | **Soll-Intervall** (beim ersten Vorkommen «Soll-Intervall des ÖSG») | Spaltenkopf «Soll-Intervall», Lage «unter dem Soll-Intervall», Fließtext |
| eine einzelne Grenze als Zahl oder Begriff; die Erklärung «(dort VDmin–VDmax)» einmal in der Lesehilfe, nicht in Spaltenköpfen | **VDmin / VDmax** – die Spaltennamen des ÖSG, die man dort und in der CSV wiederfindet | Hanteldiagramm «VDmin 34,9», Position «0 = VDmin, 1 = VDmax», Spalten, wenn die Grenzen getrennt stehen |
| eine Grenze im Satz in Worten | **Untergrenze / Obergrenze** – unsere Umschreibung, kein ÖSG-Begriff, nur wo ein Satz natürlicher liest | «Bis zur Untergrenze fehlen 13,5 ÄAVE Sachleistung» (`darstellung.py`) |
| die Lage in einer schmalen Spalte | **unterhalb / innerhalb / oberhalb**, mit «Lage zum Soll-Intervall» im Kopf – Wörter, die für sich stehen («im» allein ist kein Deutsch) | Tabellen der Lesefassung |

Das Dashboard schreibt in Legende und Detailspalte «unter VDmin» / «über VDmax». Das ist richtig und bleibt: Die
Pillen sind schmal, und eine längere Lage änderte die Gestaltung für einen kleinen Gewinn. Neue Texte folgen der
Tabelle oben.

## Der Satz und die Vorbehalte stehen einmal

Zu jeder Zelle gehören zwei Texte, die nicht aus den Daten kommen, sondern Festlegungen der Darstellung sind: **der
Wert in Worten** («Bis zur Untergrenze fehlen … ÄAVE Sachleistung») und die **Vorbehalte**, die für diese Zelle
gelten. Beide stehen in [`rsg2030/darstellung.py`](../rsg2030/darstellung.py) – einmal, für jede Darstellung des
Datensatzes:

- `web.py` schreibt die Texte nach `data.json` (`vorbehalt_texte`, `satz_vorlagen`) und dazu je Zelle, **welche**
  Vorbehalte gelten (`vorbehalte`, Kennung und Argumente); `app.js` setzt nur noch ein.
- Die statischen Seiten nehmen die Vorbehalte direkt. Den Wert in Worten zeigen sie nicht mehr: Er wiederholte
  die Tabelle in Prosa (siehe «Lesefassung», «Aufbau»).

Warum nicht in `app.js`, wo sie standen: Vorbehalte folgen den Daten (CLAUDE.md). Ändert sich die Lesart einer
Fußnote, muss ein Text an einer Stelle nachgezogen werden, nicht an zwei – zwei Kopien laufen auseinander, und
niemand merkt es. Nicht mitgewandert sind Farbstufen, Schraffur und Zahlformate: Die statischen Seiten haben keine
Farben, und jede Darstellung formatiert Zahlen selbst. Geteilt ist nur, was wörtlich gleich sein muss.

Die Texte enthalten HTML und Platzhalter (`{0}`, `{1}` …). Eingesetzt wird nur, was aus den Daten kommt (Name des
Landes, IST-Jahr, Fach), und das wird maskiert.

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
    zu den Daten (z. B. fehlende Spalte), bricht er ab, und die bisherige Seite bleibt. Den Datenstand nennt die
    Fußzeile als Link aufs Release, den Stand der Seite als Commit; die Prüfsummen stehen in `data.json`. Für Änderungen an der Seite braucht es kein neues Release.
15. **Wer die Seite erstellt hat, steht in der Fußzeile**, mit den Vorbehalten gleich dahinter: ohne Auftrag
    aufbereitet, aus den Verordnungen im RIS; keine amtliche Veröffentlichung, maßgeblich sind die Verordnungen
    selbst; Angaben ohne Gewähr. «Ohne Auftrag» sagt, dass niemand die Aufbereitung bestellt hat – im
    Gesundheitswesen haben Länder, Kassen und Kammern Interessen an solchen Zahlen, und der Herausgeber arbeitet als
    Berater. Genauer als «auf eigene Initiative» (ließe offen, ob jemand zahlt); «unabhängig» behauptete mehr, als
    sich belegen lässt. Nicht «amtliche Daten»
    (die Quellen sind verschieden: Verordnungen, amtliche Statistik, ÖSG) und nicht «inoffiziell» (klingt nach
    nicht erlaubt). Die Seite liegt unter einer eigenen Adresse, nicht beim Repo; wer sie ohne das README
    öffnet, muss sie dort einordnen können. Dazu die Links auf Impressum und Datenschutz, die eine veröffentlichte
    Seite braucht. Mehr nicht: kein Logo, kein Werbetext, keine Kennzahl und kein Urteil, das nicht in der Doku
    steht. Die drei Links trägt die Fußzeile wie alle anderen mit `noreferrer`, und die Seite lädt weiterhin nichts
    von fremden Servern («Wer prüft was»). Sinngemäß derselbe Satz steht im README («Versionen und Zitieren»).
    **Dashboard und Lesefassung haben dieselbe Fußzeile**, aus einer Funktion (`darstellung.fusszeile`; das
    Dashboard bekommt sie über `data.json`, Test in beiden Testdateien): ein Satz, wer sie erstellt hat; eine Zeile
    Links (Release, CC BY 4.0, Methodik, Zitieren, Fehler melden, Impressum, Datenschutz); die Quellen. Zwei
    verschiedene Fußzeilen für dieselbe Herkunft und dieselbe Haftung verwirrten nur. Der Name verlinkt auf die
    Personenseite beim Herausgeber (für eine Suchmaschine ein klareres Zeichen, wer hinter den Zahlen steht, als
    eine Nummer); «Lösungswerk» steht nicht dabei – das sagen die Adresse `rsg.loesungswerk.at`, Impressum und
    Datenschutz. Im README steht es, dort fehlt die Adresse.
    Die ORCID steht in den strukturierten Daten (`creator`), nicht sichtbar auf jeder Seite; der Satz zur Methode
    einmal auf `/daten/`.
    **Dazu in beiden Darstellungen eine Zeile «Quellen»** im Wortlaut von LIZENZ_DATEN.md: Die Bevölkerung von
    Statistik Austria und die ÖROK-Prognose stehen unter CC BY 4.0 und gehen bearbeitet in die Versorgungsdichte
    ein; die Lizenz verlangt die Nennung bei jeder Veröffentlichung, ein Link auf die Methodik reicht nicht. Der
    Text steht als `NAMENSNENNUNG` in `darstellung.py`, als Teil der gemeinsamen Fußzeile.

## Aufbau

```
web/                  die Seite: index.html, app.js, style.css
  fonts/                IBM Plex, selbst ausgeliefert (Lizenz SIL OFL, fonts/README.md)
  kacheln.csv           je Region Spalte und Zeile der Kachelkarte und die Beschriftung der Kachel (VR und BL)
  faecher.csv           Fächer in der Reihenfolge der Spalten, Name, «Teil von» (PUL → IM, KFO → ZMK)
rsg2030/darstellung.py  der Wert in Worten und die Vorbehalte je Zelle – einmal für jede Darstellung (siehe oben)
rsg2030/lesefassung.py  «python -m rsg2030 lesefassung»: die 59 statischen Seiten und die Sitemap
web/lesefassung/        lesefassung.css – ein Stil, keine Schrift von außen, keine Farbe mit Bedeutung
rsg2030/web.py        «python -m rsg2030 web»: Tabellen Versorgungsdichte und Planungsmatrizen → data.json,
                        Seite nach daten_ergebnis/web/; `baue_herkunft` baut den Herkunfts-Teil
rsg2030/korrekturen.py  `regel_fuer_zelle`: welche Regel aus korrekturen.csv eine korrigierte Zelle erklärt
rsg2030/scripts/rohtext_eindeutig.py   belegt, warum die Seite die Zahl im PDF nicht markiert
tests/test_web.py     Kacheln, Fächer, Vorbehalte, Farben, data.json, Herkunft (siehe «Wer prüft was»)
tests/test_lesefassung.py   Adressen, Vorlagen, Zahlen und Apparat der Lesefassung
.github/workflows/webseite.yml   bauen und auf GitHub Pages veröffentlichen
```

Die fertige Seite liegt wie alle Ergebnisse nicht in git. Die Seite lädt `data.json` und rechnet nichts nach; jede
Angabe hat eine Quelle: Werte und Soll-Intervalle aus der Tabelle Versorgungsdichte, Rohtexte, PDF, Seite und
Zeilenbeschriftung aus der Tabelle Planungsmatrizen, Art und Begründung einer Regel aus `korrekturen.csv`, die Adresse
der Verordnung aus der Dokumentnummer in `quellen/quellen.csv`, Namen der Regionen und Länder aus `oesg_regionen.csv`,
Namen der Fächer aus `web/faecher.csv`, Lage der Kacheln aus `web/kacheln.csv`. Der Kopf nennt das Release aus `data.json`; die
Fußzeile kommt fertig aus `data.json` (`fusszeile`, aus `darstellung.py`, dieselbe wie in der Lesefassung): wer die
Seite erstellt hat, die Vorbehalte dazu, die Links und die Quellen (Entscheidung 15).

## Selbst bauen und ansehen

```bash
.venv/bin/python -m rsg2030 web                          # braucht RSG_2030_Versorgungsdichte.csv und
                                                         # RSG_2030_Planungsmatrizen.csv in daten_ergebnis/
.venv/bin/python -m rsg2030 lesefassung                  # die statischen Seiten dazu (braucht auch
                                                         # RSG_2030_Stellen.csv); «--basis» setzt die Adresse
.venv/bin/python -m http.server -d daten_ergebnis/web    # dann http://localhost:8000 im Browser,
                                                         # die Lesefassung unter /daten/
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
| Vorbehalt oder Satz stehen doppelt (Python **und** app.js) und laufen auseinander | Test: kein Text aus `darstellung.py` kommt in `app.js` vor |
| die Fußzeile steht doppelt (Python **und** app.js) | Test: `app.js` setzt die Fußzeile aus `data.json` (`D.fusszeile`) und trägt keine eigene Namensnennung |
| das Dashboard rundet anders als die Lesefassung | Test: dieselben Fälle durch `lesbar` in `app.js` (mit node gerechnet) und `darstellung.lesbar`; ohne node übersprungen, die CI hat node |
| eine Suchmaschine zählt `?region=…&fach=…` als eigene Seiten oder findet die Lesefassung nicht | Test: `canonical` auf die Wurzel der eigenen Domain; der Link auf `/daten/` steht fest in `index.html` unter «Über diese Daten», und `app.js` überschreibt den Abschnitt nicht |
| eine Zelle ohne Wert hat keinen Grund und keinen Sprung in die Quelle | Test: zu jeder Zelle ohne Wert gibt es einen Grund und einen Matrix-Eintrag mit PDF und Seite |
| ein Platzhalter bleibt leer, «{0}» steht auf der Seite | Test: je Zelle passen die Argumente zu den Platzhaltern des Textes, und keines ist leer |
| Farbstufen nicht unterscheidbar | Test: Abstände benachbarter Stufen aus `style.css` nachgerechnet, normal und bei Protanopie und Deuteranopie, hell und dunkel; dunkle Farben gleich, ob über die Systemeinstellung oder den Schalter |
| Seite gibt etwas an fremde Server (z. B. Schriften von Google: IP-Adresse jeder Besucherin dorthin) | Tests: keine Schriften, Skripte oder Stile von außen, jede Schrift der CSS liegt in `web/fonts/`; jeder Link nach außen trägt `noreferrer`, gibt also nicht weiter, von welcher Seite jemand kam |
| Link auf Lösungswerk, Impressum oder Datenschutz führt ins Leere | der Herausgeber: Die drei Adressen führen auf die eigene Website. Kein Test ruft sie auf, denn weder die Seite noch ihr Bau sollen fremde Server befragen |
| Seite lädt nicht, Fehler im Skript, Seite am Handy breiter als der Bildschirm | ein Mensch vor der Veröffentlichung; später ein Test im Browser |
| ein Vorbehalt ist fachlich falsch oder missverständlich formuliert | der Herausgeber |
