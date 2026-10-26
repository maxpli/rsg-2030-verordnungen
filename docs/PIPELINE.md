# Betrieb und Pflege

Wie die Daten entstehen und wie man sie pflegt. **Wie sie abgesichert sind und was das belegt:**
[PRUEFUNG.md](PRUEFUNG.md).

## Ablauf von `python -m rsg2030 daten`

```
 1 Quellen     alle verwendeten Dateien da, Prüfsumme wie in quellen.csv?       sonst Abbruch
 2 Auslesen    jede Matrix aus seiten.csv über PDF-Koordinaten (pdfplumber)
               Seite ohne Textebene (Bild) → Werte aus manuell.xlsx;
               fehlt das Blatt: «bitte abtippen» (Blatt anlegen: python -m rsg2030 manuell)
 3 Zweitlesung Lesung A gegen die Zweitlesung aus dem Seitenbild (zweitlesung/), Zelle für Zelle;
               Abweichungen und Zeilen, die die KI unvollständig gelesen hat → Blatt «Zweitlesung» der Freigabe
 4 Fußnoten    Verzeichnis fussnoten.csv: jede Fußnote eingeordnet, Verweis wo nötig?
               (ob jede Fußnote der PDFs drinsteht, prüft tests/test_fussnoten.py am PDF)
 5 Befunde     Prüfungen auf den ROHDATEN: wo ist das PDF selbst lückenhaft oder widersprüchlich?
 6 Korrektur   Regeln aus korrekturen.csv; jede Regel muss einen Befund aus 5 auflösen
               danach: Zeilen, die ein Land nicht ausweist, aus seinen PDF-Werten ableiten (ableitungen.py)
 7 Prüfen      dieselben Prüfungen auf den korrigierten Daten + alle 32 VR laut ÖSG vorhanden
               offene Abweichung oder nicht prüfbare Zelle (weder korrigiert noch in
               bekannte_abweichungen.csv) → Fehler
 8 Freigabe    freigabe.xlsx: alles bestätigt? Lesefehler gemeldet?
               (Mappe nachziehen: python -m rsg2030 freigabe)
 9 Ausgabe     Tabelle Planungsmatrizen (nur wenn fehlerfrei) + Excel-Mappe + Pruefbericht.md
               + Abgleich mit der veröffentlichten Version (✓ / ✗)
```

Ende: `FREIGEGEBEN`, oder `NICHT FREIGEGEBEN (Grund)`. Alle Zahlen des Laufs stehen in `daten_ergebnis/Pruefbericht.md`.

`daten` schreibt nur nach `daten_ergebnis/`, nie in die Eingaben im Paket (`rsg2030/eingaben/`). Was dort zu ändern ist,
tun eigene Befehle: `seiten`, `manuell`, `fussnoten`, `freigabe` – siehe «Neue oder geänderte Verordnung einpflegen».

---

## Eingaben (`rsg2030/eingaben/2026/`)

Alles, was nicht automatisch aus dem PDF kommt – je Verordnungsstand ein Ordner, in git:

| Datei | Inhalt |
|---|---|
| `seiten.csv` | Seitenregister: welche Matrix auf welcher PDF-Seite (1-basiert) |
| `korrekturen.csv` | Abweichungen vom PDF – je Regel Art, Befund, Begründung |
| `bekannte_abweichungen.csv` | Prüfabweichungen, die bewusst bleiben – mit Begründung |
| `manuell.xlsx` | abgetippte Bildseiten (Burgenland BL, Kärnten VR 21) |
| `fussnoten.csv` | jede Fußnote jeder Matrix: Text wie gedruckt, Einordnung, Verweis (DATEN.md, «Fußnoten») |
| `zweitlesung/` | Zweitlesung je Matrix (KI aus dem Seitenbild), Zelle für Zelle; jeder Lauf vergleicht nur – ohne API-Schlüssel |
| `freigabe.xlsx` | was ein Mensch am PDF bestätigt (PRUEFUNG.md, Ebene 5) |

**Beispiele für Regeln** (`korrekturen.csv`; `*` = alle)

```csv
Land,Ebene,Region_ID,Block,Abschnitt,Zeile_ID,Fach,Regel,Art,Befund,Begruendung
# Lücke: Summenzeile im PDF leer → aus den Teilzeilen bilden
Wien,*,*,haupt,PLAN,insgesamt,*,summe:spitalsambulant+extramural,Lücke,leere_summenzelle,"Zeile «PLAN ÄAVE insgesamt 2030» ist im PDF leer …"
# Widerspruch: BL-Wert passt nicht zur Summe der VR → Entscheidung
Burgenland,BL,*,aequivalent,PLAN,insgesamt,AU,vr_summe,Widerspruch,vr_summe_gleich_bl,"PDF S.1: BL AU 18,5, aber VR 11 + VR 12 = 19,5 …"
```

| Regel | Wirkung |
|---|---|
| `summe:a+b+…` | Summe der Zeilen a, b, … in derselben Fachspalte |
| `zeilensumme` | Summe der Fachspalten → «gesamt» (überschreibt) |
| `zeilensumme_wenn_leer` | wie `zeilensumme`, nur wenn «gesamt» leer ist |
| `vr_summe` | BL-Wert = Summe derselben Zelle über alle VR |
| `umbenennen:quelle` | Zeile «quelle» ist im PDF falsch beschriftet → wird zu `Zeile_ID` |
| `nicht_ausgewiesen` | Werte der Zeile (bzw. der Fachspalte in «Fach») → leer, `Roh` bleibt (optionale Zeile, nicht ausgefüllt; «0», die «nicht angegeben» heißt) |
| `zusatz:wert` | Fachspalte bekommt «wert» (muss leer sein), «gesamt» der Zeile + «wert»; `Zeile_ID` mit «+» für mehrere Zeilen |
| `plus:wert` | Fachspalte + «wert» (leer zählt als 0), «gesamt» der Zeile + «wert»; `Zeile_ID` mit «+» für mehrere Zeilen |
| `wert:wert` | leere Zelle bekommt «wert», «gesamt» bleibt; nur wo er sich eindeutig aus demselben Dokument ergibt – Rechnung in der Begründung, eine Prüfung rechnet sie nach (OÖ VR 42: % aus dem BL-%) |

`bekannte_abweichungen.csv`: `Check,Land,Region_ID,Block,Abschnitt,Zeile_ID,Fach,Grund`, z. B.
`vr_summe_gleich_bl,OÖ,OÖ,haupt,IST,wahl,*,"VR-Matrizen OÖ enthalten keine Wahlärzt:innen-Zeile"`.

---

## Neue oder geänderte Verordnung einpflegen

Reihenfolge, die Zeit spart: zuerst alles, was die Maschine prüft (Schritte 1–3 bis auf die Freigabe), **die Freigabe
zuletzt** – jede spätere Änderung am bestätigten Inhalt öffnet die Haken wieder. Abschrift von Bildseiten und
KI-Lesung bleiben getrennt: Abweichungen entscheidet ein Mensch am PDF, die Abschrift wird nie nach der KI-Lesung
ausgerichtet.

0. **Bemerken:** `python -m rsg2030 waechter` sucht im RIS nach allen geltenden RSG-Verordnungen mit «2030» (kundgemacht
   ab 2017, Fassung heute) und nach dem geltenden ÖSG-Gutachten und vergleicht die Dokumentnummern mit dem Register; mit
   `--quellen` lädt er zusätzlich jede URL-Quelle und vergleicht ihre Prüfsumme (erkennt jeden Austausch unter derselben
   Adresse); mit `--archiv` lädt er jede Archivkopie und prüft, ob sie die geprüfte Fassung ist. In GitHub Actions läuft
   der RIS-Teil jeden Montag, die Prüfung der Originale und Archivkopien am 1. jedes Monats; bei einem Hinweis schlägt
   der Lauf fehl und GitHub schickt eine Mail. Antwortet ein Server nicht (das RIS schickt gelegentlich «HTTP 503» und
   bittet um Pause), meldet der Wächter das als Hinweis «nicht erreichbar – kein Abgleich in diesem Lauf»: Dieser
   Abgleich hat dann nicht stattgefunden. Bleibt es dabei, von Hand nachsehen. Meldet er eine Archivkopie, die nicht die geprüfte Fassung ist: das
   Original bei web.archive.org/save neu einreichen (solange es noch die geprüfte Fassung ist) und den neuen Zeitstempel
   in die Spalte «Archiv» eintragen (`https://web.archive.org/web/<Zeitstempel>id_/<Adresse>`). Gibt es zum Zeitstempel
   keine Aufnahme, leitet die Wayback Machine still auf die nächste um; das zeigt erst die Prüfsumme. Der Download lädt
   immer nur die Dateien aus dem Register (notfalls aus dem Archiv) – so bleibt jede Datenversion festgelegt.
1. **Quellen:** in `rsg2030/quellen/quellen.csv` je Datei eine Zeile (Datei, `RIS`, Dokumentnummer, ggf. Präfix bei
   mehreren Verordnungen eines Landes, Bundesland, Stand, Verwendet = `rsg_2030`). `python -m rsg2030 download` lädt
   sie; die SHA-256 ins Register übernehmen. Bei einem neuen Stand: neuer Ordner `eingaben/<stand>/`, `VERORDNUNGSSTAND`
   in `rsg2030/config.py` darauf setzen; die Pipeline liest dann nur die RIS-Zeilen mit diesem Stand.
2. **Seiten:** `python -m rsg2030 seiten` – Matrixseiten werden gefunden; bei Bildseiten fragt das Skript
   (Vorschlag: Bildseite zwischen den Nachbarmatrizen). Gibt es Matrizen in mehreren Verordnungen eines Landes,
   gilt die neueste.
3. **`python -m rsg2030 daten`** und Schritt für Schritt abarbeiten:
   - **«bitte abtippen»** → `python -m rsg2030 manuell` legt das Blatt in `manuell.xlsx` an; ausfüllen, Werte genau
     wie im PDF («12,0», «-», «n.v.»), auch jeden Strich. Von Hand und ohne die KI-Lesung daneben: Die Abschrift ist
     eine der beiden unabhängigen Lesungen. Abweichungen zur Zweitlesung entscheidet ein Mensch am PDF (Blatt
     «Zweitlesung»); erst danach die Abschrift berichtigen – nie nach der KI-Lesung (PRUEFUNG.md, Ebene 2).
   - **Befunde** (Blatt `_Befunde_roh` der Excel-Mappe) → je Befund im PDF nachsehen und entscheiden:
     korrigieren (`korrekturen.csv`) oder so lassen (`bekannte_abweichungen.csv`), immer mit Begründung.
   - **Fußnoten** → `python -m rsg2030 fussnoten` trägt neue Fußnoten der Textseiten als Entwurf ein; Text am PDF
     prüfen, Einordnung und ggf. Verweis ergänzen. Fußnoten von Bildseiten von Hand eintragen. In Oberösterreich
     stehen sie auf der Seite nach der Matrix («Fußnoten VR 41»). Ersetzt die Verordnung eine ältere desselben
     Landes, vorher dessen Einträge löschen: Der Entwurf übernimmt nur Zeichen, die es für die Region noch nicht gibt.
     Vergessene alte Einträge meldet `daten` (Schritt 4: «keine Seite dieser Matrix im Seitenregister»).
   - **Zweitlesung** der neuen Seiten: `python -m rsg2030.scripts.zweitlesung_ki --matrizen <name> --batch` (braucht
     einen API-Schlüssel, siehe Skript), dann `--abholen <batch-id>`. Meldet das Skript Matrizen mit unvollständigen
     Zeilen, den genannten Befehl einmal ausführen (ersetzt nur, wenn vollständiger). Abweichungen entscheidet die
     Freigabe.
   - **Freigabe** → `python -m rsg2030 freigabe` bringt `freigabe.xlsx` auf den neuen Stand (bestehende Haken bleiben,
     wo sich nichts geändert hat); die offenen Zeilen am PDF prüfen, «bestätigt» = ja.
4. Wiederholen, bis `FREIGEGEBEN`. Dann `python -m pytest`: Der Test der Tabelle Planungsmatrizen zeigt, was sich
   geändert hat. Ist die Änderung gewollt: neue SHA-256 und Zeilenzahl in `rsg2030/erwartete_ausgaben.csv`, Eintrag in
   `CHANGELOG.md`, neue Version in `pyproject.toml` und `CITATION.cff`.
5. **Hat sich das IST geändert** (neue Verordnung, neue oder geänderte Korrektur im IST): `python -m
   rsg2030.scripts.monitoring_abgleich` und die Ergebnisse mit PRUEFUNG.md, «Abgleich mit dem RSG-Monitoring»,
   vergleichen. Eine neue Abweichung ist ein Befund für einen Menschen – nie ein Wert, der übernommen wird. Gibt es für
   das neue IST-Jahr noch keine Kurzfassung, sie ins Register eintragen (Verwendet = `Abgleich`, wie die beiden
   vorhandenen); das Skript liest das Datenjahr aus der Datei.

Ändert sich das Layout einer Matrix (neue Zeile, anderer Kopf), meldet Schritt 2 Parser-Fehler; dann `ZEILEN_DEFS` in
`rsg2030/matrix_extract.py` bzw. `rsg2030/specs.py` erweitern.

**Leerer Ordner:** Für einen Lauf ganz ohne vorhandene Dateien (Test «frisch geklont») lassen sich die Ordner
umlenken: `RSG2030_DATEN` (alles), einzeln `RSG2030_QUELLEN_DIR`, `RSG2030_EINGABEN_DIR`, `RSG2030_AUSGABE_DIR`.

---

## Release

Vor dem Tag in `CITATION.cff` `version`, `date-released` und bei jeder Referenz `date-accessed` setzen, beide Daten =
Tag des Release (`JJJJ-MM-TT`). Ohne Datum fehlt in der Zitation das Jahr. Abrufdatum ist der Tag des Release, weil
der Release-Lauf jede Quelle frisch lädt und ihre Prüfsumme prüft; die Spalte `Abgerufen` im Register bleibt das Datum
der geprüften Fassung. Fehlt etwas, bricht der Release-Lauf ab (Version oder Datum) bzw. die Testsuite
(`tests/test_zitation.py`). Die Daten trägt der Lauf nicht selbst ein: Der Tag zeigt schon auf den Commit, ein
nachträglicher Eintrag fehlte in der Version.

Ein Tag mit der Version (z. B. `2026.1`, muss der Version in `pyproject.toml` entsprechen) startet
`.github/workflows/release.yml`: frischer Download ohne Zwischenspeicher, `alles`, Vergleich mit
`erwartete_ausgaben.csv`, ganze Testsuite. Nur wenn alles grün ist, legt der Lauf das Release an und hängt die
beiden CSV-Dateien, die Excel-Mappe, den Prüfbericht, die Laufprotokolle und `SHA256SUMS.txt` an. Ist etwas rot,
entsteht kein Release; Tag löschen, Ursache beheben, neu taggen.

Zum Ausprobieren: ein Tag `test-…` (z. B. `test-release-1`) tut dasselbe, legt das Release aber nur als Entwurf an.
Danach Entwurf und Tag wieder löschen (`gh release delete test-release-1 --cleanup-tag`).

---

## Termine, die kein Wächter erkennt

Neue Fassungen, die unter einer **neuen Adresse** erscheinen, findet der Wächter nicht. Die bekannten Termine:

| Was | Wann | Was dann |
|---|---|---|
| Bevölkerungsprognose von Statistik Austria | in der Regel jährlich (laut Datensatz «Aktualisierungszeitraum: jährlich»), zuletzt 10.–12.11.2025 | prüfen, ob eine neue Datenversion mit dem neuen Jahrgang sinnvoll ist (METHODIK.md, R7) |
| ÖROK-Prognose (Anteile der Versorgungsregionen) | etwa alle drei bis fünf Jahre, zuletzt «ÖROK-Prognose 2021» (April 2022) | wie oben |
| ÖSG (Richtwerte, Versorgungsregionen) | bei Revisionen, zuletzt Stand 10.10.2025 | Text- und Tabellenband meldet der Wächter (RIS); Regionale Gliederung und Methodenband erscheinen bei der GÖG unter neuer Adresse: Richtwerte und Regionen neu prüfen, Quellen im Register ergänzen |

Diese Termine am besten in den eigenen Kalender eintragen.

**Hinweis zu GitHub:** In einem öffentlichen Repo schaltet GitHub zeitgesteuerte Workflows ab, wenn es 60 Tage keine
Aktivität gab. Dann den Wächter unter «Actions → Wächter → Enable workflow» wieder einschalten.
