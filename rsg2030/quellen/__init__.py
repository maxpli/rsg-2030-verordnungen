"""Register aller Quelldateien (`quellen.csv`): Herkunft (URL oder RIS-Dokument), SHA-256, Zweck.

Eine Zeile je Datei unter `daten_original/` (nicht in git). Spalten: Datei (relativ zu `daten_original/`),
Herkunft (URL | RIS), Kennung (URL bzw. RIS-Dokumentnummer), Praefix (mehrere Verordnungen eines Landes),
Bundesland, Stand (Verordnungsstand, nur RSG-Verordnungen), SHA256, Abgerufen, Herausgeber, Verwendet (rsg_2030 =
liest die Pipeline | oesg_methodik = Bevölkerung | Doku = nur zum Nachlesen | Abgleich = liest nur ein Prüfskript unter
`rsg2030/scripts/`, nicht die Pipeline), Inhalt, Lizenz.
Archiv (Wayback-Kopie der geprüften Fassung, nur URL-Quellen).
Herkunft RIS sind die RSG-Verordnungen und der ÖSG (kundgemacht als ÖSG-Gutachten); `ist_rsg_verordnung` trennt sie.
Laden und prüfen: `python -m rsg2030 download` (`quellen.download`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from oesg_methodik.pfade import original_dir

QUELLEN_CSV = Path(__file__).with_name("quellen.csv")
# RIS-Dokumentnummer: SPG_<Land>_<RSG|OSG>_<V = Verordnung | G = Gutachten>_<Datum>_<Nummer>_<Jahr>
RSG_VERORDNUNG_RE = r"SPG_[A-Z]+_RSG_V_"


def lade_quellen(path: Path = QUELLEN_CSV) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def ist_rsg_verordnung(q: pd.DataFrame) -> pd.Series:
    """Maske: Zeile gehört zu einer RSG-Verordnung im RIS (nicht zum ÖSG oder einer URL-Quelle)."""
    return (q["Herkunft"] == "RIS") & q["Kennung"].str.match(RSG_VERORDNUNG_RE)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pruefe(quellen: pd.DataFrame | None = None, root: Path | None = None) -> list[str]:
    """Probleme je Datei (fehlt / Prüfsumme weicht ab); leere Liste = alles in Ordnung."""
    quellen = lade_quellen() if quellen is None else quellen
    root = root or original_dir()
    probleme: list[str] = []
    for _, q in quellen.iterrows():
        p = root / q["Datei"]
        if not p.is_file():
            probleme.append(f"fehlt: {q['Datei']} → python -m rsg2030 download")
        elif sha256(p) != q["SHA256"]:
            probleme.append(f"Prüfsumme weicht ab: {q['Datei']} – nicht die geprüfte Fassung (online geändert?)")
    return probleme
