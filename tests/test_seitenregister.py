"""Seitenregister: `python -m rsg2030 seiten` erzeugt aus den PDFs genau die eingecheckte seiten.csv.

Bildseiten (ohne Textebene) nimmt der Test mit dem Vorschlag des Skripts an (Bildseite zwischen den
Nachbarmatrizen) – so fällt auch auf, wenn eine Bildseite an anderer Stelle liegt als erwartet.
"""

from __future__ import annotations

import conftest  # noqa: F401
import pandas as pd
import pytest

from rsg2030.config import seiten_csv
from rsg2030.scripts.seiten import vorschlag

pytestmark = pytest.mark.slow


def test_seiten_aus_pdfs_wie_register():
    neu, offen = vorschlag(interaktiv=False)
    assert not offen, offen
    alt = pd.read_csv(seiten_csv(), dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(neu.astype(str), alt)
