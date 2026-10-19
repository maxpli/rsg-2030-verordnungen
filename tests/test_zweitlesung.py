"""Zweitlesung lesen: was verglichen wird und was nicht. Ohne Quelldateien."""

from __future__ import annotations

from rsg2030.zweitlesung import _norm, _verkuerzt, lese


def test_unvollstaendige_zeile_wird_nicht_verglichen(tmp_path):
    """Weniger Werte als Spalten: unklar, welcher Wert in welche Spalte gehört → nicht verglichen, gemerkt.
    Eine Zeile ohne einen einzigen Wert ist eine Leerzeile; «KIC» ist KJC (I/J verwechselt)."""
    datei = tmp_path / "x_bl.tsv"
    datei.write_text(
        "# Zweitlesung\n"
        "#Abschnitt\tIST ÄAVE 2022\n"
        "#Kopf\tAM\tKIC(1)\tgesamt\n"
        "ÄAVE insgesamt 2022\t1,0\t–\t1,0\n"
        "- davon ÄAVE in PVE\t0,5\t0,5\n"
        "(ohne Beschriftung)\t\t\t\n",
        encoding="utf-8",
    )
    zuordnung = {
        ("haupt", "IST", _norm("ÄAVE insgesamt 2022")): "insgesamt",
        ("haupt", "IST", _norm("- davon ÄAVE in PVE")): "pve",
    }
    les = lese(datei, zuordnung)
    assert list(zip(les.zellen["Zeile_ID"], les.zellen["Fach"], les.zellen["Roh"])) == [
        ("insgesamt", "AM", "1,0"),
        ("insgesamt", "KJC", "–"),
        ("insgesamt", "gesamt", "1,0"),
    ]
    assert les.unvollstaendig == {("haupt", "IST", "pve")}
    assert not any("ohne Beschriftung" in u for u in les.unbekannt)


def test_verkuerzte_beschriftung():
    """Fehlende Wörter in der Beschriftung: Zuordnung nur, wenn genau eine Zeile der Gruppe alle Wörter in Reihenfolge hat."""
    zuordnung = {
        ("aequivalent", "IST", _norm("Umrechnungsfaktor für ÄrztInnen spitalsambulant")): "umr_spitalsambulant",
        ("aequivalent", "IST", _norm("Umrechnungsfaktor für ÄrztInnen in Kassenambulatorien")): "umr_kassen_amb",
    }
    assert _verkuerzt("Umrechnungsfaktor für spitalsambulant", "aequivalent", "IST", zuordnung) == "umr_spitalsambulant"
    assert _verkuerzt("Umrechnungsfaktor für ÄrztInnen", "aequivalent", "IST", zuordnung) is None  # zwei passen
    assert _verkuerzt("spitalsambulant Umrechnungsfaktor", "aequivalent", "IST", zuordnung) is None  # Reihenfolge
    assert _verkuerzt("Umrechnungsfaktor für spitalsambulant", "haupt", "IST", zuordnung) is None  # andere Gruppe
