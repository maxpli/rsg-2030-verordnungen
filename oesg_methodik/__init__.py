"""ÖSG-Methodik: Fach-Zuordnung, Planungsrichtwerte, Bevölkerung, Versorgungsdichte, Lage zum
Versorgungsdichte-Soll-Intervall (ÖSG).

Gilt für jeden Datensatz, der ÄAVE je Region liefert (Vertrag: `eingang.py`); kennt keinen Datensatz selbst
und importiert nichts aus `rsg2030` (Test `tests/test_pakete.py`). Regeln und Quellen: docs/METHODIK.md.
"""

BUNDESLAENDER = [
    "Burgenland",
    "Kärnten",
    "NÖ",
    "OÖ",
    "Salzburg",
    "Steiermark",
    "Tirol",
    "Vorarlberg",
    "Wien",
]
"""Kurznamen der Bundesländer, wie sie in allen Tabellen stehen (Reihenfolge = amtliche Kennziffer 1–9)."""

LAND_KURZ = {"Niederösterreich": "NÖ", "Oberösterreich": "OÖ"}
"""Bundesland-Name in ÖSG- und Statistik-Austria-Listen → Kurzname."""
