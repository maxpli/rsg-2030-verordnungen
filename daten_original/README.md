# Quellen (`daten_original/`)

Die Quelldateien, **nicht in git**. Laden und prüfen:

```bash
python -m rsg2030 download
```

Woher jede Datei kommt (RIS-Dokumentnummer bzw. URL), ihre SHA-256-Prüfsumme, wofür sie gebraucht wird und unter
welcher Lizenz sie steht, steht im Register [`rsg2030/quellen/quellen.csv`](../rsg2030/quellen/quellen.csv).

```
rsg_2030/<bundesland>/   Verordnungen und Anlagen aus dem RIS (z. B. kaernten, niederoesterreich)
statistik_austria/       Open Data: Bevölkerung zu Jahresbeginn (2021–2023), Prognose 2025; ÖROK-Prognose 2021
oesg/                    ÖSG-Textband, Tabellenband, Methodenband, Regionale Gliederung
rsg_monitoring/          RSG-Monitoring der GÖG, Kurzfassungen 2024 und 2025 – nur für den Abgleich
                         (`python -m rsg2030.scripts.monitoring_abgleich`), nicht für die Daten
```

Ordnernamen nur mit Kleinbuchstaben, Ziffern, `_` und `-`; Dateien behalten den Namen der Quelle, aber nur mit
ASCII-Buchstaben, Ziffern, `_`, `-` und `.` (keine Leerzeichen, keine Umlaute), damit Pfade auf jedem System gleich
funktionieren. Aus dem RIS werden die PDF-Dateien eines Verordnungsdokuments geladen (Verordnung und Anlagen); das
Register führt die, die geprüft und gebraucht werden.
