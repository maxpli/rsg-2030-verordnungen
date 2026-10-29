# Offene Punkte

Was an den Daten noch offen ist. Offene Fragen zur **ÖSG-Methodik** stehen in
[METHODIK.md](METHODIK.md#bekannte-grenzen-und-offene-fragen). Eingaben und Doku verweisen auf die Abschnitte über
ihren Namen (in `fussnoten.csv` z. B. `offene_punkte.md «Unklare Angaben in den Verordnungen»`); die Überschriften
bleiben daher fest. Was erledigt ist, wird entfernt; das CHANGELOG hält fest, was sich dadurch an den Daten geändert
hat.

## Unklare Angaben in den Verordnungen

Hier lässt sich aus der Verordnung allein nicht entscheiden, wie ein Wert gemeint ist. Wir haben uns für eine Lesart
entschieden und sie dokumentiert; bestätigen kann sie nur das jeweilige Land. Was eindeutig war, ist korrigiert und
steht nicht hier. Antworten nehmen wir gern als Issue entgegen.

### Burgenland (Anlage 1, S.1, S.3, S.8)

1. **AU, PLAN 2030, Bundesland-Matrix:** Dort steht extramural 14,5 und insgesamt 18,5 ÄAVE. Die beiden
   Versorgungsregionen ergeben zusammen 15,5 und 19,5 (VR 11: 8,0 und 11,2; VR 12: 7,5 und 8,3). Wir haben die Summe
   der Regionen übernommen.
   *Frage: Gelten die Werte der Regionen?*
2. **Zeile «SVE spitalsambulant», PLAN 2030, Bundesland-Matrix:** Die Werte sind in jedem Fach die Summe der
   ÄAVE-Äquivalente der Regionen, nicht die Summe ihrer SVE (gesamt 98,2 statt 48,2). Wir halten das für einen
   Übertragungsfehler und haben die Summe der SVE eingesetzt.
   *Frage: Ist das richtig?*
3. **Umrechnung SVE → ÄAVE-Äquivalente, spitalsambulant, PLAN 2030:** Bei IM passen die gedruckten Werte nicht zu den
   gedruckten Faktoren. In VR 11 ergibt 5,8 SVE × 2,4 = 13,9, gedruckt sind 11,9. In VR 12 ergibt 3,5 × 4,2 = 14,7,
   gedruckt sind 8,8. Bei AU gibt es nur einen Faktor für das Bundesland (5,0), und der passt zu keiner Region. Wir
   haben die gedruckten Werte übernommen.
   *Frage: Mit welchen Faktoren wurde bei IM und AU umgerechnet, und gelten die gedruckten Werte?*

### Kärnten (Anhang, S.97)

**KFO, IST, Bundesland-Matrix:** In der Zeile «insgesamt» steht bei KFO «-», obwohl bei den Niedergelassenen 12,1 ÄAVE
stehen. Die Summe «insgesamt gesamt» (939,2) enthält diese 12,1 nicht. Wir haben «insgesamt» aus den Teilzeilen
zusammengezählt: KFO 12,1, gesamt 951,3.
*Frage: Gehört KFO in die Summe «insgesamt», oder wurde sie bewusst weggelassen?*

### Oberösterreich (Anlage, S.9–27)

1. **KFO:** KFO hat in der Matrix keine eigene Spalte, sie steht in der Fußnote zu ZMK: «zusätzlich KFO: IST 2022 und
   Plan 2030: 38,2 ÄAVE bzw. 32 vertragskieferorthopädische Planstellen SV» (S.10; je Region eigene Zahlen auf
   S.12–27). Wir zählen die 38,2 ÄAVE im IST und im PLAN zu den Niedergelassenen mit Kassenvertrag und zu
   «insgesamt»; die 32 Planstellen im IST zu jeder Träger-Zeile (ÖGK, SVS, BVAEB) und im PLAN zu den gemeinsamen
   Sachleistungsstellen, mit 100 % Maximalanteil vertragsärztlicher Planstellen.
   **Aus dem Dokument belegt** ist davon zweierlei – dass die Zahlen zusätzlich sind und welche Träger gemeint sind –,
   und zwar auf den Bezirksseiten derselben Anlage (S.13, 16, 19, 22, 25, 28): Dort steht je Bezirk «ZMK – zuzügl. in Kieferorthopädie (KFO): *n* vertragskieferorthopädische
   Planstellen: ÖGK, SVS, BVAEB». Das sind die Träger, und «zuzügl.» heißt zusätzlich – in derselben Zeile steht für
   ORTR «davon in Unfallchirurgie (UC)». Die Bezirkswerte ergeben je Seite die Zahl der VR-Fußnote und zusammen 32.
   **Offen sind drei Punkte:** ob die 38,2 ÄAVE niedergelassen mit Kassenvertrag sind (die Fußnote nennt keinen
   Sektor), die PLAN-Zuordnung zu den gemeinsamen Sachleistungsstellen und der Maximalanteil von 100 %. Welches Indiz
   wofür trägt, steht in [PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), «Steckt KFO schon in der
   gedruckten ZMK-Spalte?»; die Umsetzung in [METHODIK.md](METHODIK.md), R4.
   *Frage: Sind die 38,2 ÄAVE niedergelassen mit Kassenvertrag, und gelten sie für IST und PLAN gleichermaßen? Sind
   die 32 Planstellen im PLAN gemeinsame Sachleistungsstellen – und dürfen alle als Kassenpraxis besetzt werden
   (100 %)?*
2. **ÖGK-Zahngesundheitszentrum (nur Bezirksseite S.13, Linz Stadt):** Dort steht hinter den KFO-Planstellen
   «+ 2,2 Sachleistungsstellen in ÖGK-Zahngesundheitszentrum» – eine Zahl, die auf keiner BL- oder VR-Seite vorkommt
   (Test: `tests/test_fussnoten.py::test_ooe_zahngesundheitszentrum_nur_auf_der_bezirksseite`). Die Fußnoten dort
   nehmen stattdessen ein nicht beziffertes «zahnärztliches Notdienstzentrum Linz» aus ZMK heraus (S.10, S.12).
   **Hypothese:** Beides ist dieselbe Einrichtung, und die Bezirksseite beziffert, was die Matrix-Fußnote nur
   ausnimmt. *Dafür:* Die Ausnahmen der Fußnoten liegen dort, wo die Verordnung sie nennt – das Bundesland nennt
   Notdienstzentrum Linz **und** Vorgriffstelle Steyr, die VR 41 nur Linz, die VR 44 nur Steyr, und laut ÖSG-Referenz
   besteht die VR 41 aus Linz (Stadt) und Linz-Land, die VR 44 aus Steyr (Stadt) und zwei weiteren Bezirken. Die 2,2
   stehen genau auf der Bezirksseite von Linz (Stadt) und dort mit «+», also als Zusatz, passend zum «exkl.» der
   Fußnote. *Dagegen:* Die Namen sind verschieden – ein Notdienstzentrum ist ein Dienst, ein Zahngesundheitszentrum
   eine eigene Einrichtung der ÖGK, also ein Kassenambulatorium. Dessen ÄAVE gehören nach ÖSG in die Zeile der
   Kassenambulatorien (R2a, D1), und OÖ druckt dort ZMK 79,1, was mit dem RSG-Monitoring auf die Stelle übereinstimmt;
   die ärztlichen Vollzeitäquivalente von Ambulatorien gehören nach Tabellenband S.232 ohnehin in die
   Sachleistungsstellen, könnten also in den gedruckten 480,3 des PLAN schon enthalten sein.
   Entscheiden lässt sich das nicht: Eine zweite Quelle gibt es nicht (das Monitoring führt weder PLAN noch
   Sachleistungsstellen). Wir haben nichts ergänzt – die Bezirke sind keine Ebene dieses Datensatzes, und jede
   Zuordnung wäre geraten.
   *Frage: Ist das ÖGK-Zahngesundheitszentrum das in den Fußnoten ausgenommene zahnärztliche Notdienstzentrum Linz –
   und sind die 2,2 Sachleistungsstellen in den ZMK-Werten des Bundeslands und der VR 41 enthalten oder nicht?*
3. **Zusätzliche SVS-Sachleistungsstellen URO (S.9 Bundesland, S.11 VR 41):** Dort stehen 1,5 Stellen, das Feld für den
   Maximalanteil vertragsärztlicher Planstellen (in Prozent) ist leer – URO ist das einzige Fach dieser Zeile mit
   Stellen, aber ohne Prozentsatz. Wir lesen es als 0 %, weil 0 % in dieser Zeile der häufigste gedruckte Wert ist
   (Bundesland 4 von 12 Fächern mit Prozentsatz, VR 41 6 von 12); aus einer anderen Zahl folgt der Wert nicht
   (Bundesland = VR 41). Es ist also eine Lesart, keine Herleitung. Folge: Das gesamt-% der Zeile wird abgeleitet.
   *Frage: Welcher Maximalanteil gilt?*

### Steiermark (Anlage 1, S.1)

**ZMK, IST, vertragsärztliche Planstellen:** Gedruckt sind 358 ÖGK-Planstellen in ZMK und 25 in KFO, zusammen 383. Das
RSG-Monitoring der GÖG weist für dasselbe Jahr 407 ÖGK-Planstellen in ZMK aus, dort ausdrücklich «inkl. KFO»; in den
übrigen Fächern stimmen die Planstellen bis auf CH (4 gegenüber 0) und die technischen Fächer überein
([PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), «Vertragsärztliche Planstellen»). Woher die 24 Stellen
Unterschied kommen, sagt die Verordnung nicht; wir haben die gedruckten Werte übernommen.
*Frage: Was zählen die ZMK-Planstellen der Verordnung – auch Zahnbehandler:innen und Dentist:innen, die Wien in
Fußnote (5) ausdrücklich zu ZMK rechnet?*

### Tirol (Anlage, S.1, S.3, S.5, S.7, Fußnote (7))

**Zentrale Aufnahme- und Erstversorgungseinheiten (ZAE):** Die Fußnote lautet «davon 4,8 VZÄ in der AM, 1 VZÄ in der
KIJU und 2,25 VZÄ in der ORTR durch L-ZK als zusätzliche SLS der SV anrechenbar». Wir lesen das als Anrechnung von
Personal als Sachleistungsstellen und zählen alle ZAE-ÄAVE zu AM, wie es der ÖSG vorsieht (Textband S.39).
*Frage: Ist das so gemeint? Oder versorgen diese Anteile der ZAE tatsächlich Kinder (KIJU) und
Orthopädie/Traumatologie (ORTR), sodass sie dort zu zählen wären?*

### Vorarlberg (Anlage, S.1, S.3, S.5)

1. **ZMK, PLAN 2030, gemeinsame Sachleistungsstellen:** Der Maximalanteil vertragsärztlicher Planstellen ist im
   Bundesland mit 90 % angegeben (128 Stellen). Die Regionen haben 89 % (VR 81, 71 Stellen) und 96 % (VR 82, 57
   Stellen); gewichtet ergibt das 92,1 %. Damit kommt man auf höchstens 115,2 bzw. 117,9 Kassenstellen. Wir haben die
   gedruckten 90 % übernommen.
   *Frage: Welcher Wert gilt für das Bundesland?*
2. **ZMK, IST, vertragsärztliche Planstellen:** Gedruckt sind 110 ÖGK-Planstellen. KFO hat keine eigene Spalte und
   ist laut Textteil in ZMK enthalten: «Zahn-, Mund- und Kieferheilkunde (ZMK; einschließlich Kieferorthopädie,
   KFO)», und das gilt dort ausdrücklich für «IST-Standdarstellung und Kapazitätsplanung»
   (`4_VO_RSG_Vbg_2025_Textteil_RSG_zur_Erlaeuterung.pdf`, PDF-Seite 4 = Dokumentseite 1, Abschnitt «Hinweis»; KFO
   kommt in der Anlage nicht vor). Das RSG-Monitoring weist 123 ÖGK-Planstellen «inkl. KFO» aus. Anders als in
   den übrigen Ländern weicht Vorarlberg aber auch sonst in vielen Fächern ab, und das Monitoring druckt dort
   Planstellen mit Nachkommastellen (AM 158,4 gegenüber 160) – der Unterschied bei ZMK steht also nicht für sich
   ([PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring)). Die 13 Stellen liegen in der Größenordnung einer
   KFO-Spalte (Tirol 18 von 246, NÖ 37 von 502); die ZMK-ÄAVE passen dagegen ins Muster der Länder, deren ZMK KFO
   enthält (+13,8 % gegenüber dem Monitoring, NÖ +13,5 %, Tirol +13,5 %). Wir haben die gedruckten Werte übernommen.
   Der Textteil hilft hier nur zur Hälfte: Er rechnet die Kieferorthopädie zum Planungsbereich «Zahnärztliche
   Versorgung» und sagt, dieser sei «im IST 2023 in ÄAVE abgebildet» und für 2030 «in Sachleistungsstellen
   übergeleitet» (PDF-Seite 19 = Dokumentseite 16). Beide Aussagen betreffen ÄAVE und PLAN-Sachleistungsstellen – die
   vertragsärztlichen Planstellen des IST, also genau die Zeile mit dem Unterschied, kommen dort nicht vor.
   **Für die Daten ist hier nichts zu entscheiden:** Die Anlage nennt nirgends eine KFO-Zahl, es gibt also nichts zu
   ergänzen; wir übernehmen die gedruckten Werte, und laut Textteil ist KFO in ZMK enthalten. Offen ist nur, woher der
   Unterschied zum Monitoring kommt – eine Frage an das Land, keine Entscheidung von uns.
   *Frage: Enthalten die ZMK-Planstellen im IST die Kieferorthopädie, wie der Textteil es für die ÄAVE und die
   Sachleistungsstellen sagt?*

### Alle Länder: Bezugswert der niedergelassenen ÄAVE

Im Vergleich mit dem RSG-Monitoring der GÖG liegen die niedergelassenen ÄAVE im IST höher. Je Fach ist der Unterschied
verschieden groß, aber in allen Ländern mit demselben IST-Jahr fast gleich; Oberösterreich liegt darüber.
Spitalsambulanzen, Ambulatorien und Wahlärzt:innen stimmen überein (Zahlen:
[PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), «Abgleich mit dem RSG-Monitoring»). Ein gleicher Zuschlag
je Fach spricht dafür, dass mit einem anderen Bezugswert gerechnet wurde («durchschnittlich arbeitende Ärztin/Arzt»,
DAA; METHODIK R8).
*Frage: Mit dem DAA welchen Jahres sind die niedergelassenen ÄAVE der Verordnung gerechnet, in Oberösterreich und in
den übrigen Ländern?*

Niederösterreich, Salzburg, Wien: keine offene Frage zur eigenen Verordnung.

## Zweite Durchsicht (Beiträge willkommen)

Die Freigabe hat bisher eine Person gemacht. Eine unabhängige Durchsicht durch eine ÖSG-kundige Person würde die
Daten weiter absichern, vor allem des Blatts «Entscheidungen» in `freigabe.xlsx` (Korrekturen, bekannte Abweichungen,
Ableitungen) und der Methodik (METHODIK.md, R1–R10). Wer beitragen will: Issue «Frage zur Methodik» oder «Wert weicht
vom PDF ab».

## Mögliche Erweiterung: Wahlärzt:innen extramural

«Summe extramural inkl. Wahlärzt:innen» weist nur Wien aus, die Wahlärzt:innen-Zeile ist optional und nur in 6
Ländern im IST befüllt, im PLAN nach ÖSG nie (METHODIK.md, R1 und «Bekannte Grenzen» 1). Heute wird die Summe nur
geprüft, wo sie steht (Wien), nicht abgeleitet. Für alle Länder bräuchte es eine zweite Datenquelle, z. B.
Wahlärzt:innen im IST-Jahr übernehmen und für 2030 als Szenario fortschreiben (gleiche Zahl oder gleiche Dichte) – als
eigene, gekennzeichnete Größe, nicht als Wert der Verordnungen. Eine solche Quelle ist das RSG-Monitoring der GÖG
(Zeile «ÄAVE WahlärztInnen», je Land und Jahr; PRUEFUNG.md, «Abgleich mit dem RSG-Monitoring»).

## Webseite

Was an der Webseite ([WEB.md](WEB.md)) noch offen ist.

1. **Weitere Zeilen der Tabelle Versorgungsdichte zeigen?** Heute nur `insgesamt`. Möglich wären `spitalsambulant` und
   `extramural` (Aufteilung, ohne Soll-Intervall; Fallstrick 10), `pve` (nur AM und KIJU, im PLAN Mindestwert) und die
   Veränderung IST → PLAN. Offen ist, was davon die Seite tragen soll, ohne unübersichtlich zu werden.
2. **Herkunft je Wert zeigen?** In der Detailspalte «Woher kommen diese ÄAVE?»: PDF, Seite, Originaltext und, wo
   korrigiert wurde, die Regel – aus der Tabelle Planungsmatrizen. Das zeigte, was den Datensatz ausmacht, braucht aber
   die zweite, große Tabelle in der Seite, mit eigenen Tests. Ebenso denkbar: eine Ansicht der Matrizen selbst.
3. **Test im Browser:** Seite lädt ohne Fehler, keine seitliche Verschiebung bei Handy-Breite. Bis dahin prüft das ein
   Mensch.
