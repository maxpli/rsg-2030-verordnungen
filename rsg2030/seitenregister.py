"""RSG-2030-Verordnungen: Bundesland → PDF und Seiten der Planungsmatrizen (BL + VR).

Register: `eingaben/2026/seiten.csv` (eine Zeile je Matrix, Seiten 1-basiert wie im PDF-Viewer).
Intern sind Seitenangaben 0-basiert. Erzeugt von `python -m rsg2030 seiten` (scripts/seiten.py) aus den PDFs;
tests/test_seitenregister.py prüft, dass das Register dazu passt.

Seiten ohne Textebene (Bilder) erkennt `matrix_extract.hat_textebene`; sie werden manuell erfasst,
siehe `manuell.py`. Kärnten und Steiermark planen in SVE; ihre Matrizen enthalten
zusätzlich einen Block «ÄAVE-Äquivalente» (Kärnten VR 22: Spalte «Folgeseiten»).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from rsg2030.config import quellen_dir, seiten_csv


@dataclass(frozen=True)
class VrSeite:
    """Planungsmatrix einer Versorgungsregion (gleiche Struktur wie die BL-Matrix)."""

    region_id: str
    region_name: str
    seite_idx: int
    """0-basierter Seitenindex in der PDF."""
    folgeseiten_idx: tuple[int, ...] = ()
    """Folgeseiten, auf denen dieselbe Matrix weitergeht (z. B. ÄAVE-Äquivalente-Block)."""


@dataclass(frozen=True)
class Rsg2030Quelle:
    land: str
    pdf: Path
    seite_idx: int
    """0-basierter Seitenindex in der PDF."""
    vr: tuple[VrSeite, ...] = ()
    """Planungsmatrizen der Versorgungsregionen."""


def lade_seitenregister(path: Path | None = None) -> tuple[Rsg2030Quelle, ...]:
    """Register laden (bei jedem Aufruf neu, klein); fehlt seiten.csv (neuer Verordnungsstand), ist es leer →
    `python -m rsg2030 seiten`."""
    path = path or seiten_csv()
    if not path.is_file():
        return ()
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    quellen = quellen_dir()
    out: list[Rsg2030Quelle] = []
    for land, g in df.groupby("Land", sort=False):
        bl = g[g["Ebene"] == "BL"]
        if len(bl) != 1:
            raise ValueError(f"{path.name}: {land} braucht genau eine BL-Zeile, hat {len(bl)}")
        vr = tuple(
            VrSeite(
                region_id=r["Region_ID"],
                region_name=r["Region_Name"],
                seite_idx=int(r["Seite"]) - 1,
                folgeseiten_idx=tuple(int(p) - 1 for p in r["Folgeseiten"].split(";") if p),
            )
            for _, r in g[g["Ebene"] == "VR"].iterrows()
        )
        b = bl.iloc[0]
        out.append(Rsg2030Quelle(land, quellen / b["Datei"], int(b["Seite"]) - 1, vr))
    return tuple(out)
