"""Wächter ohne Netz: Suche, Infoseite und Katalog werden durch gespeicherte Seiten ersetzt."""

from __future__ import annotations

from datetime import date

import pytest

from rsg2030 import waechter as w


def _ris(*nummern: str, hits: int | None = None) -> bytes:
    """OGD-Antwort mit einem Dokument je Nummer; Typ laut Kennung (…_RSG_V_… = RsgVerordnung, sonst OsgGutachten)."""
    import json

    doks = [
        {
            "Data": {
                "Metadaten": {
                    "Technisch": {"ID": n},
                    "Sonstige": {"Spg": {"Typ": "RsgVerordnung" if "_RSG_V_" in n else "OsgGutachten"}},
                }
            }
        }
        for n in nummern
    ]
    antwort = {
        "OgdSearchResult": {
            "OgdDocumentResults": {
                "Hits": {"@pageNumber": "1", "@pageSize": "100", "#text": str(hits or len(nummern))},
                "OgdDocumentReference": doks,
            }
        }
    }
    return json.dumps(antwort).encode()


def test_ris_abfrage_stichtag_und_typfilter(monkeypatch):
    """Die Abfrage geht an die OGD-Schnittstelle mit FassungVom; der Typ wird aus der Antwort gefiltert."""
    urls: list[str] = []

    def abrufen(url: str) -> bytes:
        urls.append(url)
        return _ris("SPG_A_RSG_V_1", "SPG_AT_OSG_G_1")

    monkeypatch.setattr(w, "abrufen", abrufen)
    assert w.ris_dokumente(date(2026, 10, 15)) == {"SPG_A_RSG_V_1"}
    assert "data.bka.gv.at" in urls[0] and "FassungVom=2026-10-15" in urls[0] and "Suchworte=2030" in urls[0]
    assert w.ris_dokumente(date(2026, 10, 15), typ="OsgGutachten", suchworte="") == {"SPG_AT_OSG_G_1"}
    assert "Suchworte" not in urls[1]


def test_ris_ohne_treffer_bricht_ab(monkeypatch):
    monkeypatch.setattr(w, "abrufen", lambda url: _ris())
    with pytest.raises(RuntimeError, match="ohne Treffer"):
        w.ris_dokumente()


def test_ris_mehr_als_eine_seite_bricht_ab(monkeypatch):
    monkeypatch.setattr(w, "abrufen", lambda url: _ris("SPG_A_RSG_V_1", hits=101))
    with pytest.raises(RuntimeError, match="mehr als eine Seite"):
        w.ris_dokumente()


def test_ris_neu_und_weg(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(w, "abrufen", lambda url: _ris("SPG_A_RSG_V_1", "SPG_B_RSG_V_2"))
    q = pd.DataFrame(
        {
            "Herkunft": ["RIS", "RIS", "RIS"],
            "Kennung": ["SPG_A_RSG_V_1", "SPG_C_RSG_V_3", "SPG_AT_OSG_G_4"],
            "Bundesland": ["A", "C", ""],
        }
    )
    h = w.pruefe_ris(q)
    assert any("SPG_B_RSG_V_2" in x and "neue" in x for x in h)
    assert any("SPG_C_RSG_V_3" in x and "nicht mehr" in x for x in h)
    assert len(h) == 2  # der ÖSG im Register ist keine weggefallene Verordnung


def test_oesg_neu_und_weg(monkeypatch):
    import pandas as pd

    q = pd.DataFrame({"Herkunft": ["RIS", "RIS"], "Kennung": ["SPG_A_RSG_V_1", "SPG_AT_OSG_G_1"]})
    monkeypatch.setattr(w, "abrufen", lambda url: _ris("SPG_AT_OSG_G_1"))
    assert w.pruefe_oesg(q) == []
    monkeypatch.setattr(w, "abrufen", lambda url: _ris("SPG_AT_OSG_G_2"))
    h = w.pruefe_oesg(q)
    assert len(h) == 2 and "neuer ÖSG SPG_AT_OSG_G_2" in h[0] and "SPG_AT_OSG_G_1 gilt nicht mehr" in h[1]


def test_ris_nicht_erreichbar_ist_hinweis(monkeypatch):
    """Ein RIS, das nicht antwortet (z. B. HTTP 503), ist ein Hinweis – der Lauf bricht nicht mit Traceback ab."""
    import urllib.error

    import pandas as pd

    def abrufen(url: str) -> bytes:
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(w, "abrufen", abrufen)
    q = pd.DataFrame({"Herkunft": ["RIS"], "Kennung": ["SPG_A_RSG_V_1"], "Bundesland": ["A"]})
    for hinweise in (w.pruefe_ris(q), w.pruefe_oesg(q)):
        assert len(hinweise) == 1 and "nicht erreichbar" in hinweise[0] and "503" in hinweise[0]


def test_originale(monkeypatch):
    import hashlib

    import pandas as pd

    q = pd.DataFrame(
        {
            "Herkunft": ["URL", "URL"],
            "Datei": ["a.csv", "b.csv"],
            "Kennung": ["https://x/a.csv", "https://x/b.csv"],
            "SHA256": [hashlib.sha256(b"a").hexdigest(), hashlib.sha256(b"b").hexdigest()],
            "Archiv": ["https://web.archive.org/web/1id_/https://x/a.csv", ""],
        }
    )
    monkeypatch.setattr(w, "abrufen", lambda url: b"a" if url.endswith("a.csv") else b"neu")
    h = w.pruefe_originale(q)
    assert len(h) == 1 and h[0].startswith("b.csv: online durch eine andere Fassung ersetzt")


def test_archiv(monkeypatch):
    """Archivkopie fehlt, ist eine andere Fassung (Wayback leitet auf die nächste Aufnahme um) oder nicht erreichbar."""
    import gzip
    import hashlib
    import urllib.error

    import pandas as pd

    sha = hashlib.sha256(b"a").hexdigest()
    q = pd.DataFrame(
        {
            "Herkunft": ["URL"] * 4,
            "Datei": ["ok.csv", "alt.csv", "weg.csv", "ohne.csv"],
            "Kennung": [""] * 4,
            "SHA256": [sha] * 4,
            "Archiv": ["https://web.archive.org/ok", "https://web.archive.org/alt", "https://web.archive.org/weg", ""],
        }
    )

    def abrufen(url: str) -> bytes:
        if url.endswith("weg"):
            raise urllib.error.URLError("404")
        return gzip.compress(b"a") if url.endswith("ok") else b"alt"

    monkeypatch.setattr(w, "abrufen", abrufen)
    h = w.pruefe_archiv(q)
    assert len(h) == 3
    assert h[0].startswith("alt.csv: Archivkopie ist nicht die geprüfte Fassung")
    assert h[1].startswith("weg.csv: Archivkopie nicht erreichbar")
    assert h[2].startswith("ohne.csv: keine Archivkopie")
