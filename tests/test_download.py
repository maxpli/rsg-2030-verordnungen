"""Download einer URL-Quelle mit Rückgriff auf die Archivkopie (ohne Netz: `abrufen` ersetzt)."""

from __future__ import annotations

import hashlib
import urllib.error

import pandas as pd
import pytest

from rsg2030.quellen import download as d

GEPRUEFT, NEU = b"gepruefte Fassung", b"neue Fassung"


def _quelle(archiv: str = "https://web.archive.org/web/1id_/https://x/a.csv") -> pd.Series:
    return pd.Series(
        {
            "Datei": "x/a.csv",
            "Kennung": "https://x/a.csv",
            "SHA256": hashlib.sha256(GEPRUEFT).hexdigest(),
            "Archiv": archiv,
        }
    )


@pytest.mark.parametrize(
    "original, erwartet",
    [
        (GEPRUEFT, GEPRUEFT),  # Original unverändert
        (NEU, GEPRUEFT),  # Original überschrieben → Archivkopie
        (None, GEPRUEFT),  # Original weg → Archivkopie
    ],
)
def test_archivkopie(tmp_path, monkeypatch, original, erwartet):
    def abrufen(url: str, netz_versuche: int = 2) -> bytes:
        if url.startswith("https://web.archive.org/"):
            return GEPRUEFT
        if original is None:
            raise urllib.error.URLError("weg")
        return original

    monkeypatch.setattr(d, "abrufen", abrufen)
    assert d._url_quelle(_quelle(), neu=False, root=tmp_path)
    assert (tmp_path / "x/a.csv").read_bytes() == erwartet


def test_ohne_archiv_bleibt_neue_fassung(tmp_path, monkeypatch):
    """Ohne Archivkopie wird gespeichert, was da ist – die Prüfsummen-Kontrolle danach meldet die Abweichung."""
    monkeypatch.setattr(d, "abrufen", lambda url, **_: NEU)
    assert d._url_quelle(_quelle(archiv=""), neu=False, root=tmp_path)
    assert (tmp_path / "x/a.csv").read_bytes() == NEU


def test_archivkopie_gzip(tmp_path, monkeypatch):
    """Wayback liefert manche Dateien gzip-komprimiert (so, wie der Server sie übertrug) – wird entpackt."""
    import gzip

    monkeypatch.setattr(d, "abrufen", lambda url, **_: gzip.compress(GEPRUEFT) if "web.archive.org" in url else NEU)
    assert d._url_quelle(_quelle(), neu=False, root=tmp_path)
    assert (tmp_path / "x/a.csv").read_bytes() == GEPRUEFT


def test_archivkopie_nicht_erreichbar(tmp_path, monkeypatch):
    """Antworten Original und Archiv nicht: kein Abbruch, keine Datei – die Prüfsummen-Kontrolle meldet «fehlt»."""

    def abrufen(url: str, netz_versuche: int = 2) -> bytes:
        raise TimeoutError("timed out")

    monkeypatch.setattr(d, "abrufen", abrufen)
    assert not d._url_quelle(_quelle(), neu=False, root=tmp_path)
    assert not (tmp_path / "x/a.csv").exists()


def test_stummer_server_wird_nicht_weiter_angefragt(monkeypatch):
    """Höchstens zwei Versuche mit langer Pause, danach keine Anfrage mehr an diesen Server – auch nicht für andere
    Dateien dort. Ein anderer Server wird weiter angefragt."""
    anfragen: list[str] = []
    pausen: list[float] = []

    def urlopen(req, timeout, context):
        anfragen.append(req.full_url)
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(d.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(d.time, "sleep", pausen.append)
    monkeypatch.setattr(d, "_unerreichbar", set())

    with pytest.raises(urllib.error.URLError):
        d.abrufen("https://stumm.example/a.pdf")
    assert len(anfragen) == 2
    assert d.PAUSE_NETZ_S in pausen

    with pytest.raises(urllib.error.URLError):
        d.abrufen("https://stumm.example/b.pdf")
    assert len(anfragen) == 2  # gesperrt, keine Anfrage

    with pytest.raises(urllib.error.URLError):
        d.abrufen("https://anders.example/c.pdf", netz_versuche=1)
    assert len(anfragen) == 3  # ein Versuch, weil eine Archivkopie einspringt


def test_pdf_links_nur_das_exakte_dokument():
    """OGD-Antwort: Die Dokumentnummer wirkt als Suche – gelesen wird nur das Dokument mit exakt dieser ID,
    nur PDF-Adressen, und ein einzelnes Element kommt in der Antwort ohne Liste (beide Formen)."""

    def dok(id_, inhalte):
        return {"Data": {"Metadaten": {"Technisch": {"ID": id_}}, "Dokumentliste": {"ContentReference": inhalte}}}

    antwort = {
        "OgdSearchResult": {
            "OgdDocumentResults": {
                "OgdDocumentReference": [
                    dok(
                        "SPG_X_1",
                        [
                            {  # Hauptdokument: Liste mehrerer Formate, nur das PDF zählt
                                "Urls": {
                                    "ContentUrl": [
                                        {"DataType": "Html", "Url": "https://ogd.x/SPG_X_1/a.html"},
                                        {"DataType": "Authentisch", "Url": "https://ogd.x/SPG_X_1/a.pdf"},
                                    ]
                                }
                            },
                            # Anlage: einzelnes Element ohne Liste
                            {"Urls": {"ContentUrl": {"DataType": "Authentisch", "Url": "https://ogd.x/SPG_X_1/b.pdf"}}},
                        ],
                    ),
                    dok(
                        "SPG_X_10",
                        [{"Urls": {"ContentUrl": {"DataType": "Authentisch", "Url": "https://ogd.x/falsch.pdf"}}}],
                    ),
                ]
            }
        }
    }
    assert d.pdf_links(antwort, "SPG_X_1") == ["https://ogd.x/SPG_X_1/a.pdf", "https://ogd.x/SPG_X_1/b.pdf"]
    assert d.pdf_links(antwort, "SPG_X_99") == []
