# Ergebnisse (`daten_ergebnis/`)

Entstehen mit `python -m rsg2030 alles`, **nicht in git**. Beschreibung jeder Spalte: [docs/DATEN.md](../docs/DATEN.md).

| Datei | erzeugt von |
|---|---|
| `RSG_2030_Planungsmatrizen.csv`, `RSG_2030_Planungsmatrizen.xlsx`, `Laufprotokoll_daten.json` | `python -m rsg2030 daten` |
| `RSG_2030_Versorgungsdichte.csv`, `Laufprotokoll_versorgungsdichte.json` | `python -m rsg2030 versorgungsdichte` |

Am Ende jedes Laufs steht, ob die CSV-Dateien Byte für Byte der veröffentlichten Version entsprechen
(✓ / ✗; erwartete Prüfsummen in `rsg2030/erwartete_ausgaben.csv`).
