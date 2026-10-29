"""Vertrag der Stellen-Eingangstabelle: was ein Datensatz an Stellen im ÖSG-Zuschnitt liefert.

Eine Zeile je Region × Abschnitt × Jahr × Stellen-Zeile × Fach. `Fach` ist im selben ÖSG-Zuschnitt wie bei den ÄAVE
(`faecher.ZUSCHNITT`), geschnitten von derselben Funktion (`faecher.summe_im_zuschnitt`) – nur so bedeutet ein Fach in
beiden Tabellen dasselbe. Der Adapter liegt beim Datensatz (`rsg2030.analyse_eingang.stellen_eingang`), dieses Modul
legt Spalten und Regeln fest. Bedeutung der Zeilen: docs/DATEN.md, «Stellen lesen»; Belege: docs/METHODIK.md,
«Stellen».

Drei Regeln, die hier durchgesetzt werden, weil sie leicht brechen:

1. **IST und PLAN verhalten sich entgegengesetzt – das ist die häufigste Falle.**
   *IST (`planstellen_…`):* **nicht summieren.** Dieselbe Stelle hat meist Verträge mit mehreren Trägern und steht
   deshalb in mehreren Zeilen; «die Werte dürfen nicht addiert werden» (Tabellenband S.231). Wien druckt für diesen
   Fall eine eigene, bereinigte Zeile (`planstellen_oegk_svs_bvaeb`) – wir rechnen sie weder aus den Trägern aus noch
   in sie hinein.
   *PLAN (`slst_…`):* **summierbar.** Gemeinsame Stellen aller Träger und zusätzliche einzelner Träger sind
   verschiedene Stellen (Tabellenband S.232). Beleg aus der Verordnung: Wiens gedruckte `slst_gesamt` ist in allen 27
   Fachspalten genau `slst_gemeinsam` + die drei `slst_zus_…` (Bundesland gesamt 3.065 + 0 + 264 + 217 = 3.546).
   Die Höchstzahl der Kassenpraxen **eines** Trägers ist dagegen gemeinsam × % + sein zusätzliches × %
   (docs/DATEN.md, «Stellen lesen») – dabei wird wieder nicht über Träger summiert.
   Abgeleitet wird hier nichts: Die Tabelle führt die gedruckten Zeilen, eine Gesamtzeile nur, wo das Land sie druckt.
2. **Prozentsätze werden nicht summiert.** Der Maximalanteil vertragsärztlicher Planstellen steht je Matrixspalte;
   gerechnet wird Stellen × Prozent je Spalte, erst danach summiert (`Max_VAEP_Stellen`). `Max_VAEP_Prozent` ist das
   Ergebnis geteilt durch die Stellen – ein gewichtetes Mittel, nie ein Mittel aus Prozentsätzen.
3. **Keine ZAE in den Stellen.** Sachleistungsstellen bilden den extramuralen Bereich ab (Tabellenband S.232), ZAE
   sind spitalsambulant (Vorlage (Tabellenband S.239), Fußnote (5)). `faecher.teile` lässt sie für Stellen-Zeilen von
   selbst weg; der Vertrag hält fest, dass das Absicht ist.
"""

from __future__ import annotations

import pandas as pd

from oesg_methodik.eingang import ABSCHNITTE, EBENEN
from oesg_methodik.faecher import OESG_ANALYSEKERN

SPALTEN = [
    "Datensatz",
    "Land",
    "Ebene",
    "Region_ID",
    "Abschnitt",
    "Jahr",
    "Zeile_ID",
    "Fach",
    "Stellen",
    "Zuschnitt",
    "Max_VAEP_Stellen",
    "Max_VAEP_Prozent",
]
"""`Zuschnitt`: aus welchen Matrixspalten der Wert entstand (`faecher.zuschnitt`), wörtlich wie in der Tabelle
Versorgungsdichte. `Max_VAEP_*`: leer, wo die Matrix keinen Maximalanteil führt (alle IST-Zeilen, `slst_eva`)."""
SCHLUESSEL = [c for c in SPALTEN if c not in ("Stellen", "Zuschnitt", "Max_VAEP_Stellen", "Max_VAEP_Prozent")]

IST_ZEILEN = ("planstellen_oegk", "planstellen_svs", "planstellen_bvaeb", "planstellen_oegk_svs_bvaeb")
"""Vertragsärztliche Planstellen je KV-Träger im IST (Tabellenband S.231). **Nicht addieren**: dieselbe Stelle steht
in mehreren Zeilen. `planstellen_oegk_svs_bvaeb` druckt nur Wien, als bereinigte Zeile statt dreier."""
PLAN_ZEILEN = ("slst_gemeinsam", "slst_eva", "slst_zus_oegk", "slst_zus_svs", "slst_zus_bvaeb", "slst_gesamt")
"""Sachleistungsstellen im PLAN (Tabellenband S.232): gemeinsame Stellen aller Träger, davon in Einrichtungen für
Erstversorgung-Allgemeinmedizin (`slst_eva`, **Teilmenge** – nicht dazuzählen), zusätzliche je Träger. Anders als im
IST sind gemeinsame und zusätzliche verschiedene Stellen und damit summierbar; `slst_gesamt` druckt nur Wien."""
ZEILEN = IST_ZEILEN + PLAN_ZEILEN

TEILMENGEN = {"slst_eva": "slst_gemeinsam"}
"""Zeile → Zeile, von der sie eine Teilmenge ist. Nicht zu `slst_gemeinsam` addieren, sonst doppelt gezählt."""
OHNE_PROZENT = ("slst_eva",) + IST_ZEILEN
"""Zeilen ohne Maximalanteil in der ÖSG-Vorlage. Bei `slst_eva` ist das keine Lücke der Länder, sondern die Vorlage:
Einen Prozentsatz zu setzen wäre eine Behauptung (docs/offene_punkte.md, «Sachleistungsstellen im ÖSG-Zuschnitt»)."""


def pruefe(eingang: pd.DataFrame) -> pd.DataFrame:
    """Prüft den Vertrag; gibt die Tabelle in Spaltenreihenfolge zurück."""
    fehlt = [c for c in SPALTEN if c not in eingang.columns]
    if fehlt:
        raise ValueError(f"Stellen-Eingang: Spalten fehlen: {fehlt}")
    e = eingang[SPALTEN]
    for spalte, erlaubt in (
        ("Ebene", EBENEN),
        ("Abschnitt", ABSCHNITTE),
        ("Zeile_ID", set(ZEILEN)),
        ("Fach", set(OESG_ANALYSEKERN)),
    ):
        anders = set(e[spalte]) - erlaubt
        if anders:
            raise ValueError(f"Stellen-Eingang: unbekannte Werte in {spalte}: {sorted(anders)}")
    for zeilen, abschnitt in ((IST_ZEILEN, "IST"), (PLAN_ZEILEN, "PLAN")):
        falsch = e[e["Zeile_ID"].isin(zeilen) & (e["Abschnitt"] != abschnitt)]
        if not falsch.empty:
            raise ValueError(f"Stellen-Eingang: {zeilen[0]}-Zeilen gibt es nur im {abschnitt}: {len(falsch)} Zeilen")
    if e["Stellen"].isna().any():
        raise ValueError("Stellen-Eingang: leere Stellen – fehlende Werte weglassen, nicht leer liefern")
    mit_prozent = e[e["Zeile_ID"].isin(OHNE_PROZENT) & e["Max_VAEP_Stellen"].notna()]
    if not mit_prozent.empty:
        raise ValueError(
            f"Stellen-Eingang: Maximalanteil bei {sorted(set(mit_prozent['Zeile_ID']))} – "
            "diese Zeilen haben in der ÖSG-Vorlage keinen"
        )
    doppelt = e.duplicated(SCHLUESSEL)
    if doppelt.any():
        raise ValueError(f"Stellen-Eingang: Schlüssel doppelt, z. B. {e[doppelt].iloc[0].to_dict()}")
    return e
