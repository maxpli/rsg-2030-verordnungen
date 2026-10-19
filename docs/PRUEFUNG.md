# Wie die Daten abgesichert sind

Diese Seite erklärt, **was** an den Daten geprüft ist, **wie**, und **was das belegt – und was nicht**. Die Zahlen eines
Laufs (wie viele Zellen, Prüfungen, Korrekturen, Bestätigungen) stehen nicht hier, sondern im Prüfbericht, den jeder
Lauf neben die Daten schreibt: `daten_ergebnis/Pruefbericht.md`.

## Was wir zusagen

> Jeder Wert in `RSG_2030_Planungsmatrizen.csv` steht so in der Verordnung – oder er trägt eine Kennzeichnung, warum
> nicht (`Quelle` = `korrigiert` oder `abgeleitet`, mit Regel und Begründung). Das ist auf fünf Ebenen abgesichert, und jede
> Ebene hinterlässt einen Nachweis im Repository.

| Ebene | Frage | Nachweis |
|---|---|---|
| 1. Quellen | Ist es genau die Datei, die geprüft wurde? | Register mit SHA-256 je Datei |
| 2. Lesung | Was steht im PDF? | Textseiten maschinell, Bildseiten von Hand |
| 3. Zweitlesung | Liest ein anderes Verfahren dasselbe? | KI-Lesung aus dem Seitenbild, Zelle für Zelle verglichen |
| 4. Prüfungen | Ist das PDF in sich stimmig? | Rechenprüfungen bei jedem Lauf; Korrekturen nur mit Befund |
| 5. Freigabe | Hat ein Mensch bestätigt, was keine Maschine unabhängig prüfen kann? | `freigabe.xlsx`, Zeile für Zeile abgehakt |

`FREIGEGEBEN` am Ende von `python -m rsg2030 daten` heißt: Alle fünf Ebenen sind ohne offenen Punkt. Ob die
Verordnungen selbst zu einer anderen Quelle passen, prüft keine Ebene; das IST ist dafür einmal mit dem RSG-Monitoring
der GÖG abgeglichen ([unten](#abgleich-mit-dem-rsg-monitoring)).

## Auf einen Blick: wie sicher die Daten sind

| Frage | Wie sicher | Warum |
|---|---|---|
| Steht jeder Wert so in der Verordnung? | sehr hoch | jede Zelle zweimal unabhängig gelesen, jede Abweichung von einem Menschen am PDF entschieden ([2](#2-lesung), [3](#3-zweitlesung), [5](#5-freigabe)) |
| Passt jede Zahl zu ihren Nachbarn? | hoch | jede Zelle steht in einer Rechenprüfung, außer abgeleiteten; kleine Fehler in Zeilen mit ganzen Zahlen findet nur die Zweitlesung ([4](#4-prüfungen), [Was danach noch unsicher ist](#was-danach-noch-unsicher-ist)) |
| Sind Lücken und Widersprüche im PDF richtig behandelt? | begründet, von einer Person bestätigt | jede Korrektur mit Befund, PDF-Stelle und Begründung; Blatt «Entscheidungen» der Freigabe |
| Passt das IST zu einer unabhängigen Quelle? | auf Bundesland-Ebene ja, bis auf benannte Ausnahmen | [Abgleich mit dem RSG-Monitoring](#abgleich-mit-dem-rsg-monitoring); «niedergelassen» wahrscheinlich mit anderem DAA-Stand gerechnet |
| PLAN und Versorgungsregionen? | nur in sich geprüft | dafür gibt es keine unabhängige Quelle |
| Lassen sich die Länder vergleichen? | eingeschränkt | SVE-Länder, zwei IST-Jahre, DAA-Stand, ZAE, Wahlärzt:innen – [Fallstricke](DATEN.md#fallstricke), [Bekannte Grenzen](METHODIK.md#bekannte-grenzen-und-offene-fragen) |
| Stimmen die Lesarten? | dokumentiert, teils nicht bestätigt | Annahmen wie «KFO in Oberösterreich ist niedergelassen mit Kassenvertrag» (METHODIK R4); nicht mit den Ländern abgestimmt, [offene Fragen an die Länder](offene_punkte.md#unklare-angaben-in-den-verordnungen) |
| Wer hat geprüft? | eine Person | eine [zweite Durchsicht](offene_punkte.md#zweite-durchsicht-beiträge-willkommen) ist willkommen |

Kurz: Die Tabelle Planungsmatrizen gibt die Verordnungen sehr wahrscheinlich richtig wieder. Unsicher ist vor allem, wie
weit sich die Verordnungen untereinander vergleichen lassen – und das betrifft vor allem die Versorgungsdichte.

## Wer prüft was

Wer was prüft, folgt aus drei Regeln:

1. **Was eine Maschine gegen die Quelle prüfen kann, prüft ein Test bei jedem Lauf.** Ein Mensch bestätigt es nicht
   zusätzlich.
2. **Jede Zelle wird zweimal unabhängig gelesen.** Ein Mensch entscheidet nur, wo die beiden Lesungen nicht
   übereinstimmen.
3. **Was keine Lesung ist, sondern ein Urteil, bestätigt ein Mensch Eintrag für Eintrag** – außer, es steht wörtlich so
   in der ÖSG-Vorlage der Planungsmatrix (Tabellenband Anhang 9, S.259). Dann hat die Vorlage das Urteil schon
   gefällt, und die Maschine prüft nur, dass es dieselbe Stelle ist (Regel 1).

Damit hat jede Art von Fehler genau eine Stelle, die sie findet:

| Fehler | Beispiel | Wer findet ihn |
|---|---|---|
| falsche oder geänderte Datei | neue Fassung unter derselben Adresse | Ebene 1: Prüfsumme, Wächter |
| falsche Seite, also falsche Region | VR 61 und VR 62 vertauscht | Textseiten: Test, das Register entsteht aus dem Seitentitel (Regel 1). Bildseiten: Mensch (Regel 2) |
| Wert verlesen oder in der falschen Zelle | «1,2» als «12»; Wert eine Spalte daneben | Zweitlesung, für jede Zelle. Abweichungen und nicht verglichene Zellen: Mensch (Regel 2) |
| Zeile oder Spalte, die die Maschine nicht kennt (neue Verordnung) | neue Zeilenbeschriftung; neuer Spaltenkopf | Auslesen stoppt (`unbekannte_zeile`, `unbekannte_spalte`) → Muster in `matrix_extract.py` bzw. `specs.py` ergänzen → neue Zuordnung im Blatt «Zeilen» bzw. «Spalten» (Regel 3). Beschriftung, die nicht sagt, was die Zeile ist: Prüfung `zeile_zuordnen` → Regel `umbenennen` |
| falsche Zuordnungstabelle, die beide Lesungen teilen | «SON» der falschen Fachspalte zugeordnet; Beschriftung der falschen `Zeile_ID` | Wie in der ÖSG-Vorlage: Test gegen die Vorlage (Regel 1). Sonst Mensch, je Eintrag einmal (Regel 3) |
| Lücke oder Widerspruch im PDF selbst | Zeilensumme passt nicht | Ebene 4: Prüfungen → Korrektur mit Regel → Mensch (Regel 3) |
| Fußnote, die die Bedeutung einer Zahl ändert | «ZMK einschließlich KFO», «PLAN = IST fortgeschrieben» | Verzeichnis aller Fußnoten: vollständig und wie gedruckt per Test (Regel 1), Einordnung durch einen Menschen (Regel 3) |
| falsche Referenzdaten der Kennzahlen | Richtwert vertippt, Bezirk in der falschen Region | Test gegen ÖSG-Textband S.37 und GÖG «Regionale Gliederung» (Regel 1) |
| falsch gerechnete Versorgungsdichte | Bevölkerung der falschen Region | Handrechnungen je Land, Bevölkerung gegen die ÖSG-Zahlen (Tests, Regel 1) |
| Teilzeile falsch zugeschnitten | ZAE bei extramural addiert; AM spitalsambulant ohne ZAE | Test: spitalsambulant + extramural = insgesamt je Region, Abschnitt und Fach (Toleranz = Rundung der gedruckten Zellen); Handrechnungen NÖ, Burgenland VR 12, OÖ, Wien, Tirol (Regel 1) |
| Teilzeile in SVE statt ÄAVE | Steiermark spitalsambulant aus dem Block `haupt` | Abbruch, wenn eine Zeile der Tabelle Versorgungsdichte nicht in ÄAVE ist; Handrechnung Steiermark (Regel 1) |
| Zeile, Fach oder Soll-Intervall, die es nicht geben darf | PVE in AN (Vorarlberg druckt dort «0,0»); Soll-Intervall bei spitalsambulant | Vertrag der ÄAVE-Eingabe (`oesg_methodik/eingang.py`) und Tests (Regel 1) |

---

## 1. Quellen

Jede Quelldatei steht im Register [`rsg2030/quellen/quellen.csv`](../rsg2030/quellen/quellen.csv): Herkunft
(RIS-Dokument oder URL), SHA-256-Prüfsumme, Lizenz. Fehlt eine Datei oder stimmt ihre Prüfsumme nicht, bricht der Lauf
ab. Ersetzt eine Website eine Datei unter derselben Adresse, lädt der Download die geprüfte Fassung aus der Wayback
Machine. Ein Wächter meldet neue Verordnungen und einen neuen ÖSG im RIS, geänderte Originale und Archivkopien, die
nicht die geprüfte Fassung sind (PIPELINE.md).

**Belegt:** Die Daten beruhen auf genau diesen Dateien. **Nicht belegt:** dass es keine neuere Fassung gibt – das
meldet nur der Wächter.

## 2. Lesung

- **Textseiten** (alle Matrizen außer zweien): Das PDF enthält die Zahlen als Text. Der Parser (pdfplumber) liest jedes
  Wort mit seiner Position und ordnet es über die Lage der Spaltenköpfe einer Fachspalte und über die Zeilenbeschriftung
  einer Zeile zu. Ziffern werden dabei nicht «erkannt», sondern als Text übernommen – verlesen kann sich der Parser
  nicht, falsch **zuordnen** schon. Was sich nicht eindeutig zuordnen lässt, ist ein Fehler, kein Raten. Welche Seite
  welche Region ist, steht im Seitenregister; es entsteht aus den Seitentiteln («Versorgungsregion 61 …»), und ein
  Test prüft bei jedem Lauf, dass es zu den PDFs passt.
- **Bildseiten** (Burgenland BL, Anlage 1 S.1; Kärnten VR 21, Anhang S.99): Seiten ohne Textebene. Von Hand abgetippt,
  genau wie im PDF («12,0», «-», «n.v.»), in [`manuell.xlsx`](../rsg2030/eingaben/2026/manuell.xlsx). Das ist eine
  Lesung des PDFs, keine Korrektur – und von der KI-Lesung (Ebene 3) unabhängig, solange niemand die Abschrift nach der
  KI-Lesung ausrichtet. Weichen beide ab, entscheidet ein Mensch am PDF (Blatt «Zweitlesung»); erst dann wird die
  Abschrift berichtigt.

  **Herkunft der Abschrift** (Auskunft des Herausgebers): Alle Zahlen sind von Hand abgetippt. Ausgenommen vier
  Zellen, die eine KI vor der Zweitlesung nach einer Lesung des Seitenbilds geändert hat: Burgenland BL, Block
  `aequivalent`, IST `insgesamt` ORTR 32,3 → 32,2 und ZMK 92,2 → 92,3, PLAN `pve` gesamt 10,9 → leer (schraffiert);
  Kärnten VR 21 PLAN `spitalsambulant` KJP 2,89 → 2,80. Für diese vier Zellen sind die beiden Lesungen nicht
  unabhängig; der Herausgeber hat sie von Hand am PDF bestätigt (alle vier wie im Datensatz). Die Striche und
  «n.v.», die die Abschrift offen gelassen hatte, hat ebenfalls die KI nachgetragen. Ein Strich statt einer Zahl fiele
  in den Summen gegen die Textseiten auf (Burgenland BL = VR 11 + VR 12, Kärnten BL = VR 21 + VR 22; Prüfung
  `vr_summe_gleich_bl`); offen bleibt nur «-» (= 0) gegen «leer», und das vergleicht die Zweitlesung.

Der Originaltext jeder Zelle bleibt in der Spalte `Roh` erhalten.

## 3. Zweitlesung

Ein zweites, unabhängiges Verfahren liest dieselben Seiten: eine KI liest das **Bild** der Seite (nicht die Textebene)
und ordnet über das sichtbare Layout zu – ohne die Werte der ersten Lesung zu kennen. Das Ergebnis liegt je Matrix als
Textdatei in [`zweitlesung/`](../rsg2030/eingaben/2026/zweitlesung) (Modell, Datum, Anweisung und Prüfsumme des Bildes
im Dateikopf); jeder Lauf vergleicht es Zelle für Zelle mit den Daten. Weichen die Lesungen ab, entscheidet ein Mensch
am PDF; die KI entscheidet nie.

**Warum das trägt:** Auf Textseiten kann sich die erste Lesung nicht verlesen, nur falsch zuordnen; die KI ordnet auf
einem anderen Weg zu (Bild statt Textposition) und verliest sich auf ihre eigene Art. Damit ein Fehler unentdeckt
bleibt, müssten beide an derselben Zelle denselben falschen Wert liefern. Auf **Bildseiten** lesen ein Mensch
(Abschrift) und die KI aus demselben Bild – auch das sind zwei verschiedene Verfahren, die sich nicht auf dieselbe Art
verlesen. Zusätzlich bestätigt ein Mensch, welche Region auf der Seite steht (Ebene 5, Blatt «Bildseiten»): Den
Seitentitel kann dort keine Maschine lesen.

**Was als gleich gilt:** Schreibweisen, die dasselbe bedeuten: «2,0» = «2,00», «–» = «-», «n.v» = «n.v.»; eine Fußnote
an der Zelle zählt nicht («-(7)» = «-»). Liest die KI eine Beschriftung verkürzt («Umrechnungsfaktor für
spitalsambulant»), gilt sie als die Zeile derselben Gruppe, die alle ihre Wörter in derselben Reihenfolge enthält – nur
wenn es genau eine gibt. Eine falsche Zuordnung fiele als Abweichungen auf; einen Fehler verdecken kann sie nicht.

**Unvollständige Zeilen:** Gibt die KI in einer Zeile weniger Werte zurück, als die Zeile Spalten hat, ist unklar,
welcher Wert in welche Spalte gehört. Solche Zeilen vergleicht der Lauf nicht. Das Skript nennt die betroffenen
Matrizen; sie werden noch einmal gelesen, und die neue Lesung ersetzt die alte nur, wenn sie vollständiger ist. Was
danach noch unvollständig ist, steht Zelle für Zelle im Blatt «Zweitlesung» der Freigabe – so ist jede Zelle entweder
von zwei Verfahren gleich gelesen oder von einem Menschen am PDF entschieden.

**Wer die Daten nur erzeugt, braucht dafür nichts:** Die Zweitlesung liegt im Repository und wird bei jedem Lauf nur
verglichen. Einen API-Schlüssel (und Kosten) braucht nur, wer eine Seite neu lesen lässt – etwa bei einer neuen
Verordnung ([PIPELINE.md](PIPELINE.md)).

**Ergebnis:** Jede Abweichung wurde vorab am PDF nachgesehen: **In allen Fällen stimmte die erste Lesung**,
die KI hatte sich verlesen – vor allem auf einer Seite, wo das Komma sehr eng an der Ziffer steht («1,2» als «12»),
dazu einzelne leere Zellen, die sie mit «-» füllte, und umgekehrt. Ein Fehler der ersten Lesung wurde nicht gefunden.
Die Abweichungen stehen trotzdem im Blatt «Zweitlesung», damit ein Mensch sie selbst am PDF entscheidet. Zahlen je
Version im CHANGELOG, je Lauf im Prüfbericht.

## 4. Prüfungen

[`rsg2030/checks.py`](../rsg2030/checks.py) rechnet bei jedem Lauf nach, ob das Gelesene in sich stimmig ist. Toleranz
ist jeweils die Rundung der Werte im PDF («12,1» → ±0,05).

| Prüfung | Prüft |
|---|---|
| `zeilensumme` | Fachspalten einer Zeile = Spalte «gesamt» |
| `teile_insgesamt` | IST: spitalsambulant + niedergelassen + selbst. Ambulatorien + Kassenambulatorien = insgesamt; PLAN: spitalsambulant + extramural = insgesamt |
| `teile_extramural` | niedergelassen + selbst. Ambulatorien + Kassenambulatorien = extramural (wo die Zeile im PDF steht) |
| `teile_extramural_wahl` | extramural + Wahlärzt:innen = «Summe extramural inkl. WahlärztInnen» (Wien) |
| `teile_slst` | gemeinsame + zusätzliche Sachleistungsstellen je Träger = Sachleistungsstellen gesamt (Wien) |
| `faktor_aequivalente` | ÄAVE-Äquivalente = Wert im Block `haupt` × Umrechnungsfaktor seines Sektors, in IST und PLAN (Tabellenband S.254); ohne Faktor (Zeilen schon in ÄAVE) in beiden Blöcken gleich; Wert nur in einem Block = Abweichung. Haben alle Regionen eigene Faktoren, prüft das Bundesland seinen BL-Faktor nur im Abschnitt, in dem er steht, sonst gilt Σ VR = BL (Burgenland, Kärnten, Steiermark; METHODIK R6) |
| `vr_summe_gleich_bl` | Summe der Versorgungsregionen = Bundesland, je Zelle |
| `kjc_pch_in_ch` | KJC und PCH ohne eigene ÄAVE – sie sind in CH enthalten (Tabellenband S.252; METHODIK R4) |
| `davon_le_obermenge` | «davon»-Zeilen ≤ ihre Obermenge (PVE ≤ VGF ≤ insgesamt; EVA ≤ gemeinsame Stellen) |
| `prozent_0_100`, `prozent_gewichtet`, `prozent_gesamt`, `prozent_ohne_stellen` | Prozentwerte zwischen 0 und 100; BL-% = mit den Stellen gewichtetes Mittel der VR-%, je Fachspalte (fehlt ein VR- oder BL-% bei Stellen > 0, auch wenn im Fach gar kein % steht: «nicht prüfbar»); gedrucktes gesamt-% = mit den Stellen gewichtetes Mittel der Fach-% derselben Zeile; ohne Stellen nur 0 oder 100 % |
| `leere_summenzelle` | Summenzelle leer, obwohl ihre Teile Werte haben (eine befüllte Teilzeile genügt) |
| `zeile_zuordnen` | keine Zeile bleibt, deren Beschriftung nicht sagt, was sie ist («IST ÄAVE gesamt extramural», Wien VR 92) – eine Regel `umbenennen` muss sie zuordnen; ob richtig, prüfen danach die Summen |
| `optional_nicht_ausgewiesen` | optionale Zeile (Wahlärzt:innen) ohne eine einzige Zahl > 0 → nicht ausgefüllt |
| Vollständigkeit | alle 32 Versorgungsregionen laut ÖSG vorhanden, jede Matrix mit Werten |

**Erst auf den Rohdaten, dann auf den korrigierten.** Jede Prüfung läuft zuerst auf dem, was im PDF steht. Was dort
auffällt (ein «Befund»), ist keine Lesepanne, sondern eine Lücke oder ein Widerspruch **im PDF**. Jeder Befund wird
entweder

- **korrigiert:** eine Regel in [`korrekturen.csv`](../rsg2030/eingaben/2026/korrekturen.csv) mit Art (Lücke,
  Widerspruch, Fußnote …), PDF-Stelle und Begründung. Eine Regel ohne zugehörigen Befund ist ein Fehler. Die
  korrigierten Zellen tragen `Quelle = korrigiert`; der PDF-Text bleibt in `Roh`. Oder
- **bewusst gelassen:** ein Eintrag in [`bekannte_abweichungen.csv`](../rsg2030/eingaben/2026/bekannte_abweichungen.csv)
  mit Grund (z. B. «Wahlärzt:innen-Zeile nur in der BL-Matrix»).

**Wann korrigieren, wann lassen.** Korrigiert wird, wenn das PDF erkennbar falsch ist und sich der richtige Wert
eindeutig aus demselben Dokument ergibt: als Summe der gedruckten Teile, als Summe der Regionen, aus einer Fußnote oder
weil eine Zeile offensichtlich falsch beschriftet ist. Bewusst gelassen wird nur aus einem von zwei Gründen:

1. **Kein Fehler:** Die Prüfung passt auf diese Matrix nicht, weil eine Zeile oder Spalte nur auf einer Ebene steht
   (Wahlärzt:innen-Zeile nur in der BL-Matrix – dann kann Σ VR nicht BL sein).
2. **Nicht entscheidbar:** Das PDF widerspricht sich, aber welcher Wert stimmt, lässt sich aus ihm nicht ablesen
   (RAD 2,0 nur in der Burgenland-BL-Matrix: fehlt der Wert einer Region, oder ist er im Land zu viel?). Jede
   Korrektur wäre geraten.

Kein Grund ist, dass eine Abweichung die Versorgungsdichte nicht berührt: Die Tabelle Planungsmatrizen ist selbst ein
Datensatz, und wer dort eine Summe nimmt, muss sich auf sie verlassen können.

Dasselbe gilt für eine Zelle, die eine Prüfung **nicht nachrechnen** kann («nicht prüfbar», z. B. fehlt ein VR-%):
Auch sie wird korrigiert, wo der Wert eindeutig ist, oder mit Grund in `bekannte_abweichungen.csv` eingetragen.

Danach laufen alle Prüfungen noch einmal. Bleibt eine Abweichung oder nicht prüfbare Zelle ohne Begründung, ist der Lauf
nicht freigegeben, und die Tabelle Planungsmatrizen wird nicht geschrieben.

Dazu kommen **Ableitungen** ([`ableitungen.py`](../rsg2030/ableitungen.py)): Zeilen, die ein Land nicht ausweist, andere
aber schon, werden aus den PDF-Werten desselben Landes gerechnet (`Quelle = abgeleitet`). Heute zwei: IST «extramural»
außer in Wien und das gesamt-% der %-Zeilen, wo es nicht gedruckt ist. Eine abgeleitete Zahl prüft keine Prüfung nach –
es wäre dieselbe Rechnung; geprüft sind die Werte, aus denen sie entsteht.

**Belegt:** Jede Zahl passt zu ihren Nachbarn – zu Zeilensumme, Teilen, Regionen. Ein einzelner verrutschter oder
verlesener Wert fällt so fast immer auf. **Nicht belegt:** Fehler, die alle Summen gleich verschieben. Ein falsch
zugeordneter Spaltenkopf verschiebt alle Werte einer Matrix in dieselbe falsche Spalte – Teile und Summe bleiben
stimmig. Dafür gibt es Ebene 3 und 5.

## 5. Freigabe

In die Mappe [`freigabe.xlsx`](../rsg2030/eingaben/2026/freigabe.xlsx) kommt genau das, was nach Regel 2 und 3 ein
Mensch entscheiden muss – nicht mehr:

| Blatt | Regel | Was bestätigt wird | Warum ein Mensch |
|---|---|---|---|
| Zweitlesung | 2 | jede Zelle, in der die Lesungen verschieden sind oder die nicht verglichen werden konnte | mindestens eine Lesung ist falsch; welche, zeigt nur das PDF |
| Bildseiten | 2 | welche Region auf der Seite steht | der Seitentitel ist nicht maschinell lesbar; die Werte laufen wie überall über das Blatt «Zweitlesung» |
| Spalten | 3 | je Land, welche Fachspalten es anders hat als die ÖSG-Vorlage (zusätzlich KFO, ohne STR oder MKG); jede Kopfzeile, in der ein Kopf nicht schon selbst seine Fachspalte ist, mit ihrer Zuordnung «Kopf → Fachspalte» (z. B. «SON → SON/IDB») | ob eine Spalte, die die Vorlage nicht kennt, das bedeutet, was ihr Name sagt, ist ein Urteil; und beide Lesungen benutzen dieselbe Zuordnung – ein Fehler dort verschiebt eine ganze Spalte, ohne dass eine Summe es merkt |
| Zeilen | 3 | jede Zeilenbeschriftung im PDF, die nicht die der ÖSG-Vorlage ist, und ihre `Zeile_ID` | dasselbe für Zeilen |
| Fußnoten | 3 | jede Fußnote, die nicht wörtlich der ÖSG-Vorlage entspricht, mit ihrer Einordnung (DATEN.md, «Fußnoten») | ob eine Fußnote eine Zahl ändert, ist ein Urteil; auf Bildseiten ist auch der Text nur von Hand gelesen. Oben einzeln, was Werte betrifft, offen ist oder auf einer Bildseite steht (genau prüfen); darunter je Land eine Zeile mit allen Hinweisen und Teilmengen (überfliegen: versteckt sich eine Wertänderung?) |
| Entscheidungen | 3 | jede Korrektur, bekannte Abweichung und Ableitung | ein Urteil, keine Lesung |

**Nicht in der Mappe**, weil eine Maschine es unabhängig prüft (Regel 1): das Seitenregister der Textseiten, die
Richtwerte und die Zuordnung Bezirk → Versorgungsregion, Fußnoten der Textseiten, die wörtlich der ÖSG-Vorlage
entsprechen, und jede Zelle, die beide Lesungen gleich lesen. Ebenso Zeilen und Spalten wie in der Vorlage
(`rsg2030/vorlage.py`):

- **Zeilen:** Die Beschriftung steht so in der Vorlage (in diesem Abschnitt), und der Parser hat sie der Zeile_ID dieser
  Vorlage-Zeile zugeordnet. Die Vorlage-Zeilen und ihre Zeile_ID stehen in
  [`oesg_rsgpm_zeilen.csv`](../oesg_methodik/referenz/oesg_rsgpm_zeilen.csv); dass jede Beschriftung so auf S.259
  steht, prüft `tests/test_referenz.py`. Die Zeile_ID ist durch ihre Vorlage-Zeile definiert (DATEN.md, «Zeilen», in
  der Reihenfolge der Vorlage). Zwei Platzhalter der Vorlage füllen die Länder aus: «ÄAVE (ggf. SVE)» steht als
  «ÄAVE (ggf. SVE)», «ÄAVE» oder «SVE» da, «(- davon)» als «(- davon)», «- davon» oder gar nicht. Jede andere
  Abweichung («- davon ÄAVE in PVE», «ÄAVE-Ä & ÄAVE insgesamt», Faktoren unter PLAN statt IST) kommt in die Mappe.
- **Spalten:** Das Land hat genau die Fachspalten der Vorlage (`vorlage.SPALTEN_VORLAGE`, Test gegen die Kopfzeile auf
  S.259), und jeder Kopf ist ohne Fußnotenzeichen genau seine Fachspalte («AM(4)», «ORTR3)» → AM, ORTR) oder «AM/PV» →
  AM wie in der Vorlage. Dann gibt es nichts zu urteilen. Hat ein Land eine Spalte, die die Vorlage nicht kennt (KFO),
  oder fehlt eine (STR), kommt das je Land einmal in die Mappe. Ob in einer Matrix ein Kopf fehlt oder eine Spalte
  verschoben gelesen ist, zeigt die Zweitlesung, die die Köpfe aus dem Bild liest: Sie vergleicht jede Zelle, und eine
  Zelle, die nur eine der beiden Lesungen hat, ist eine Abweichung. Dazu muss jede Zeile ihre Spalte «gesamt» ergeben.

**Keine Zufallsauswahl, keine Fangzellen:** Eine Stichprobe misst eine Fehlerquote an einer Auswahl; die Zweitlesung
vergleicht jede Zelle. Und ob jemand wirklich ins PDF schaut, muss nicht mit absichtlich falschen Werten geprüft werden:
Im Blatt «Zweitlesung» stehen zwei verschiedene Werte nebeneinander, und welcher stimmt, lässt sich nur am PDF
entscheiden.

Jede Zeile der Mappe trägt eine Prüfsumme des bestätigten Inhalts. Ändert sich der Inhalt (andere Fassung, andere Regel,
anders gelesener Wert), verfällt die Bestätigung. Steht in einer Bestätigung ein anderer Wert laut PDF als im
Datensatz, ist das ein Lesefehler: Der Lauf ist nicht freigegeben, bis der Parser bzw. die Abschrift korrigiert ist –
Werte werden nie von Hand überschrieben.

**Wer bestätigt:** bisher eine Person (der Herausgeber). Eine zweite, unabhängige Durchsicht – vor allem des Blatts
«Entscheidungen» – ist willkommen (offene_punkte.md).

---

## Abgleich mit dem RSG-Monitoring

Für Version 2026.1 wurden die IST-Werte mit dem RSG-Monitoring der GÖG verglichen: dasselbe Datenjahr, je Land,
Teilzeile und Fach, bei den SVE-Ländern der Block `aequivalent`. Nachrechnen: `python -m
rsg2030.scripts.monitoring_abgleich` lädt die beiden Kurzfassungen (im Register mit Verwendet = «Abgleich», `download`
lädt sie), prüft ihre Prüfsumme und zeigt jede Zahl dieses Abschnitts; gleich heißt auf 0,1 ÄAVE (Wien auf 1). Das
Monitoring rechnet ebenfalls mit Regiomed, ist aber von unserer Abschrift unabhängig. Es zeigt also, ob die Verordnungen
zu einer anderen Quelle passen – das prüft keine der fünf Ebenen. Quelle: GÖG, RSG-Monitoring, Kurzfassung 2024 (Daten
2022) und Kurzfassung 2025 (Daten 2023), Excel-Dateien auf goeg.at
([2024](https://goeg.at/sites/goeg.at/files/inline-files/RSG%20Monitoring%20Kurzfassung%202024.xlsx),
[2025](https://goeg.at/sites/goeg.at/files/inline-files/RSG%20Monitoring%202025%20Kurzfassung.xlsx)).

**Was übereinstimmt:** Spitalsambulant, in den Ambulatorien und bei den Wahlärzt:innen sind die IST-Werte der
Verordnungen fast überall die Werte des Monitorings desselben Jahres, Fach für Fach auf 0,1 ÄAVE (Wien druckt ganze
Zahlen). Das stützt Abschrift und Block-Regel (METHODIK R6) für diese Zeilen. Die Ausnahmen stehen so im PDF, beide
Lesungen sind gleich – es sind Unterschiede der Verordnungen, keine Lesefehler:

- spitalsambulant: Kärnten hat keine Spalte MKG (Monitoring 9,1 ÄAVE), Steiermark AM «-» (1,7), Wien STR 44 (keine;
  laut Fußnote (11) nicht in Regiomed abgebildet und aus dem RSG 2025 hochgerechnet). Salzburg und Tirol führen die ZAE
  in SON/IDB, das Monitoring in AM, gleich groß. NÖ AU und IM um 0,1.
- Ambulatorien: Burgenland selbständige Ambulatorien KJP 5,3 und PSY 4,0 (Monitoring 3,0 und 2,0), Salzburg
  selbständige Ambulatorien KJP 2,0 und ZMK 3,9 (0 und 7,0), Kärnten Kassenambulatorien IM 2,5 (5,0), Steiermark
  Kassenambulatorien AM «-» (6,0).
- Wahlärzt:innen: OÖ ZMK 23,4 (29,4; das Monitoring zählt ZMK «inkl. KFO», die OÖ-Fußnote nennt KFO für
  Wahlärzt:innen nicht), Tirol IM 16,9 (16,5); NÖ AM und IM, Tirol CH um 0,1.

**Was nicht übereinstimmt:** Bei den niedergelassenen Vertragsärzt:innen liegen die Verordnungen in allen Ländern über
dem Monitoring – und zwar je Fach und IST-Jahr in allen Ländern um praktisch denselben Anteil. IST 2022: AM +5,3 %, IM
+4,7 %, HNO +10 %; IST 2023: AM +6,3 %, IM +9,4 %, HNO +17 %. Ausnahme OÖ, rund 5 Prozentpunkte darüber (AM +10,6 %:
695,3 gegenüber 628,7). Ambulatorien und Wahlärzt:innen stimmen. Das ist das Muster eines anderen Bezugswerts je Fach,
also eines anderen DAA-Stands (METHODIK R8): Das Monitoring rechnet laut Methodenband (S.18) beide Jahre mit dem DAA
2022, die Verordnungen offenbar je IST-Jahr mit einem anderen und OÖ mit einem eigenen. Bestätigt ist das nicht; dass
die Wahlärzt:innen stimmen, obwohl sie laut fachlicher Auskunft ebenfalls über den DAA umgerechnet werden, passt nicht
ganz dazu. Es sind die Werte der Verordnungen, keine Lesefehler (DATEN.md, Fallstricke 2 und 9).

**Was der Abgleich geklärt hat:**

- **ZAE:** Das Monitoring weist die ZAE erst ab Datenjahr 2023 getrennt aus; bis 2022 stecken sie in den Fachspalten,
  vor allem IM. Wien spitalsambulant von 2022 auf 2023: AM 12,3 → 90,4 (davon 88,1 ZAE), IM 368,2 → 311,1. Daraus folgt,
  wo AM in den Kennzahlen die ZAE enthält und wo nicht, und dass die Wiener «ca. 130 VZÄ» in den Fachspalten enthalten
  sind, nicht zusätzlich (METHODIK R5).
- **Keine Ergänzung der ZAE in der Steiermark (IST):** Die IST-Werte der Steiermark sind Regiomed 2022, die ZAE
  stecken also schon in den Fachspalten. Aus SVE × Faktor ergänzt, läge die Summe bei 574,5 statt 549,4 (Monitoring
  551,1). Deshalb keine Korrektur, sondern eine bekannte Abweichung (METHODIK R6).
- **Eine Korrektur bestätigt:** Kärnten IST KIJU niedergelassen 15,7 statt gedruckt 9,4. Monitoring 15,1, mit dem
  Abstand der übrigen Länder 2022 bei KIJU (+3,4 bis +3,7 %) 15,6–15,7; die gedruckten 9,4 liegen weit darunter.
- **ORTR** ist in allen Ländern OR + UCH + ORTR des Monitorings, enthält also überall die Unfallchirurgie (METHODIK R4).
- **Nicht ausgefüllte Wahlärzt:innen-Zeilen** (Burgenland, Steiermark, Vorarlberg): Laut Monitoring gibt es dort
  Wahlärzt:innen (24,6, 135,8, 47,7 ÄAVE). «Leer» statt 0 ist also richtig (DATEN.md, Fallstrick 1).

**Warum der Abgleich trägt, obwohl Regiomed seine Methode geändert hat:** Die Schlüsse zu ZAE, ORTR und Steiermark
stützen sich nur auf spitalsambulant, und dort sind beide Quellen Fach für Fach gleich – sie verwenden also dieselben
Zahlen, welche Methode auch immer dahinter steht. (Auch die spitalsambulanten ÄAVE stammen aus Regiomed, «unter
Berücksichtigung der ärztlichen VZÄ in den nicht bettenführenden Hauptkostenstellen gemäß KA-Statistik», Textband
S.216; die Methodenänderungen, die der ÖSG nennt, betreffen den «vertragsärztlichen Bereich», Methodenband S.17–18,
METHODIK R8.)

**Belegt:** Das IST spitalsambulant, in den Ambulatorien und bei den Wahlärzt:innen passt zu einer unabhängigen Quelle,
je Land und Fach, bis auf die genannten Ausnahmen. **Nicht belegt:** PLAN und Versorgungsregionen – das Monitoring kennt
nur IST und Bundesländer. Der Abgleich ist nicht Teil des Laufs; wiederholen, wenn sich das IST ändert. Kein Wert wird
aus dem Monitoring übernommen: Es ist eine andere Quelle, nicht die Verordnung.

---

## Was danach noch unsicher ist

Wenn alle fünf Ebenen grün sind, ist **jede Zelle zweimal gelesen und jede Abweichung von einem Menschen entschieden**.
Ein Lesefehler bliebe nur unentdeckt, wenn beide Lesungen an derselben Zelle denselben falschen Wert liefern und er
zugleich alle Rechenprüfungen besteht. Das ist praktisch ausgeschlossen, solange die Lesungen unabhängig sind – auf den
Bildseiten also, solange die Abschrift nicht nach der KI-Lesung ausgerichtet wird (Ebene 2, «Herkunft der
Abschrift»).

**Wie weit die Rechenprüfungen reichen** (nachrechnen: `python -m rsg2030.scripts.abdeckung`): Je Zeilenart – Land,
Block, IST/PLAN, Zeile, Ebene, Fachspalte oder «gesamt» – wird eine Zelle grob verfälscht (+ 100, % ± 50, Faktor × 2),
und die Prüfungen laufen neu. Jede Zeilenart fällt auf, außer den abgeleiteten Zellen: Die Prüfung wäre dieselbe
Rechnung, die sie erzeugt hat; geprüft sind ihre Teile.

Kleine Fehler finden die Rechenprüfungen nur, wenn sie größer sind als die Rundung aller Werte einer Rechnung
zusammen. Bei ganzen Zahlen – Stellen-Zeilen, Wien – sind das in einer Zeilensumme über viele Fächer mehrere Einheiten;
enger geht nicht, denn auch richtig gedruckte Summen gehen dort um ± 1 nicht auf. Wo ein Fehler von 10 % (mindestens
1) so durchrutschen würde, zeigt `--stufe fein`. Solche Fehler findet nur die Zweitlesung, die jede Zelle vergleicht.

Das sagt nichts darüber, ob die Verordnungen untereinander vergleichbar sind und ob jede Lesart stimmt – dazu die
Übersicht [oben](#auf-einen-blick-wie-sicher-die-daten-sind).

## Reproduzierbarkeit

Exakte Paketversionen (`requirements.txt`), deterministische Ausgabe, und am Ende jedes Laufs der Vergleich mit der
veröffentlichten Prüfsumme (`rsg2030/erwartete_ausgaben.csv`). Wer die Daten selbst erzeugt, sieht am Ende «✓ …
entspricht Version …». Die Tests (`python -m pytest`) lassen die ganze Pipeline auf den PDFs laufen; GitHub Actions tut
das bei jedem Push.

Die Dateien am Release erzeugt GitHub Actions bei jedem Versions-Tag frisch aus dem Code und den Quellen; ein Release
entsteht nur, wenn das Ergebnis den veröffentlichten Prüfsummen entspricht und alle Tests grün sind. Das belegt: Die
Dateien kommen aus genau diesem Code, niemand hat sie danach verändert. Ob der Code richtig rechnet, belegt es nicht –
das tun die Prüfungen oben, und jeden einzelnen Wert kann man über PDF-Seite und Originaltext (`Roh`) am PDF
nachschlagen, gleich ob die Datei heruntergeladen oder selbst erzeugt ist.
