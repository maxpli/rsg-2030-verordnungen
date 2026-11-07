# Änderungen

Hier steht, was sich zwischen Versionen an den **Daten** ändert – jede Änderung einer Prüfsumme in
`rsg2030/erwartete_ausgaben.csv`, mit Grund –, an den Befehlen und an der **importierbaren Schnittstelle**. Wer das
Paket in einer festen Version einbindet (README, «Mitarbeiten»), liest vor dem Umstellen den Abschnitt
«Schnittstelle» der neuen Version. Versionen: `<Verordnungsstand>.<Nummer>`.

## 2026.3 – in Arbeit

**Doku und Prüfbericht:**

- **KFO: Richtwert ohne Zelle in der Vorlage.** Die ÖSG-Vorlage der RSG-Planungsmatrix hat keine KFO-Spalte, obwohl
  der ÖSG für die Unterzeile «- davon mit kieferorthopädischem Schwerpunkt» ein Soll-Intervall festlegt – anders als
  bei PUL, das eine Spalte hat. Begründet wird das in keinem der drei Bände. Dass die Länder trotzdem unterschiedlich
  ausweisen durften, steht im Textband S.76 («kann um weitere bundeslandspezifische Planungsgrößen … ergänzt werden»,
  «Klarstellungen … in Fußnoten»). Jetzt belegt in docs/METHODIK.md (R4 und «Bekannte Grenzen» 8) mit Ankern in
  `oesg_zitate.csv`. An den Daten ändert sich nichts.
- **Neuer Fallstrick 13: Ein Fach kann in einem Land ganz fehlen.** Kärnten druckt keine MKG-Spalte; in der Tabelle
  Versorgungsdichte fehlt MKG dort in allen drei Matrizen, in IST und PLAN. Ein Ländervergleich für MKG umfasst also
  8 von 9 Ländern. Der **Prüfbericht** nennt jetzt je Land die Fachspalten gegen die Vorlage («Spalten gegen die
  ÖSG-Vorlage»); bisher stand das nur in der Freigabe-Mappe.
- **Wiens drei Zusatzzeilen** stehen in docs/DATEN.md nicht mehr als Sammelzeile «Wien-spezifische Zeilen», sondern
  je mit Inhalt und Lesehinweis – vor allem `gastpat_spitalsambulant` und `gastpat_extramural`, die einzige Stelle in
  allen 41 Matrizen, an der ein Land die Mitversorgung von außerhalb beziffert.
- Die Freigabe-Mappe sagt bei abweichenden Spalten jetzt dazu, dass Ergänzungen laut Textband S.76 zulässig sind.

**Webseite:**

- **Das Dashboard liest `?region=` und `?fach=`** aus der Adresse, damit die statischen Seiten mit vorbelegtem
  Zustand hierher verlinken können. Ohne Parameter verhält es sich genau wie vorher; unbekannte Werte werden
  verworfen, und die Adresse wird nie geschrieben. `data.json` enthält dafür je Region einen `slug` (Nummer der VR
  bzw. Kürzel des Landes ohne Umlaute, derselbe wie in den Adressen der Lesefassung).
- `python -m rsg2030 web` **räumt nur noch die eigenen Dateien weg** statt das ganze Zielverzeichnis: Dort liegt
  jetzt auch die Lesefassung, und ein Lauf von «web» nähme sie sonst mit.

- **Falscher Vorbehalt bei ZMK in Wien und Vorarlberg behoben.** Dort stand «KFO in Oberösterreich: nur als Fußnote
  zu ZMK gedruckt … per Korrekturregel übernommen», weil die Bedingung in `app.js` auch auf den Zuschnitt-Text «KFO
  nicht getrennt ausgewiesen» passte. In Wien und Vorarlberg ist KFO aber laut Fußnote bzw. Textteil **in ZMK
  enthalten**, nur nicht einzeln gezeigt (docs/DATEN.md, Fallstrick 4); betroffen waren alle 14 ZMK-Zellen dieser beiden Länder. Jetzt sind es zwei
  getrennte Vorbehalte, und ein Test bindet jeden an den Zuschnitt-Text, der ihn trägt.
- **«Bis zur Untergrenze fehlen 0,0 ÄAVE» behoben.** Wo der ÄAVE-Abstand auf 0,0 rundet, nannte der Satz in
  Worten eine Zahl, die nichts sagt. Jetzt nennt er die Richtung: «knapp unter der Untergrenze – es fehlen weniger
  als 0,05 ÄAVE Sachleistung». Betrifft 10 der 637 Zellen außerhalb des Soll-Intervalls, auf dem Dashboard und in
  der Lesefassung.
- **Auch ohne Wert führt die Herkunft in die Quelle.** Die Klappe «Woher kommt diese Zahl?» sagte bei einer Zelle
  ohne Wert nur, es gebe nichts herzuleiten – ohne PDF und Seite. Genau dort will man aber nachsehen, dass in der
  Matrix wirklich nichts steht. Jetzt nennt sie immer PDF, Seite und die Verordnung im RIS und dazu den Grund: Fach
  steckt im Elternfach (KFO in Wien und Vorarlberg), Matrix hat die Spalte nicht (Kärnten, MKG) oder Zelle leer.
  Betrifft 20 Zellen.
- **Neuer Vorbehalt an Wiens ZMK-Zellen:** Fußnote (5) rechnet neben der Kieferorthopädie auch «Zahnbehandler +
  Dentisten» zu ZMK; die anderen acht Länder sagen dazu nichts (docs/DATEN.md, Fallstrick 4;
  docs/offene_punkte.md). Die Seite sagt das jetzt an den acht betroffenen Zellen, statt es nur in der Doku zu
  haben.
- **Der Wert in Worten und die Vorbehalte stehen nur noch einmal**, in `rsg2030/darstellung.py` statt in `app.js`
  (docs/WEB.md, «Der Satz und die Vorbehalte stehen einmal»). `data.json` enthält die Texte einmal und je Zelle,
  welche gelten; die Seite setzt ein. Vorarbeit für die statischen Seiten, die dieselben Texte brauchen. `data.json`
  wächst dadurch von 229 auf 328 KB (über die Leitung von 58 auf 66 KB). An den Daten ändert sich nichts.

- **Die Seite zeigt zu jedem Wert, woher er kommt** (docs/WEB.md): PDF, Seite und die Zeile der Matrix wie gedruckt,
  je eingegangener Matrixspalte den Text wie gedruckt und den übernommenen Wert, dazu jede Korrekturregel mit Art und
  Begründung wörtlich aus `korrekturen.csv` und einen Link auf die Verordnung im RIS. Zugeklappt eine Zeile in einem
  eigenen Panel unter Matrix und Detailspalte. «Seite 11 öffnen» springt mit `#page=` in die Datei auf dem
  OGD-Dateiserver; die Seitenzahl steht auch als Text da, weil nicht jeder PDF-Betrachter `#page=` kennt. `data.json`
  wächst dadurch von 135 auf 229 KB (über die Leitung von 44 auf 58 KB); die Seite rechnet nichts nach, sie zitiert.
  Der Bau prüft Zelle für Zelle, dass die gezeigten Spalten den veröffentlichten Wert ergeben, und bricht sonst ab.
- `python -m rsg2030 web` liest dafür **auch** `RSG_2030_Planungsmatrizen.csv` und prüft beide Tabellen gegen
  `erwartete_ausgaben.csv`; `webseite.yml` lädt beide aus dem Release und prüft sie gegen `SHA256SUMS.txt`.
  An den Daten ändert sich nichts – keine neue Prüfsumme, kein neues Release nötig.
- **Am Handy fehlten im Positions-Plot und in der Kachelkarte einzelne Namen und Zahlen.** iOS meldet eine
  Größenänderung auch, wenn beim Scrollen bloß die Adressleiste ein- und ausfährt; die Seite baute beide Grafiken
  dann mitten im Scrollen neu auf, und Safari zeichnete sie nur halb fertig. Jetzt zeichnet sie nur neu, wenn sich
  die Breite wirklich ändert (docs/WEB.md, Punkt 9).
- **Am Handy unterstrich iOS Regionsnamen gestrichelt** und fing das Tippen ab: Die Datenerkennung las Zeilen wie
  «61 Graz» als Adresse. Die Seite schaltet sie jetzt ab (`format-detection`).
- **Die Lesehilfe unter dem Positions-Plot war am Handy an beiden Enden abgeschnitten.** Sie stand als Beschriftung
  in der Grafik, und Text in einer Grafik bricht nicht um; jetzt steht sie als Text darunter.

**Schnittstelle:**

- Neu: `korrekturen.regel_fuer_zelle(regeln, zelle)` – welche Regel aus `korrekturen.csv` eine korrigierte Zelle der
  Long-CSV erklärt (die Long-CSV nennt je Zelle nur den Namen der Regel, nicht die Begründung).
- Neu: `quellen.ris_dokument_url(kennung)` – Seite eines RIS-Dokuments im Portal, für Links, die ein Mensch öffnet.
  `quellen.download.RIS_URL` ist dafür entfallen (der Wächter baute diese Adresse bisher zweimal selbst).
- Neu: `quellen.ogd_pdf_url(kennung, datei, praefix="", seite=None)`, `quellen.quell_dateiname(datei, praefix)` und
  `quellen.OGD_HOST` – Adresse einer Verordnungs-PDF auf dem OGD-Dateiserver, mit Sprungziel. Geladen wird weiter
  über die Schnittstelle (`download.ris_links`).

**Befehle:**

- `waechter --quellen` prüft zusätzlich jede Verordnungs-PDF unter der Adresse, die die Webseite verlinkt: Sie wird
  aus Dokumentnummer und Dateiname abgeleitet, also brächen alle Links der Seite auf einmal und still, wenn der
  OGD-Server sein Muster änderte – die RIS-Prüfung sieht nur die Dokumentnummern.
- `waechter` sucht die geltenden Verordnungen und das ÖSG-Gutachten ebenfalls über die OGD-Schnittstelle (der Typ
  steht in den Metadaten der Treffer und wird aus der Antwort gefiltert; die Links in den Hinweisen zeigen weiter
  auf das Portal, denn die liest ein Mensch im Browser). Davor war der Montagslauf seit dem Bot-Schutz rot.

**Doku:**

- `LIZENZ_DATEN.md` nennt `RSG_2030_Stellen.csv` (seit 2026.2 Teil des Datensatzes) jetzt ausdrücklich mit; der
  Änderungshinweis von CC BY steht nun bei den Quellen, für die er gilt (Statistik Austria, ÖROK), nicht am Ende der
  Liste hinter dem ÖSG.
- Eine Zahl in docs/METHODIK.md (R4, Wirkung der KFO-Fußnote in OÖ) war falsch gerundet: die VD ZMK im PLAN ist 41,4,
  nicht 41,5. Die Daten selbst sind unverändert.
- `tests/test_zitation.py` prüft, dass README, `LIZENZ_DATEN.md` und docs/DATEN.md keine andere Version nennen als
  `pyproject.toml`: Der Einbinde-Pin im README zeigte nach dem Release 2026.2 noch auf 2026.1.

## 2026.2 – Tabelle Stellen

**Daten:**

| Datei | SHA-256 | Zeilen (inkl. Kopf) |
|---|---|---:|
| `RSG_2030_Planungsmatrizen.csv` | `071178b62b46c2fda2e99f78226d8871ed98382baf0264f60b7282872ca2498e` | 30.841 |

`RSG_2030_Versorgungsdichte.csv` bleibt unverändert (gleiche Prüfsumme wie 2026.1): In die Versorgungsdichte gehen nur
ÄAVE-Zeilen ein, und an denen ändert sich nichts.

- **Oberösterreich: die KFO-Stellen der Fußnote übernommen** (39 Zellen mehr). Die Fußnote zu «ZMK*» nennt «IST 2022
  und Plan 2030: 38,2 ÄAVE bzw. 32 vertragskieferorthopädische Planstellen SV» (Anlage S.10, je Region S.12–27). Die
  ÄAVE standen schon in den Daten, die Planstellen nicht – das Fach ZMK bedeutete damit bei den ÄAVE etwas anderes als
  bei den Stellen. Jetzt: IST in jeder Träger-Zeile 32 (ÖGK, SVS, BVAEB – so führen alle sechs Länder mit eigener
  KFO-Spalte ihre KFO-Planstellen, auch wo ZMK bei der SVS «-» ist), PLAN 32 in den gemeinsamen Sachleistungsstellen
  («SV» ohne Träger), Maximalanteil vertragsärztlicher Planstellen 100 % (die Fußnote nennt Planstellen), «gesamt» der
  Zeilen + 32. Die Träger nennt die Verordnung selbst, auf den Bezirksseiten derselben Anlage: «ZMK – zuzügl. in
  Kieferorthopädie (KFO): n vertragskieferorthopädische Planstellen: ÖGK, SVS, BVAEB», je Seite die Zahl der
  VR-Fußnote und zusammen 32 (neuer Test). «zuzügl.» steht dort neben «davon in Unfallchirurgie (UC)» – die
  Verordnung trennt zusätzlich von enthalten. Dazu das RSG-Monitoring, das ZMK «inkl. KFO» führt: ÖGK-Planstellen 414
  gegenüber gedruckt 381, mit der Übernahme 413; Gegenprobe Wien, das «ZMK einschließlich 54 SLS KFO» schreibt und
  ohne Ergänzung passt. Welches Indiz was zeigt und was nicht:
  [docs/PRUEFUNG.md](docs/PRUEFUNG.md), «Steckt KFO schon in der gedruckten ZMK-Spalte?». Offen bleiben der
  Maximalanteil von 100 % und die PLAN-Zuordnung ([docs/offene_punkte.md](docs/offene_punkte.md), «Oberösterreich»).
- **Oberösterreich: Maximalanteil der zusätzlichen SVS-Stellen für URO = 0 %**, bisher leer und als bekannte
  Abweichung geführt. Der Wert folgt aus keiner anderen Zahl; 0 % ist in dieser Zeile der häufigste gedruckte Wert und
  steht als Lesart da, nicht als Herleitung. Folge: Das gesamt-% der Zeile wird jetzt abgeleitet.
- **ÖSG-Zitate maschinell belegt:** Zu jeder zitierten ÖSG-Seite steht ein wörtlicher Anker in
  [`oesg_zitate.csv`](oesg_methodik/referenz/oesg_zitate.csv); `tests/test_zitate.py` prüft, dass er auf dieser Seite
  steht und keine zitierte Seite ohne Anker bleibt (docs/PRUEFUNG.md, Regel 1). Die Dateinamen der drei ÖSG-Bände
  stehen nur noch an einer Stelle (`oesg_methodik.pfade.OESG_BAENDE`).

**Neue Datei:**

| Datei | SHA-256 | Zeilen (inkl. Kopf) |
|---|---|---:|
| `RSG_2030_Stellen.csv` | `06ad54ed4dc18b95a939fc25edccdee2e830b64be9f9703b5d0cfae571ffe04f` | 4.934 |

- **`RSG_2030_Stellen.csv`** – vertragsärztliche Planstellen (IST) und Sachleistungsstellen (PLAN) im **selben
  Fach-Zuschnitt wie die ÄAVE** (ZMK inkl. KFO, IM inkl. PUL, CH inkl. KJC/PCH), je Region, Abschnitt, Stellen-Zeile
  und Fach. Bisher standen die Stellen nur je Matrixspalte in der Tabelle Planungsmatrizen; wer sie den ÄAVE
  gegenüberstellte, musste den Zuschnitt selbst nachbauen – und zwar genau so, sonst verglich er ZMK ohne KFO mit ZMK
  inklusive KFO. Geschnitten wird mit derselben Funktion wie die ÄAVE, nicht mit einer zweiten Umsetzung.
  Neuer Befehl `python -m rsg2030 stellen`, Teil von `alles`; Spalten und Fallstricke: [docs/DATEN.md](docs/DATEN.md).
- Dazu der Maximalanteil vertragsärztlicher Planstellen: Stellen × Prozent **je Matrixspalte**, erst danach summiert
  (`Max_VAEP_Stellen`), und als gewichtetes Mittel (`Max_VAEP_Prozent`) – nie ein Mittel aus Prozentsätzen. Wo für
  einen Teil der Stellen kein Prozentsatz gedruckt ist, bleibt der Anteil leer und der Lauf sagt es; heute kommt das
  nirgends vor.
- **AM ist in den Stellen-Zeilen ohne ZAE** – anders als bei den ÄAVE. Sachleistungsstellen bilden den extramuralen
  Bereich ab (Tabellenband S.232), ZAE sind spitalsambulant (Vorlage, Fußnote (5)). Betroffen ist nur Tirol
  (8,05 Stellen in SON/IDB).

**Quellen:**

- **ÖSG 2023 auf den Stand 09.10.2026** (RIS `SPG_AT_OSG_G_20261009_8_2026`); die Fassung vom 10.10.2025 gilt nicht
  mehr. **Keine Datenänderung:** Alle 20 Zeilen der Planungsrichtwerte sind Wert für Wert gleich (inkl. PUL und KFO),
  die Vorlage der RSG-Planungsmatrix hat dieselben 28 Fachspalten, 6 Fußnoten und 39 Zeilenbeschriftungen, das
  Regelwerk zur ÄAVE (Anhang 5) ist zeichengleich, und alle 32 Versorgungsregionen stehen unverändert da. Geändert
  haben sich die **Seitenzahlen**: Textband 250 → 262 Seiten, Tabellenband 289 → 269. Die RSG-PM-Teile des
  Tabellenbands verschieben sich um −20 (251 → 231, 252 → 232, 254 → 234, 259 → 239, 269 → 249), der Textband vorne
  um +1 bis +2 und ab dem Glossar um +11 (37 → 39, 216 → 227, 223 → 235, 225 → 236). Die alte Seite 36 liegt jetzt
  auf zwei Seiten: Regiomed und SVE auf 37, alles zur Versorgungsdichte auf 38.
- Die ~200 Seitenangaben im Repo sind entsprechend nachgezogen, jede einzeln belegt durch `tests/test_zitate.py`
  (siehe oben). Bloße Verweise («Vorlage S.259») nennen jetzt den Band, damit der Test sie sieht.
- `tests/test_referenz.py` liest die Richtwerttabelle nicht mehr zeilenweise: Der ÖSG bricht PUL und PCH um, bei PCH
  steht das Kürzel **nach** den Werten. Jetzt wird jede Folge von fünf Werten in der Form der Tabellenspalten gesucht
  und ihr das nächstgelegene Kürzel zugeordnet – damit fallen auch Fußnotenzeichen weg, die vorne («(KJP)1 30 …»)
  wie hinten («… 3,9 * 1 vorrangig …») an die Werte stoßen.

**Schnittstelle – Umstellung nötig:**

- `oesg_methodik.faecher.aave_fach` heißt jetzt **`summe_im_zuschnitt`**. Gleiche Argumente, gleiches Verhalten, nur
  der Name. Grund: Der Zuschnitt gilt einheitenneutral – dieselbe Funktion schneidet ÄAVE und Stellen zu (für eine
  Stellen-Zeile fällt die ZAE von selbst weg), und «aave» wäre dort falsch. Bewusst **ohne Alias**: Zwei Namen für
  eine Funktion laden dazu ein, den falschen zu nehmen.

  ```python
  from oesg_methodik.faecher import summe_im_zuschnitt  # vorher: aave_fach

  summe_im_zuschnitt(zeile, "ZMK")  # unverändert
  ```

  Betroffen ist nur, wer `oesg_methodik` **importiert**. Wer die veröffentlichten Dateien liest – der Normalfall –,
  muss nichts tun.

**Befehle:**

- `monitoring_abgleich` vergleicht jetzt auch die **ÖGK-Planstellen** des RSG-Monitorings je Fach und Land, nicht nur
  die ÄAVE-Zeilen (docs/PRUEFUNG.md, «Vertragsärztliche Planstellen»). Nebenbei behoben: ORTR blieb im Abgleich leer,
  wenn das Monitoring eine der Teilspalten OR/UCH/ORTR leer lässt – eine leere Teilspalte zählt jetzt als 0.
- `monitoring_abgleich` stellt außerdem **ZMK und KFO getrennt** neben den Monitoring-Wert, der ZMK «inkl. KFO»
  führt. Daran liest man ab, ob KFO in der gedruckten ZMK-Spalte eines Landes schon steckt, fehlt oder dazugehört –
  die Gegenprobe zur KFO-Fußnote Oberösterreichs (docs/PRUEFUNG.md).
- `waechter`: Antwortet das RIS nicht (es schickt gelegentlich «HTTP 503» und bittet um Pause), ist das ein Hinweis
  «nicht erreichbar – kein Abgleich in diesem Lauf» statt eines Abbruchs mit Traceback. Der Lauf endet weiter mit
  Exit 1, damit in der Mail steht, dass dieser Abgleich ausgefallen ist.
- `download` holt die Dateiliste eines RIS-Dokuments über die **OGD-Schnittstelle des RIS** (data.bka.gv.at) und
  die Dateien von ogd.ris.bka.gv.at statt vom Portal www.ris.bka.gv.at – das Portal beantwortet Anfragen aus
  Rechenzentren mit dem unten genannten Bot-Schutz, die OGD-Schnittstelle ist der dokumentierte Weg für
  maschinelle Abrufe. Dass beide Wege dieselben Bytes liefern, belegen die Prüfsummen im Register.
- CI: Tests **und Release** laden die Quellen aus dem Zwischenspeicher und prüfen jede Datei per SHA-256 gegen das
  Register; frisch geladen wird nur, was neu ist oder fehlt. Grund: Das RIS beantwortet Anfragen aus Rechenzentren
  seit Ende Oktober 2026 mit einem Bot-Schutz («Security Check», HTTP 503) – auch der Wayback-Crawler erhält nur
  die Sperrseite. Der Nachweis der Release-Dateien war immer schon die Prüfsumme, nicht die frische Verbindung
  (docs/PIPELINE.md, «Release»).

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
  S.239); Spalten: docs/DATEN.md.
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
- **Tests gegen die Quelle:** Richtwerte gegen ÖSG-Textband S.39, Zuordnung Bezirk → Versorgungsregion gegen die
  GÖG-Datei «Regionale Gliederung», Zeilen und Spalten der Vorlage gegen Tabellenband S.239; Versorgungsdichte für
  jedes Land von Hand nachgerechnet, die Teilzeilen an Beispielen; spitalsambulant + extramural = insgesamt in jeder
  Region, jedem Abschnitt und Fach.
- **Freigabe:** Was keine Maschine unabhängig prüfen kann (Abweichungen der Zweitlesung, Bildseiten, abweichende
  Spalten und Zeilen, Fußnoten, jede Korrektur und bekannte Abweichung), hat ein Mensch je Zeile bestätigt
  (`freigabe.xlsx`, alle Blätter). Der Lauf endet mit `FREIGEGEBEN`.
- Geprüft: Lauf in einem leeren Ordner mit frischem Download aller 38 Quellen ergibt beide Dateien Byte für Byte
  (19.10.2026).

**Bekannte Grenzen:** docs/METHODIK.md, «Bekannte Grenzen und offene Fragen»; Widersprüche im PDF und wie sie
entschieden sind: Blatt «Entscheidungen» der Freigabe.
