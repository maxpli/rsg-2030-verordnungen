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

1. **KFO:** KFO hat keine eigene Spalte, sie steht nur in der Fußnote zu ZMK: «zusätzlich KFO: IST 2022 und Plan 2030:
   38,2 ÄAVE bzw. 32 vertragskieferorthopädische Planstellen SV» (S.10; je Region eigene Zahlen auf S.12–27). Wir
   zählen die 38,2 ÄAVE im IST und im PLAN zu den Niedergelassenen mit Kassenvertrag und zu «insgesamt».
   *Frage: Sind die 38,2 ÄAVE niedergelassen mit Kassenvertrag, und gelten sie für IST und PLAN gleichermaßen?*
2. **Zusätzliche SVS-Sachleistungsstellen URO (S.9 Bundesland, S.11 VR 41):** Dort stehen 1,5 Stellen, das Feld für den
   Maximalanteil vertragsärztlicher Planstellen (in Prozent) ist leer. Wir lassen es leer.
   *Frage: Welcher Maximalanteil gilt?*

### Tirol (Anlage, S.1, S.3, S.5, S.7, Fußnote (7))

**Zentrale Aufnahme- und Erstversorgungseinheiten (ZAE):** Die Fußnote lautet «davon 4,8 VZÄ in der AM, 1 VZÄ in der
KIJU und 2,25 VZÄ in der ORTR durch L-ZK als zusätzliche SLS der SV anrechenbar». Wir lesen das als Anrechnung von
Personal als Sachleistungsstellen und zählen alle ZAE-ÄAVE zu AM, wie es der ÖSG vorsieht (Textband S.37).
*Frage: Ist das so gemeint? Oder versorgen diese Anteile der ZAE tatsächlich Kinder (KIJU) und
Orthopädie/Traumatologie (ORTR), sodass sie dort zu zählen wären?*

### Vorarlberg (Anlage, S.1, S.3, S.5)

**ZMK, PLAN 2030, gemeinsame Sachleistungsstellen:** Der Maximalanteil vertragsärztlicher Planstellen ist im
Bundesland mit 90 % angegeben (128 Stellen). Die Regionen haben 89 % (VR 81, 71 Stellen) und 96 % (VR 82, 57 Stellen);
gewichtet ergibt das 92,1 %. Damit kommt man auf höchstens 115,2 bzw. 117,9 Kassenstellen. Wir haben die gedruckten
90 % übernommen.
*Frage: Welcher Wert gilt für das Bundesland?*

### Alle Länder: Bezugswert der niedergelassenen ÄAVE

Im Vergleich mit dem RSG-Monitoring der GÖG liegen die niedergelassenen ÄAVE im IST höher. Je Fach ist der Unterschied
verschieden groß, aber in allen Ländern mit demselben IST-Jahr fast gleich; Oberösterreich liegt darüber.
Spitalsambulanzen, Ambulatorien und Wahlärzt:innen stimmen überein (Zahlen:
[PRUEFUNG.md](PRUEFUNG.md#abgleich-mit-dem-rsg-monitoring), «Abgleich mit dem RSG-Monitoring»). Ein gleicher Zuschlag
je Fach spricht dafür, dass mit einem anderen Bezugswert gerechnet wurde («durchschnittlich arbeitende Ärztin/Arzt»,
DAA; METHODIK R8).
*Frage: Mit dem DAA welchen Jahres sind die niedergelassenen ÄAVE der Verordnung gerechnet, in Oberösterreich und in
den übrigen Ländern?*

Niederösterreich, Salzburg, Steiermark, Wien: keine offene Frage zur eigenen Verordnung.

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

1. **Code ins Repo:** den Prototyp nach `web/` übernehmen, `python -m rsg2030 web` und die Tests aus WEB.md, «Wer prüft
   was».
2. **Veröffentlichen:** Workflow `webseite.yml`. GitHub Pages muss im Repo eingeschaltet werden (Settings → Pages →
   Quelle «GitHub Actions»). Vorher sieht sich ein Mensch die Seite im Browser an, auch am Handy.
3. **Vorbehaltstexte gegenlesen:** Die Texte der Detailspalte sind aus den Fallstricken abgeleitet, aber nicht wörtlich
   übernommen. Jeder muss seinen Fallstrick nennen; die Formulierung bestätigt der Herausgeber.
4. **Weitere Zeilen der Tabelle Versorgungsdichte zeigen?** Heute nur `insgesamt`. Möglich wären `spitalsambulant` und
   `extramural` (Aufteilung, ohne Soll-Intervall; Fallstrick 10), `pve` (nur AM und KIJU, im PLAN Mindestwert) und die
   Veränderung IST → PLAN. Offen ist, was davon die Seite tragen soll, ohne unübersichtlich zu werden.
5. **Test im Browser:** Seite lädt ohne Fehler, keine seitliche Verschiebung bei Handy-Breite. Bis dahin prüft das ein
   Mensch.
6. **Schriften:** Die Seite lädt IBM Plex von Google Fonts. Dabei geht die IP-Adresse jeder Besucherin an Google; für
   eine öffentliche Seite datenschutzrechtlich heikel. Vor der Veröffentlichung die Schriften selbst ausliefern (IBM
   Plex steht unter der SIL Open Font License) oder Systemschriften verwenden.
