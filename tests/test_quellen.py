"""Quellenregister `rsg2030/quellen/quellen.csv`: jede Datei vorhanden und unverändert (SHA-256)."""

from __future__ import annotations

import conftest  # noqa: F401  (Pfade)
import pytest

pytestmark = pytest.mark.slow  # liest alle Quelldateien


def test_quellen_vorhanden_und_unveraendert():
    from rsg2030.quellen import pruefe

    probleme = pruefe()
    assert not probleme, "\n".join(probleme)


def test_register_vollstaendig():
    from rsg2030.quellen import ist_rsg_verordnung, lade_quellen

    q = lade_quellen()
    assert not q.duplicated("Datei").any()
    assert set(q["Herkunft"]) == {"URL", "RIS"}
    assert q.loc[q["Herkunft"] == "URL", "Kennung"].str.startswith("https://").all()
    ris = q[q["Herkunft"] == "RIS"]
    # RIS: RSG-Verordnungen (mit Verordnungsstand) oder der ÖSG (ÖSG-Gutachten, ohne Stand)
    rsg = ist_rsg_verordnung(ris)
    assert (rsg | ris["Kennung"].str.match(r"SPG_AT_OSG_G_")).all()
    assert (ris.loc[rsg, "Stand"] != "").all() and (ris.loc[~rsg, "Stand"] == "").all()
    assert set(q["Verwendet"]) <= {"rsg_2030", "oesg_methodik", "Doku", "Abgleich"}
    assert q["SHA256"].str.fullmatch(r"[0-9a-f]{64}").all()


def test_archivkopien():
    """Jede URL-Quelle, die die Daten braucht, hat eine Archivkopie (Wayback, Rohdatei «id_»); RIS braucht keine."""
    from rsg2030.quellen import lade_quellen

    q = lade_quellen()
    url = q[q["Herkunft"] == "URL"]
    gebraucht = url[~url["Verwendet"].isin(["Doku", "Abgleich"])]
    assert (gebraucht["Archiv"] != "").all(), list(gebraucht.loc[gebraucht["Archiv"] == "", "Datei"])
    mit = url[url["Archiv"] != ""]
    assert mit["Archiv"].str.match(r"https://web\.archive\.org/web/\d{14}id_/").all()
    assert (mit["Archiv"].str.split("id_/", n=1).str[1] == mit["Kennung"]).all()
    assert (q.loc[q["Herkunft"] == "RIS", "Archiv"] == "").all()
