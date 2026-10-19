"""RSG-2030-Planungsmatrizen über PDF-Koordinaten auslesen (ambulanter Block, BL + VR).

Jede Zahl wird über ihre x-Position der Fachspalte zugeordnet, deren Kopf darüber steht —
keine Heuristiken über Token-Reihenfolge. Was sich nicht eindeutig zuordnen lässt, landet
als Issue im Ergebnis statt geraten zu werden.

Ergebnis ist eine Long-Tabelle (eine Zeile je Region × Block × Abschnitt × Zeile × Fach).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pandas as pd
import pdfplumber

from rsg2030.schema import BLOCK_AEQ, BLOCK_HAUPT, GESAMT
from rsg2030.seitenregister import Rsg2030Quelle
from rsg2030.specs import fachspalte

# Block «haupt» = Matrix in der Planungsgröße des Landes (ÄAVE oder SVE);
# Block «aequivalent» = Zusatzblock «sofern Planungsgröße nicht ÄAVE gemäß ÖSG» (Ktn, Stmk).


@dataclass(frozen=True)
class ZeilenDef:
    zeile_id: str
    bereich: str
    """aave | planstellen | standorte | slst | umr"""
    muster: re.Pattern[str]
    """Regex auf das kompakte Label (lowercase, ohne Leerzeichen)."""
    einheit: str
    abschnitt: str | None = None
    """Nur für Zeilen, die nur in IST bzw. PLAN vorkommen dürfen."""


def _r(p: str) -> re.Pattern[str]:
    return re.compile(p)


# Einzige Quelle für Zeilennamen. Reihenfolge = Prüfreihenfolge (erster Treffer gewinnt).
ZEILEN_DEFS: tuple[ZeilenDef, ...] = (
    # --- ÄAVE (IST und PLAN) ---
    ZeilenDef("spitalsambulant", "aave", _r(r"^(sve|äave(-ä)?)spitalsambulant"), "ÄAVE"),
    ZeilenDef("wahl", "aave", _r(r"^äave(\(ggf\.sve\)|/äave-ä)?wahlärztinnen"), "ÄAVE", "IST"),
    ZeilenDef("niedergelassen", "aave", _r(r"^äaveniedergelasseneärztinnengesamt"), "ÄAVE", "IST"),
    ZeilenDef("extramural", "aave", _r(r"^äaveniedergelasseneärztinnenundin"), "ÄAVE"),
    ZeilenDef("selbst_amb", "aave", _r(r"^äaveinselbsts?tändigen?ambulatorien"), "ÄAVE", "IST"),
    ZeilenDef("kassen_amb", "aave", _r(r"^äaveinkassenambulatorien"), "ÄAVE", "IST"),
    ZeilenDef("insgesamt", "aave", _r(r"^(ist|plan)?(äave-ä&)?äaveinsgesamt"), "ÄAVE"),
    ZeilenDef("gesamt_nicht_darstellbar", "aave", _r(r"^gesamtnichtdarstellbar"), "ÄAVE"),
    # Wien: «IST ÄAVE gesamt extramural» (VR 92: ist die Zeile insgesamt, korrekturen.csv benennt sie um),
    # Summe inkl. Wahlärzt:innen, Gastpatient:innen-Anteile
    ZeilenDef("insgesamt_als_extramural", "aave", _r(r"^istäavegesamtextramural"), "ÄAVE", "IST"),
    ZeilenDef("extramural_inkl_wahl", "aave", _r(r"^äavesummeextramuralinkl\.?wahlärztinnen"), "ÄAVE"),
    ZeilenDef(
        "gastpat_spitalsambulant", "aave", _r(r"^-?davonfürinländischegastpatient\*?innen\(spitalsambulant"), "ÄAVE"
    ),
    ZeilenDef("gastpat_extramural", "aave", _r(r"^-?davonfürinländischegastpatient\*?innen\(extramural"), "ÄAVE"),
    # VGF und PVE: dieselbe Zeile in IST und PLAN (PLAN: «davon zumindest … in PVE»)
    ZeilenDef("vgf", "aave", _r(r"^-?davon(äave)?invgf"), "ÄAVE"),
    ZeilenDef("pve", "aave", _r(r"^-?davon(zumindest)?(äave)?inpve"), "ÄAVE"),
    # --- IST vertragsärztliche Planstellen ---
    ZeilenDef("planstellen_oegk_svs_bvaeb", "planstellen", _r(r"^(summe)?ögk/svs/bvaeb-?planstellen"), "Stellen"),
    ZeilenDef("planstellen_oegk", "planstellen", _r(r"^ögk-?planstellen"), "Stellen"),
    ZeilenDef("planstellen_svs", "planstellen", _r(r"^svs-?planstellen"), "Stellen"),
    ZeilenDef("planstellen_bvaeb", "planstellen", _r(r"^bvaeb-?planstellen"), "Stellen"),
    # --- IST Ambulatorien-Standorte (Zeile ist zugleich Abschnittskopf) ---
    ZeilenDef("amb_standorte", "standorte", _r(r"^istanzahlambulatorien-?standorte"), "Anzahl"),
    # --- PLAN Sachleistungsstellen ---
    ZeilenDef("slst_gesamt", "slst", _r(r"^plansachleistungsstellen(20\d\d)?gesamt"), "Stellen"),
    ZeilenDef("slst_gemeinsam", "slst", _r(r"^gemeinsamesachleistungsstellen"), "Stellen"),
    ZeilenDef("slst_eva", "slst", _r(r"^-?davonineva"), "Stellen"),
    ZeilenDef("slst_zus_oegk", "slst", _r(r"^zusätzlicheögk-?sachleistungsstellen"), "Stellen"),
    ZeilenDef("slst_zus_svs", "slst", _r(r"^zusätzlichesvs-?sachleistungsstellen"), "Stellen"),
    ZeilenDef("slst_zus_bvaeb", "slst", _r(r"^zusätzlichebvaeb-?sachleistungsstellen"), "Stellen"),
    # «davon maximal als vertragsärztliche Planstellen in %» → <vorige Stellen-Zeile>_max_vaep_prozent
    ZeilenDef("_max_vaep_prozent", "slst", _r(r"^-?davonmaximalalsvertragsärztlicheplanstellen"), "Prozent"),
    # --- Umrechnungsfaktoren (nur Block «aequivalent») ---
    ZeilenDef("umr_spitalsambulant", "umr", _r(r"^umrechnungsfaktorfürärztinnenspitalsambulant"), "Faktor"),
    ZeilenDef("umr_niedergelassen", "umr", _r(r"^regiomed-?umrechnungsfaktor"), "Faktor"),
    ZeilenDef("umr_selbst_amb", "umr", _r(r"^umrechnungsfaktorfürärztinneninselbsts?tändigen"), "Faktor"),
    ZeilenDef("umr_kassen_amb", "umr", _r(r"^umrechnungsfaktorfürärztinneninkassenambulatorien"), "Faktor"),
    ZeilenDef("umr_wahl", "umr", _r(r"^umrechnungsfaktorfürwahlärztinnen"), "Faktor"),
)

# Abschnittsköpfe (Zeilen ohne Werte): Regex → (Abschnitt, Section)
_ABSCHNITT_DEFS: tuple[tuple[re.Pattern[str], str | None, str], ...] = (
    (_r(r"^istäave"), "IST", "aave"),
    (_r(r"^istvertragsärztlicheplanstellen"), "IST", "planstellen"),
    (_r(r"^planäave"), "PLAN", "aave"),
    (_r(r"^plan(sachleistungsstellen|kassenstellen)"), "PLAN", "slst"),
    (_r(r"^umrechnungsfaktoren"), None, "umr"),
)
# Issue-Arten, die keine Werte verfälschen können (nur Info für den Audit-Report)
HINWEIS_ARTEN = frozenset({"stoertext", "isolierte_werte"})

_AEQ_MARKER = _r(r"^sofern(die)?planungsgröße")
_STOP_MARKER = _r(r"^akut-?krankenanstalten")
_FOOTNOTE_LABEL = _r(r"^\(\d+\)|^\*")
_IGNORE_LABEL = _r(r"^(ambulanteärztlicheversorgung|farblegende|legende|\"?rsg-planungsmatrix|gesamtnichtdarstellbar$)")

_FOOTER = _r(r"seite\d+von\d+")
# Wertezeile ohne Label, die weiter als das unter der vorigen Zeile steht, gehört nicht mehr zur
# Matrix (z. B. Seitenzahl «85» am Seitenende, OÖ VR 41) → nicht an eine leere Zeile anhängen.
_MAX_ZEILENABSTAND = 30.0


def _ist_labelbeginn(lab: str) -> bool:
    return bool(
        any(rd.muster.search(lab) for rd in ZEILEN_DEFS)
        or any(pat.search(lab) for pat, _, _ in _ABSCHNITT_DEFS)
        or _AEQ_MARKER.search(lab)
        or _STOP_MARKER.search(lab)
        or _FOOTNOTE_LABEL.search(lab)
        or _IGNORE_LABEL.search(lab)
    )


_FOOTNOTE_TOKEN = re.compile(r"^\(\d+\)$")
_NULL_TOKEN = re.compile(r"^(-|–|n\.v\.?|nv|m\.v\.?|x,?)(\(\d+\))?$", re.I)
# Zusammengeklebte Werte («100,00%71,05%», «-(9)100,00%») in Einzelwerte zerlegen
_GLUED_PART = re.compile(r"-\(\d+\)|\d[\d.]*(?:,\d+)?%|-|n\.v\.")
_NUM_TOKEN = re.compile(r"^\d[\d.]*(,\d+)?%?(\(\d+\))?$")
_YEAR = re.compile(r"(20\d\d)")


@dataclass
class _PdfZeile:
    top: float
    words: list[dict]


@dataclass
class _Gruppe:
    """Logische Matrixzeile: Label (ggf. über mehrere PDF-Zeilen) + max. eine Wertezeile."""

    top: float
    label: str = ""
    values: list[dict] = field(default_factory=list)
    extra: list[dict] = field(default_factory=list)
    """Wörter im Wertebereich, die keine Werte sind (Spaltenköpfe, Störtext)."""


@dataclass
class Ausleseergebnis:
    datensaetze: list[dict]
    issues: list[dict]
    koepfe: list[dict] = field(default_factory=list)
    """Je erkannte Kopfzeile: Seite, Block, Spaltenköpfe wie im PDF und zugeordnete Fachspalten (für die Freigabe)."""


def kompakt(label: str) -> str:
    return re.sub(r"\s+", "", label).lower().replace("selbständig", "selbstständig")


def lese_zahl(raw: str) -> float | None:
    """«1.604,2» → 1604.2 · «99,5%» → 99.5 · «-»/«n.v.»/«x(7)» → None."""
    t = raw.strip()
    if _NULL_TOKEN.match(t):
        return None
    t = re.sub(r"\(\d+\)$", "", t).rstrip("%")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif "." in t and all(len(p) == 3 for p in t.split(".")[1:]):
        t = t.replace(".", "")
    return float(t)


# «-» = nichts geplant/vorhanden → 0 in additiven Zeilen (ÄAVE, Stellen, Anzahl). In %- und
# Faktor-Zeilen bleibt «-» ohne Wert (kein Anteil, weil keine Stellen) – außer unter Stellen > 0
# (`prozent_strich_null`). «n.v.» = nicht verfügbar (Legende Ktn S.99), «x» = Anzahl nicht ausgewiesen,
# schraffiert/leer = nicht vorgesehen → kein Wert.
_STRICH = re.compile(r"^[-–](\(\d+\))?$")
_OHNE_STRICH_NULL = {"Prozent", "Faktor"}
PROZENT_SUFFIX = "_max_vaep_prozent"
"""Zeilen «- davon maximal als vertragsärztliche Planstellen in %» heißen <Stellen-Zeile> + Suffix."""


def zellwert(raw: str, einheit: str) -> float | None:
    """Rohtext → Wert unter Berücksichtigung der Bedeutung von «-» je Einheit."""
    w = lese_zahl(raw)
    if w is None and einheit not in _OHNE_STRICH_NULL and _STRICH.match(raw.strip()):
        return 0.0
    return w


def einheit_laut_beschriftung(einheit: str, beschriftung: str) -> str:
    """«SVE spitalsambulant» (Block «haupt» der SVE-Länder) zählt in Standardversorgungseinheiten, nicht in ÄAVE –
    die Beschriftung sagt es, nicht eine Liste der Länder."""
    return "SVE" if einheit == "ÄAVE" and kompakt(beschriftung).startswith("sve") else einheit


def prozent_strich_null(long: pd.DataFrame) -> pd.DataFrame:
    """«-» in einer %-Zeile, wo darüber Stellen > 0 stehen, heißt 0 % (keine davon vertragsärztlich): Ein Anteil
    muss dort stehen, und «-» ist die Null der Matrix (Burgenland KJP: BL 0 %, VR 11/12 «-»). In der Spalte
    «gesamt» bleibt «-» leer – viele Länder rechnen den Anteil über alle Fächer nicht aus."""
    pct = long["Zeile_ID"].str.endswith(PROZENT_SUFFIX) & long["Wert"].isna() & (long["Fach"] != GESAMT)
    pct &= long["Roh"].astype(str).str.strip().str.match(_STRICH.pattern)
    if not pct.any():
        return long
    schluessel = ["Land", "Ebene", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"]
    stellen = long[long["Wert"].fillna(0) > 0].set_index(schluessel)["Wert"]
    basis = long.loc[pct, schluessel].assign(Zeile_ID=lambda d: d["Zeile_ID"].str.removesuffix(PROZENT_SUFFIX))
    unter_stellen = [k in stellen.index for k in basis.itertuples(index=False, name=None)]
    out = long.copy()
    out.loc[basis.index[unter_stellen], "Wert"] = 0.0
    return out


def _ist_werttoken(text: str) -> bool:
    return bool(_NULL_TOKEN.match(text) or _NUM_TOKEN.match(text))


def _mitte(w: dict) -> float:
    return (w["x0"] + w["x1"]) / 2


def _trenne_geklebt(w: dict) -> list[dict]:
    t = w["text"]
    if _ist_werttoken(t):
        return [w]
    parts = _GLUED_PART.findall(t)
    if len(parts) < 2 or "".join(parts) != t:
        return [w]
    out, pos, width = [], 0, (w["x1"] - w["x0"]) / len(t)
    for part in parts:
        x0 = w["x0"] + pos * width
        out.append({**w, "text": part, "x0": x0, "x1": x0 + len(part) * width})
        pos += len(part)
    return out


def _tausender_zusammenfuegen(words: list[dict]) -> list[dict]:
    """«3» + «.739,0» (pdfplumber trennt am Tausenderpunkt) → «3.739,0»."""
    out: list[dict] = []
    for w in words:
        prev = out[-1] if out else None
        if (
            prev is not None
            and re.match(r"^\.\d{3}(,\d+)?%?$", w["text"])
            and re.match(r"^\d{1,3}$", prev["text"])
            and w["x0"] - prev["x1"] < 3
        ):
            out[-1] = {**prev, "text": prev["text"] + w["text"], "x1": w["x1"]}
        else:
            out.append(w)
    return out


def _pdf_zeilen(words: list[dict], tol: float = 2.5) -> list[_PdfZeile]:
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    out: list[_PdfZeile] = []
    for w in words:
        if out and abs(w["top"] - out[-1].top) <= tol:
            out[-1].words.append(w)
        else:
            out.append(_PdfZeile(w["top"], [w]))
    for line in out:
        line.words.sort(key=lambda w: w["x0"])
        line.words = _tausender_zusammenfuegen([p for w in line.words for p in _trenne_geklebt(w)])
    return out


def _trenne_gesamt(w: dict) -> list[dict]:
    """«SON/IDB(5)gesamt» (Bgld VR 12) → zwei Wörter; x-Grenze anteilig nach Zeichenzahl."""
    t = w["text"]
    if len(t) <= len(GESAMT) or not t.lower().endswith(GESAMT):
        return [w]
    x = w["x0"] + (w["x1"] - w["x0"]) * (len(t) - len(GESAMT)) / len(t)
    return [{**w, "text": t[: -len(GESAMT)], "x1": x}, {**w, "text": t[-len(GESAMT) :], "x0": x}]


def _kopfspalten(line: _PdfZeile) -> list[tuple[str, float, str]] | None:
    """Kopfzeile → (Fachspalte, x-Mitte, Text im PDF) je Spalte; None, wenn die Zeile keine Kopfzeile ist."""
    cols: list[tuple[str, float, str]] = []
    for w in (teil for wort in line.words for teil in _trenne_gesamt(wort)):
        t = w["text"]
        spec = GESAMT if t.lower() == GESAMT else (fachspalte(t) or fachspalte(re.sub(r"\(?\d+\)$", "", t)))
        if spec:
            cols.append((spec, _mitte(w), t))
        elif cols and re.fullmatch(r"\(\d+\)", t):  # «KJP (7)»: Fußnote als eigenes Wort – nur für die Anzeige
            spec, x, text = cols[-1]
            cols[-1] = (spec, x, f"{text} {t}")
    if len(cols) < 10 or cols[-1][0] != GESAMT:
        return None
    return cols


def _unbekannte_koepfe(line: _PdfZeile, cols: list[tuple[str, float, str]]) -> list[str]:
    """Wörter einer Kopfzeile zwischen erster Fachspalte und «gesamt», die keine Fachspalte sind (außer Fußnotenzeichen):
    eine Spalte, die `specs.fachspalte` nicht kennt – ihre Werte hätten sonst keinen Platz."""
    links, rechts = cols[0][1], cols[-1][1]
    bekannt = {round(x, 1) for _, x, _ in cols}
    return [
        w["text"]
        for wort in line.words
        for w in _trenne_gesamt(wort)
        if links < _mitte(w) < rechts
        and round(_mitte(w), 1) not in bekannt
        and not re.fullmatch(r"[\d,()*\s]+", w["text"])  # Fußnotenzeichen, auch zerteilt: «AM (3, 13)»
    ]


class _SeitenParser:
    def __init__(self, *, land: str, ebene: str, region_id: str, region_name: str, pdf: Path):
        self.land, self.ebene, self.region_id, self.region_name = land, ebene, region_id, region_name
        self.pdf = pdf
        self.block = BLOCK_HAUPT
        self.abschnitt: str | None = None
        self.bereich: str | None = None
        self.jahr: int | None = None
        self.cols: list[tuple[str, float, str]] | None = None
        self.last_stellen_row: str | None = None
        self.stopped = False
        self.datensaetze: list[dict] = []
        self.issues: list[dict] = []
        self.koepfe: list[dict] = []

    # --- Hilfen ---
    def _issue(self, seite: int, art: str, detail: str) -> None:
        self.issues.append(
            {
                "Schwere": "hinweis" if art in HINWEIS_ARTEN else "fehler",
                "Land": self.land,
                "Ebene": self.ebene,
                "Region_ID": self.region_id,
                "Seite": seite + 1,
                "Block": self.block,
                "Art": art,
                "Detail": detail,
            }
        )

    def _labelgrenze(self) -> float:
        assert self.cols
        xs = [x for _, x, _ in self.cols]
        spacing = min(b - a for a, b in zip(xs, xs[1:]))
        return xs[0] - spacing / 2

    def _zuordnen(self, values: list[dict], seite: int, label: str) -> dict[str, str]:
        """Werte-Token → Fachspalte über nächstgelegenen Spaltenmittelpunkt."""
        assert self.cols
        xs = [x for _, x, _ in self.cols]
        by_col: dict[int, list[dict]] = {}
        for w in values:
            c = _mitte(w)
            i = min(range(len(xs)), key=lambda k: abs(xs[k] - c))
            left = xs[i] - xs[i - 1] if i > 0 else xs[1] - xs[0]
            right = xs[i + 1] - xs[i] if i + 1 < len(xs) else left
            if abs(xs[i] - c) > 0.5 * min(left, right):
                self._issue(seite, "spalte_unsicher", f"{label}: «{w['text']}» bei x={c:.0f}")
            by_col.setdefault(i, []).append(w)
        out: dict[str, str] = {}
        for i, ws in by_col.items():
            texts = [w["text"] for w in sorted(ws, key=lambda w: w["x0"])]
            raw = texts[0] if len(texts) == 1 else "".join(texts)
            if len(texts) > 1 and not _NUM_TOKEN.match(raw):
                self._issue(seite, "mehrere_werte_in_spalte", f"{label}: {texts} → {self.cols[i][0]}")
            out[self.cols[i][0]] = raw
        return out

    def _spaltenmenge(self, values: list[dict]) -> set[int]:
        assert self.cols
        xs = [x for _, x, _ in self.cols]
        return {min(range(len(xs)), key=lambda k: abs(xs[k] - _mitte(w))) for w in values}

    def _gruppen(self, lines: list[_PdfZeile], seite: int) -> list[_Gruppe]:
        """PDF-Zeilen → logische Matrixzeilen.

        Eine neue Gruppe beginnt bei einem bekannten Label-Anfang (Zeile, Abschnitt, Fußnote,
        Marker). Label-Zeilen ohne bekannten Anfang sind Fortsetzungen umbrochener Labels;
        Wertezeilen ohne Label gehören zur vorigen Gruppe, solange diese noch keine Werte hat.
        """
        assert self.cols
        boundary = self._labelgrenze()
        groups: list[_Gruppe] = []
        prev_top: float | None = None
        for ln in lines:
            text = " ".join(w["text"] for w in ln.words)
            if _FOOTER.search(kompakt(text)):
                continue
            label_words = [w for w in ln.words if _mitte(w) < boundary]
            rest = [w for w in ln.words if _mitte(w) >= boundary]
            vals = [w for w in rest if _ist_werttoken(w["text"])]
            abstand = None if prev_top is None else ln.top - prev_top
            prev_top = ln.top
            if not label_words and abstand is not None and abstand > _MAX_ZEILENABSTAND:
                if vals:
                    self._issue(seite, "isolierte_werte", f"{text[:60]} ({abstand:.0f} pt unter voriger Zeile)")
                continue
            extra = [w for w in rest if not _ist_werttoken(w["text"]) and not _FOOTNOTE_TOKEN.match(w["text"])]
            label = " ".join(w["text"] for w in label_words)
            if not label and len(extra) >= 2 and len(extra) >= len(vals):
                continue  # Fließtext (Fußnote), der in den Wertebereich ragt
            g = groups[-1] if groups else None
            starts = bool(label) and _ist_labelbeginn(kompakt(label))
            # Hochgestellte Werte mit Fußnote («2,0(6)») stehen leicht über der Wertezeile:
            # zusammenführen, wenn sich die belegten Spalten nicht überschneiden.
            disjoint = g is not None and not (self._spaltenmenge(g.values) & self._spaltenmenge(vals))
            if g is not None and not starts and (not (g.values and vals) or disjoint):
                g.label = f"{g.label} {label}".strip()
                g.values.extend(vals)
                g.extra.extend(extra)
            else:
                groups.append(_Gruppe(ln.top, label, list(vals), list(extra)))
        # Hochgestellte Werte über der eigenen Zeile («14(8)») stehen als labellose Gruppe davor:
        # in die folgende Zeile ziehen, wenn nah dran und Spalten disjunkt.
        merged: list[_Gruppe] = []
        for g in groups:
            prev = merged[-1] if merged else None
            if (
                prev is not None
                and not prev.label
                and prev.values
                and g.label
                and g.top - prev.top <= 5
                and not (self._spaltenmenge(prev.values) & self._spaltenmenge(g.values))
            ):
                g.values = prev.values + g.values
                g.extra = prev.extra + g.extra
                merged[-1] = g
            else:
                merged.append(g)
        return merged

    # --- Hauptschleife ---
    def lese_seite(self, page, seite: int) -> None:
        if self.stopped:
            return
        lines = _pdf_zeilen(page.extract_words())
        i = 0
        while i < len(lines):
            # Spaltenköpfe suchen (können mehrfach pro Seite vorkommen)
            cols = _kopfspalten(lines[i])
            if cols:
                self.cols = cols
                for t in _unbekannte_koepfe(lines[i], cols):
                    self._issue(seite, "unbekannte_spalte", f"«{t}» in der Kopfzeile – in specs.py zuordnen")
                hdr_label = kompakt(
                    " ".join(
                        w["text"]
                        for w in lines[i].words
                        if fachspalte(w["text"]) is None and w["text"].lower() != GESAMT
                    )
                )
                if _AEQ_MARKER.search(hdr_label):
                    self.block = BLOCK_AEQ
                self.koepfe.append(
                    {
                        "Land": self.land,
                        "Ebene": self.ebene,
                        "Region_ID": self.region_id,
                        "PDF": self.pdf.name,
                        "Seite": seite + 1,
                        "Block": self.block,
                        "Kopf_PDF": [t for _, _, t in cols],
                        "Faecher": [f for f, _, _ in cols],
                        # wo auf der Seite: die wievielte Kopfzeile, und was direkt darunter steht
                        "Nr_auf_Seite": 1
                        + sum(k["PDF"] == self.pdf.name and k["Seite"] == seite + 1 for k in self.koepfe),
                        "Darunter": " ".join(w["text"] for w in lines[i + 1].words)[:70] if i + 1 < len(lines) else "",
                    }
                )
                i += 1
                # nächste Kopfzeile finden → Bereich bis dahin parsen
                j = i
                while j < len(lines) and not _kopfspalten(lines[j]):
                    j += 1
                for g in self._gruppen(lines[i:j], seite):
                    self._verarbeite_gruppe(g, seite)
                    if self.stopped:
                        return
                i = j
            else:
                n_werte = sum(_ist_werttoken(w["text"]) for w in lines[i].words)
                if n_werte >= 5:
                    text = " ".join(w["text"] for w in lines[i].words)
                    self._issue(seite, "werte_ohne_kopfzeile", text[:80])
                i += 1

    def _verarbeite_gruppe(self, g: _Gruppe, seite: int) -> None:
        lab = kompakt(g.label)
        if _STOP_MARKER.search(lab):
            self.stopped = True
            return
        if _AEQ_MARKER.search(lab):
            self.block = BLOCK_AEQ
            return
        if _FOOTNOTE_LABEL.search(lab) or _IGNORE_LABEL.search(lab):
            return
        if not g.values or (self._finde_zeile(lab) is None and self._ist_abschnittskopf(lab)):
            if not lab:
                return
            non_year = [
                w["text"]
                for w in g.values
                if not re.fullmatch(r"20\d\d", w["text"]) and not _NULL_TOKEN.match(w["text"])
            ]
            if non_year:
                self._issue(seite, "abschnitt_mit_werten", f"{g.label}: {non_year[:5]}")
            for pat, abschnitt, bereich in _ABSCHNITT_DEFS:
                if pat.search(lab):
                    y = _YEAR.search(lab)
                    if bereich == "umr":
                        # «… auf ÄAVE-Äquivalente PLAN 2030» bzw. «IST 2022»: Abschnitt und Jahr stehen oft rechts der
                        # Labelgrenze (Stmk BL S.1: PLAN 2030, VR-Seiten: IST 2022) → ganze Zeile lesen
                        zeile = kompakt(" ".join([g.label, *(w["text"] for w in g.extra + g.values)]))
                        abschnitt = "PLAN" if "plan" in zeile else "IST"
                        y = _YEAR.search(zeile)
                    self.abschnitt, self.bereich = abschnitt, bereich
                    self.jahr = int(y.group(1)) if y else None
                    self.last_stellen_row = None
                    return
            if self._finde_zeile(lab) is None:
                self._issue(seite, "label_ohne_werte", g.label)
            return

        rd = self._finde_zeile(lab)
        if rd is None:
            self._issue(seite, "unbekannte_zeile", g.label or "(ohne Label)")
            zeile_id, einheit = "UNBEKANNT", ""
        else:
            zeile_id, einheit = rd.zeile_id, einheit_laut_beschriftung(rd.einheit, lab)
            if zeile_id == "amb_standorte":
                y = _YEAR.search(lab)
                self.abschnitt, self.bereich = "IST", "standorte"
                self.jahr = int(y.group(1)) if y else self.jahr
            if zeile_id == "_max_vaep_prozent":
                if not self.last_stellen_row:
                    self._issue(seite, "prozentzeile_ohne_bezug", g.label)
                zeile_id = f"{self.last_stellen_row}_max_vaep_prozent"
            elif rd.bereich == "slst" and zeile_id != "slst_eva":
                self.last_stellen_row = zeile_id
        if g.extra:
            self._issue(seite, "stoertext", f"{g.label}: {[w['text'] for w in g.extra]}")

        for fach, raw in self._zuordnen(g.values, seite, g.label).items():
            try:
                wert = zellwert(raw, einheit)
            except ValueError:
                self._issue(seite, "zahl_unlesbar", f"{g.label}: «{raw}» ({fach})")
                wert = None
            self.datensaetze.append(
                {
                    "Land": self.land,
                    "Ebene": self.ebene,
                    "Region_ID": self.region_id,
                    "Region_Name": self.region_name,
                    "Block": self.block,
                    "Abschnitt": self.abschnitt,
                    "Jahr": self.jahr,
                    "Zeile_ID": zeile_id,
                    "Einheit": einheit,
                    "Zeile_PDF_roh": g.label,
                    "Fach": fach,
                    "Wert": wert,
                    "Roh": raw,
                    "PDF": self.pdf.name,
                    "Seite": seite + 1,
                }
            )

    @staticmethod
    def _ist_abschnittskopf(lab: str) -> bool:
        return any(pat.search(lab) for pat, _, _ in _ABSCHNITT_DEFS)

    def _finde_zeile(self, lab: str) -> ZeilenDef | None:
        for rd in ZEILEN_DEFS:
            if rd.bereich == "standorte":
                if rd.muster.search(lab):
                    return rd
                continue
            if self.bereich and rd.bereich != self.bereich:
                continue
            if rd.abschnitt and rd.abschnitt != self.abschnitt:
                continue
            if rd.muster.search(lab):
                return rd
        # Zeilen ohne Label im PLAN-ÄAVE-Abschnitt: zwischen spitalsambulant und insgesamt
        if not lab and self.bereich == "aave" and self.abschnitt == "PLAN":
            return next(r for r in ZEILEN_DEFS if r.zeile_id == "extramural")
        return None


def lese_matrix(
    pdf: Path,
    pages: tuple[int, ...],
    *,
    land: str,
    ebene: str,
    region_id: str,
    region_name: str = "",
) -> Ausleseergebnis:
    """Eine Planungsmatrix (BL oder VR), ggf. über mehrere Seiten fortgesetzt."""
    pp = _SeitenParser(land=land, ebene=ebene, region_id=region_id, region_name=region_name, pdf=pdf)
    with pdfplumber.open(pdf) as doc:
        for seite in pages:
            pp.lese_seite(doc.pages[seite], seite)
    if not pp.datensaetze:
        pp._issue(pages[0], "keine_werte", "Seite ohne lesbare Matrix")
    return Ausleseergebnis(pp.datensaetze, pp.issues, pp.koepfe)


# Seiten mit weniger Zeichen haben keine Textebene (Bild): Bildseiten haben nur Kopf-/Fußzeile
# (Bgld BL 61, Ktn VR 21 58 Zeichen), Matrixseiten mit Text mindestens ~2.600.
TEXT_MIN_ZEICHEN = 500


@cache
def hat_textebene(pdf: Path, seite: int) -> bool:
    """False, wenn die Seite ein Bild ohne Textebene ist (Werte nur manuell erfassbar)."""
    with pdfplumber.open(pdf) as doc:
        return len(doc.pages[seite].chars) >= TEXT_MIN_ZEICHEN


def lese_quelle(src: Rsg2030Quelle) -> Ausleseergebnis:
    """BL-Matrix + alle VR-Matrizen eines Bundeslands. Seiten ohne Textebene werden übersprungen
    (→ `manuell.manuelle_matrizen`)."""
    datensaetze: list[dict] = []
    issues: list[dict] = []
    koepfe: list[dict] = []
    if hat_textebene(src.pdf, src.seite_idx):
        r = lese_matrix(src.pdf, (src.seite_idx,), land=src.land, ebene="BL", region_id=src.land)
        datensaetze += r.datensaetze
        issues += r.issues
        koepfe += r.koepfe
    for vr in src.vr:
        if not hat_textebene(src.pdf, vr.seite_idx):
            continue
        r = lese_matrix(
            src.pdf,
            (vr.seite_idx, *vr.folgeseiten_idx),
            land=src.land,
            ebene="VR",
            region_id=vr.region_id,
            region_name=vr.region_name,
        )
        datensaetze += r.datensaetze
        issues += r.issues
        koepfe += r.koepfe
    return Ausleseergebnis(datensaetze, issues, koepfe)
