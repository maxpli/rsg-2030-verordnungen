"""Darstellung einer Zelle der Tabelle Versorgungsdichte in Worten: der Satz und die Vorbehalte.

Hier stehen die Texte **einmal**, für beide Darstellungen des Datensatzes: das Dashboard (`web.py` schreibt sie
nach `data.json`, `web/app.js` setzt sie ein) und die statischen Seiten (`lesefassung.py`). Zwei Kopien derselben
Vorbehalte würden auseinanderlaufen, sobald sich eine Lesart ändert – und die Vorbehalte müssen den Daten folgen
(CLAUDE.md, «Vorbehalte folgen den Daten»).

Was hier **nicht** steht: Farbstufen, Schraffur und Zahlformate. Die statischen Seiten haben keine Farben, und jede
Darstellung formatiert Zahlen selbst; geteilt ist nur, was wörtlich gleich sein muss.

Die Texte enthalten HTML (`<b>`) und Platzhalter `{0}`, `{1}` … in der Reihenfolge der Argumente. Sie urteilen nicht
über die Fallstricke in docs/DATEN.md hinaus; jeder Vorbehalt nennt den Fallstrick, der ihn trägt (Prüfung in
tests/test_web.py).
"""

from __future__ import annotations

import math
import re
from typing import NamedTuple


class Vorbehalt(NamedTuple):
    """Ein Vorbehalt: der Fallstrick aus docs/DATEN.md, der ihn trägt, und der Text mit Platzhaltern."""

    fallstrick: int
    text: str


VORBEHALTE: dict[str, Vorbehalt] = {
    "teil_von": Vorbehalt(
        4,
        "<b>Teil von {0}.</b> {1} steckt schon in {0} und hat zusätzlich ein eigenes Soll-Intervall. Nicht addieren.",
    ),
    "zae_in_fachspalten": Vorbehalt(
        4,
        "<b>ZAE nicht getrennt ausgewiesen.</b> Die zentrale ambulante Erstversorgung steckt hier in den "
        "Fachspalten, vor allem IM. AM ist zu niedrig, IM zu hoch.",
    ),
    "zae_umbuchung": Vorbehalt(
        10,
        "<b>IST → PLAN enthält eine Umbuchung</b> der ZAE von den Fachspalten nach AM, nicht nur Wachstum oder Abbau.",
    ),
    "kfo_korrekturregel": Vorbehalt(
        4,
        "<b>KFO in Oberösterreich:</b> nur als Fußnote zu ZMK gedruckt, ein Wert je Region, per Korrekturregel "
        "übernommen.",
    ),
    "kfo_nicht_getrennt": Vorbehalt(
        4,
        "<b>KFO nicht getrennt ausgewiesen.</b> {0} druckt keine KFO-Spalte; die Kieferorthopädie ist in ZMK "
        "enthalten, nur nicht einzeln gezeigt. Der ZMK-Wert ist vollständig.",
    ),
    "wien_zmk_breiter": Vorbehalt(
        4,
        "<b>Wien rechnet mehr zu ZMK.</b> Fußnote (5) der Wiener Matrizen sagt «ZMK: Zahn-, Mund- und "
        "Kieferheilkunde + Zahnbehandler + Dentisten». Ob die anderen Länder ebenso zählen, sagen sie nicht – der "
        "Wiener ZMK-Wert kann breiter abgegrenzt sein.",
    ),
    "ooe_plan_spitalsambulant": Vorbehalt(
        8,
        "<b>OÖ PLAN spitalsambulant</b> ist laut Fußnote das fortgeschriebene IST 2022, kein neuer Plan.",
    ),
    "sve_block": Vorbehalt(
        3,
        "<b>{0} plant in SVE</b>, nicht in ÄAVE. Gezeigt sind die ÄAVE-Äquivalente aus dem zweiten Block der "
        "Matrix (im PDF «ÄAVE-Ä»); nur die sind mit den anderen Ländern vergleichbar.",
    ),
    "wien": Vorbehalt(
        11,
        "<b>Wien</b> ist nicht Basis der Soll-Intervalle (Bundesdurchschnitt ohne Wien) und versorgt das Umland "
        "mit; Regionen mit Zentrumsfunktion liegen deshalb eher höher.",
    ),
    "unter_einer_aave": Vorbehalt(
        6,
        "<b>Weniger als 1 ÄAVE vom Intervall entfernt.</b> Lage und Position sind hier nicht belastbar.",
    ),
    "keine_patientenstroeme": Vorbehalt(
        11,
        "<b>Ohne Patientenströme.</b> Regionen mit Zentrumsfunktion liegen eher höher, ihr Umland eher tiefer.",
    ),
    "ist_an_norm_2030": Vorbehalt(
        11,
        "<b>IST an der Norm 2030 gemessen.</b> Das zeigt den Abstand zur Norm 2030, keine Verletzung im "
        "IST-Jahr. IST-Jahr dieses Landes: {0}.",
    ),
}
"""Jeder Vorbehalt, den eine Darstellung zeigen kann: Kennung → Fallstrick und Text."""

SATZ: dict[str, str] = {
    "kein": "<p>{0}: kein Wert.</p>",
    "im": "<p>{0}: <b>im Soll-Intervall</b>.</p>",
    "unter": '<p>{0}: Bis zur Untergrenze fehlen <b class="num">{1}</b> ÄAVE Sachleistung.</p>',
    "über": '<p>{0}: <b class="num">{1}</b> ÄAVE über der Obergrenze.</p>',
}
"""Der Wert in Worten, je Lage zum Soll-Intervall: {0} = Beschriftung (z. B. «PLAN 2030»), {1} = ÄAVE-Abstand."""

NICHT_GETRENNT = "nicht getrennt ausgewiesen"
"""Ende der Zuschnitt-Texte «<Fach> nicht getrennt ausgewiesen» (ZAE, KFO)."""
ZAE_NICHT_GETRENNT = f"ZAE {NICHT_GETRENNT}"
"""Text in `Zuschnitt`, wenn die ZAE in den Fachspalten stecken statt in SON/IDB (docs/DATEN.md, Fallstrick 4)."""
KFO_NICHT_GETRENNT = f"KFO {NICHT_GETRENNT}"
"""Text in `Zuschnitt`, wenn ein Land keine KFO-Spalte druckt (Wien, Vorarlberg); KFO steckt dann in ZMK."""
KFO_KORREKTURREGEL = "per Korrekturregel"
"""Text in `Zuschnitt`, wenn KFO nur aus einer Fußnote kommt (Oberösterreich)."""

KEIN_WERT: dict[str, str] = {
    "in_elternfach": "Diese Matrix weist {0} nicht getrennt aus; die Werte stecken in {1} und sind dort "
    "vollständig. Die Seite der Matrix steht trotzdem hier, zum Nachsehen.",
    "keine_spalte": "Die Matrix dieses Landes hat keine Spalte {0} – dort gibt es keinen Wert, auch keine 0. "
    "Die Seite der Matrix steht trotzdem hier, zum Nachsehen.",
    "zelle_leer": "Die Spalte {0} gibt es in dieser Matrix, die Zelle ist aber leer. Die Seite der Matrix steht "
    "hier, zum Nachsehen.",
}
"""Warum eine Zelle keinen Wert hat: {0} = Fach, {1} = Fach, in dem es steckt. Auch ohne Wert nennt die
Darstellung PDF und Seite, damit man nachsehen kann, dass dort wirklich nichts steht (docs/WEB.md)."""


def kein_wert(
    *, fach: str, teil_von: str | None, zuschnitt_elternfach: str | None, spalte_in_matrix: bool
) -> tuple[str, tuple[str, ...]]:
    """Welcher Text erklärt, dass diese Zelle keinen Wert hat – Kennung aus `KEIN_WERT` und seine Argumente."""
    if teil_von and f"{fach} {NICHT_GETRENNT}" in (zuschnitt_elternfach or ""):
        return ("in_elternfach", (fach, teil_von))
    if not spalte_in_matrix:
        return ("keine_spalte", (fach,))
    return ("zelle_leer", (fach,))


ZAE_FAECHER = ("AM", "IM")
"""Fächer, deren Werte der ZAE-Zuschnitt verschiebt: AM zu niedrig, IM zu hoch (docs/METHODIK.md, R5)."""


class Zelle(NamedTuple):
    """Eine Zelle der Zeile «insgesamt», so weit die Darstellung sie braucht."""

    lage: str | None
    """`unter`, `im`, `über` – oder None, wenn die Region das Fach nicht ausweist."""
    aave_abstand: float | None
    """`AAVE_Abstand_Intervall`: 0 im Intervall, sonst der Abstand zur nächsten Grenze."""
    zuschnitt: str | None
    """`Zuschnitt` der Zelle, wörtlich aus der Tabelle."""
    jahr: int | None
    """`Jahr` der Zelle (IST-Jahr des Landes bzw. 2030)."""


def _fehlt(x: float | None) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def unter_einer_aave(zelle: Zelle | None) -> bool:
    """Liegt die Zelle außerhalb des Intervalls, aber weniger als 1 ÄAVE davon entfernt? (Fallstrick 6)"""
    if zelle is None or zelle.lage in (None, "im") or _fehlt(zelle.aave_abstand):
        return False
    return abs(float(zelle.aave_abstand or 0.0)) < 1


def vorbehalte(
    *,
    fach: str,
    teil_von: str | None,
    abschnitt: str,
    ebene: str,
    land: str,
    land_name: str,
    block: str | None,
    zelle: Zelle | None,
    am_ist: Zelle | None,
    am_plan: Zelle | None,
    ist_jahr: int | None,
) -> list[tuple[str, tuple[str, ...]]]:
    """Welche Vorbehalte für diese Zelle gelten, in der Reihenfolge, in der sie gezeigt werden.

    Gibt je Vorbehalt die Kennung aus `VORBEHALTE` und die Argumente seiner Platzhalter zurück – nicht den
    fertigen Text, damit `data.json` jeden Text nur einmal enthält.

    `zelle` ist die Zelle des gezeigten Abschnitts, `am_ist`/`am_plan` die AM-Zellen derselben Region (für die
    Umbuchung der ZAE), `block` der maßgebliche Block der Matrix (`aequivalent` bei den Ländern, die in SVE planen).
    """
    out: list[tuple[str, tuple[str, ...]]] = []
    am = am_ist if abschnitt == "IST" else am_plan

    if teil_von:
        out.append(("teil_von", (teil_von, fach)))
    if fach in ZAE_FAECHER and am is not None and ZAE_NICHT_GETRENNT in (am.zuschnitt or ""):
        out.append(("zae_in_fachspalten", ()))
    if fach in ZAE_FAECHER and am_ist is not None and am_plan is not None:
        ist, plan = ZAE_NICHT_GETRENNT in (am_ist.zuschnitt or ""), ZAE_NICHT_GETRENNT in (am_plan.zuschnitt or "")
        if ist != plan:
            out.append(("zae_umbuchung", ()))
    if zelle is not None and KFO_KORREKTURREGEL in (zelle.zuschnitt or ""):
        out.append(("kfo_korrekturregel", ()))
    if zelle is not None and KFO_NICHT_GETRENNT in (zelle.zuschnitt or ""):
        out.append(("kfo_nicht_getrennt", (land_name,)))
    # Nur Wien sagt in seiner Fußnote, was außer KFO noch in ZMK steckt (docs/DATEN.md, Fallstrick 4)
    if land == "Wien" and fach == "ZMK":
        out.append(("wien_zmk_breiter", ()))
    if land == "OÖ" and abschnitt == "PLAN":
        out.append(("ooe_plan_spitalsambulant", ()))
    if block == "aequivalent":
        out.append(("sve_block", (land_name,)))
    if land == "Wien":
        out.append(("wien", ()))
    if unter_einer_aave(zelle):
        out.append(("unter_einer_aave", ()))
    if ebene == "VR":
        out.append(("keine_patientenstroeme", ()))
    if abschnitt == "IST":
        out.append(("ist_an_norm_2030", (str(ist_jahr) if ist_jahr is not None else "–",)))
    return out


def zahl(x: float | None, stellen: int = 1) -> str:
    """Zahl wie auf der Seite: Komma als Dezimaltrennzeichen, Minus als «−» (U+2212), fehlender Wert als «–»."""
    if _fehlt(x):
        return "–"
    s = f"{float(x or 0.0):.{stellen}f}".replace(".", ",")
    return s.replace("-", "−")


def satz(zelle: Zelle | None, beschriftung: str) -> str:
    """Der Wert in Worten, wie in der Detailspalte des Dashboards («Bis zur Untergrenze fehlen … ÄAVE»)."""
    if zelle is None or zelle.lage is None:
        return SATZ["kein"].format(beschriftung)
    if zelle.lage == "im":
        return SATZ["im"].format(beschriftung)
    abstand = float(zelle.aave_abstand or 0.0)
    if zelle.lage == "unter":
        return SATZ["unter"].format(beschriftung, zahl(-abstand))
    return SATZ["über"].format(beschriftung, zahl(abstand))


def platzhalter(text: str) -> set[int]:
    """Die Platzhalter eines Textes (`{0}`, `{1}` …) – für die Prüfung, dass die Argumente dazu passen."""
    return {int(n) for n in re.findall(r"\{(\d+)\}", text)}
