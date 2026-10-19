"""RSG 2030: Extraktion, Korrekturen, Prüfungen, Freigabe-Mappe und erwartete Long-CSV (langsam: liest alle PDFs)."""

from __future__ import annotations

import pandas as pd
import pytest
from conftest import pruefe_ausgabe

pytestmark = pytest.mark.slow


def _fmt(df: pd.DataFrame, cols: list[str]) -> str:
    return df[cols].to_string(index=False, max_rows=40)


def test_parser_ohne_fehler(pipeline):
    issues = pipeline.issues
    fehler = issues[issues["Schwere"] == "fehler"]
    assert fehler.empty, "Parser-Fehler:\n" + _fmt(fehler, ["Land", "Region_ID", "Seite", "Art", "Detail"])


def test_alle_matrizen_vorhanden(pipeline):
    from rsg2030.seitenregister import lade_seitenregister

    long = pipeline.long
    for src in lade_seitenregister():
        assert ((long["Land"] == src.land) & (long["Ebene"] == "BL")).any(), f"BL-Matrix fehlt: {src.land}"
        for vr in src.vr:
            assert (long["Region_ID"] == vr.region_id).any(), f"VR-Matrix fehlt: {src.land} VR {vr.region_id}"


def test_keine_offenen_pruefabweichungen(pipeline):
    c = pipeline.checks
    offen = c[c["Status"] == "abweichung"]
    assert offen.empty, (
        f"{len(offen)} unbegründete Abweichungen (klären und ggf. in korrekturen.csv / "
        "bekannte_abweichungen.csv begründen):\n"
        + _fmt(
            offen, ["Check", "Land", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach", "Wert", "Soll", "Detail"]
        )
    )


def test_korrekturen_greifen(pipeline):
    """Jede Regel in korrekturen.csv ändert mindestens eine Zelle (sonst wirft korrigiere), und jede geänderte Zelle ist
    in der Long-CSV als «korrigiert» sichtbar – außer eine Ableitung füllt sie danach (Vorarlberg VR 82: falsche «0» →
    leer → gesamt-% abgeleitet; `Roh` zeigt weiter die «0»)."""
    from rsg2030.schema import ZELLE

    log = pipeline.korrekturen
    assert not log.empty
    long = pipeline.long.astype({"Region_ID": str})
    zellen = log.astype({"Region_ID": str})[
        ZELLE
    ].drop_duplicates()  # eine Zelle kann mehrere Regeln nacheinander haben
    danach_abgeleitet = zellen.merge(long.loc[long["Quelle"] == "abgeleitet", ZELLE], on=ZELLE)
    assert len(danach_abgeleitet) == 1
    assert (long["Quelle"] == "korrigiert").sum() + len(danach_abgeleitet) == len(zellen)


def test_freigabe_mappe_aktuell(pipeline):
    """freigabe.xlsx passt zum Datenstand – dieselbe Prüfung wie im Ablauf: keine Zeile fehlt oder ist verfallen, und keine
    Bestätigung nennt einen anderen Wert laut PDF als den gelesenen. Offene Zeilen sind erlaubt (Freigabe noch im Gang);
    ob alles bestätigt ist, meldet `python -m rsg2030 daten` («FREIGEGEBEN»). Nachziehen: `python -m rsg2030 freigabe`."""
    from rsg2030.freigabe import stand

    st = stand(pipeline)
    assert st.abweichend.empty, "Lesefehler laut Freigabe:\n" + st.abweichend.to_string()
    nicht = {
        n: (b.neu, b.verfallen, b.entfallen) for n, b in st.blaetter.items() if b.neu or b.verfallen or b.entfallen
    }
    assert not nicht, f"freigabe.xlsx nicht auf dem Datenstand (neu, verfallen, entfallen): {nicht}"


def test_long_csv_aktuell(pipeline):
    """Pipeline-Ergebnis = erwartete Long-CSV (SHA-256 in rsg2030/erwartete_ausgaben.csv), Zeichen für Zeichen
    (alle Spalten, auch Roh/Quelle/Regel). Die Datei selbst liegt nicht in git."""
    from rsg2030.config import LONG_DATEI, ausgabe_dir
    from rsg2030.pipeline import LONG_CSV_FORMAT

    text = pipeline.long.to_csv(index=False, **LONG_CSV_FORMAT)
    pruefe_ausgabe(LONG_DATEI, text, ausgabe_dir() / LONG_DATEI)


def test_long_csv_schema(pipeline):
    """Vertrag (schema.py): Spalten, eindeutiger Zellschlüssel, erlaubte Werte."""
    from rsg2030 import schema as s

    long = pipeline.long
    assert list(long.columns) == s.LONG_SPALTEN
    assert not long.duplicated(s.ZELLE).any(), "Zellschlüssel nicht eindeutig"
    assert set(long["Land"]) == set(s.LAENDER)
    assert set(long["Ebene"]) <= s.EBENEN and set(long["Abschnitt"]) <= s.ABSCHNITTE
    assert set(long["Quelle"]) <= s.QUELLEN and set(long["Einheit"]) <= s.EINHEITEN
    assert set(long["Block"]) <= {s.BLOCK_HAUPT, s.BLOCK_AEQ}
    assert set(long["Fach"]) <= {*s.FACHSPALTEN, s.GESAMT}, set(long["Fach"]) - {*s.FACHSPALTEN, s.GESAMT}
    assert long["Wert"].dropna().map(lambda v: isinstance(v, float)).all()


def test_bekannte_abweichungen_aktuell(pipeline):
    """Jede Zeile in bekannte_abweichungen.csv trifft noch eine Prüfung (sonst veraltet → entfernen)."""
    from rsg2030.checks import lade_bekannte_abweichungen

    checks = pipeline.checks
    bekannt = checks[checks["Status"] == "bekannt"]
    veraltet = []
    for _, k in lade_bekannte_abweichungen().iterrows():
        sel = pd.Series(True, index=bekannt.index)
        for c in ("Check", "Land", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"):
            if k[c] != "*":
                sel &= bekannt[c].astype(str) == str(k[c])
        if not sel.any():
            veraltet.append(k.to_dict())
    assert not veraltet, "Veraltete Einträge in bekannte_abweichungen.csv:\n" + "\n".join(map(str, veraltet))
