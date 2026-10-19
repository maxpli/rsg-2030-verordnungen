"""Zweitlesung: ein zweites, unabhängiges Verfahren liest dieselben Seiten; Vergleich Zelle für Zelle (PRUEFUNG.md, Ebene 3).

Die Lesung A ist der Parser (Textseiten) bzw. die Abschrift (Bildseiten). Die Lesung B entsteht aus dem **Bild** der Seite
(`scripts/zweitlesung_ki.py`), ohne die Werte von A zu kennen, und liegt je Matrix als Datei im Repository:

    eingaben/<Stand>/zweitlesung/<land>_<bl|vrNN>.tsv          z. B. kaernten_vr21.tsv

    # Kommentarzeilen: Herkunft (Verfahren, Modell, Datum, PDF, Seite, Prüfsumme des Bildes)
    #Abschnitt<TAB>IST ÄAVE 2022                  Überschrift wie gedruckt (auch «sofern Planungsgröße …»,
                                                  «Umrechnungsfaktoren … PLAN 2030»)
    #Kopf<TAB>AM(4)<TAB>AN<TAB>…<TAB>gesamt        Spaltenköpfe wie gedruckt
    ÄAVE spitalsambulant<TAB>-<TAB>…               Zeilenbeschriftung und Werte wie gedruckt; leer = leere/schraffierte Zelle

Spaltenköpfe und Zeilenbeschriftungen werden über dieselben Zuordnungen auf Fachspalte und `Zeile_ID` abgebildet, die in
der Freigabe (Blätter «Spalten», «Zeilen») von Hand bestätigt sind – unabhängig ist die **Lesung**: welcher Wert unter
welchem Kopf und neben welcher Beschriftung steht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from rsg2030.config import eingaben_dir
from rsg2030.matrix_extract import _ABSCHNITT_DEFS, _AEQ_MARKER, ZEILEN_DEFS, kompakt
from rsg2030.schema import BLOCK_AEQ, BLOCK_HAUPT, FACHSPALTEN, GESAMT
from rsg2030.specs import fachspalte

ORDNER = "zweitlesung"
SCHLUESSEL = ["Land", "Ebene", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"]
PROZENT = re.compile(r"^-?davonmaximalalsvertragsarztlicheplanstellen")  # auf _norm (ohne Umlaute)
OHNE_WERTE = {"gesamt_nicht_darstellbar"}
"""Zeilen, die im PDF stehen, aber bewusst nicht in den Datensatz kommen (nur «-» bzw. «n.v.»)."""


_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def dateiname(land: str, ebene: str, region_id: str) -> str:
    """«burgenland_bl.tsv», «kaernten_vr21.tsv», «ooe_vr41.tsv» – ein Name je Matrix, Kleinbuchstaben ohne Umlaute."""
    return f"{land.lower().translate(_UMLAUT)}_{'bl' if ebene == 'BL' else 'vr' + region_id}.tsv"


def ordner() -> Path:
    return eingaben_dir() / ORDNER


def _norm(label: str) -> str:
    """Beschriftung ohne Fußnotenzeichen, Jahr und Leerraum – so vergleichbar über Matrizen und Lesungen."""
    t = re.sub(r"[\u2010-\u2015\u2212]", "-", label)  # Gedankenstrich, Minuszeichen → Bindestrich
    t = re.sub(r"\(\d+\)|\*(?=\s|\)|$)", "", t)
    t = re.sub(r"\b20\d\d\b", "", t)
    # Umlaute weglassen: dieselbe Beschriftung, ob «ÄAVE» oder «AAVE» gelesen (Zuordnung ist trotzdem eindeutig)
    return kompakt(t).strip("-").translate(str.maketrans("äöü", "aou"))


@dataclass
class Lesung:
    """Eine Zweitlesung, aufgelöst auf Zellen."""

    kopf: list[str] = field(default_factory=list)
    """Kommentarzeilen (Herkunft)."""
    zellen: pd.DataFrame = field(default_factory=pd.DataFrame)
    """Block, Abschnitt, Zeile (wie gedruckt), Zeile_ID, Kopf (wie gedruckt), Fach, Roh."""
    unbekannt: list[str] = field(default_factory=list)
    """Zeilen oder Köpfe, die sich keiner Zeile_ID bzw. Fachspalte zuordnen ließen."""
    unvollstaendig: set[tuple[str, str, str]] = field(default_factory=set)
    """(Block, Abschnitt, Zeile_ID) mit weniger Werten als Spalten: Zuordnung zur Spalte unsicher, nicht verglichen."""


def zuordnung_zeilen(raw: pd.DataFrame) -> dict[tuple[str, str, str], str]:
    """(Block, Abschnitt, Beschriftung normalisiert) → Zeile_ID, aus dem, was der Parser zugeordnet hat (in der Freigabe,
    Blatt «Zeilen», bestätigt). %-Zeilen ausgenommen – deren Zeile_ID hängt an der vorigen Stellen-Zeile."""
    r = raw[raw["Quelle"].fillna("PDF").eq("PDF") & ~raw["Zeile_ID"].str.endswith("_max_vaep_prozent")]
    paare = r[["Block", "Abschnitt", "Zeile_PDF_roh", "Zeile_ID"]].drop_duplicates()
    return {(b, a, _norm(str(t))): z for b, a, t, z in paare.itertuples(index=False) if _norm(str(t))}


def _zeile_per_muster(norm: str, abschnitt: str | None) -> str | None:
    for rd in ZEILEN_DEFS:
        if rd.abschnitt and rd.abschnitt != abschnitt:
            continue
        if rd.muster.search(norm):
            return rd.zeile_id
    return None


def _verkuerzt(label: str, block: str, abschnitt: str, zuordnung: dict[tuple[str, str, str], str]) -> str | None:
    """Verkürzt gelesene Beschriftung («Umrechnungsfaktor für spitalsambulant» statt «… für ÄrztInnen spitalsambulant»):
    die Zeile derselben Gruppe, deren Beschriftung alle Wörter in derselben Reihenfolge enthält – nur wenn es genau eine
    gibt. Eine falsche Zuordnung fiele als Abweichungen auf; sie kann keinen Fehler verdecken."""
    woerter = [_norm(w) for w in re.findall(r"\w+", label) if _norm(w)]
    if len(woerter) < 2:
        return None

    def enthaelt(text: str) -> bool:
        pos = 0
        for w in woerter:
            pos = text.find(w, pos)
            if pos < 0:
                return False
            pos += len(w)
        return True

    treffer = {z for (b, a, t), z in zuordnung.items() if b == block and a == abschnitt and enthaelt(t)}
    return treffer.pop() if len(treffer) == 1 else None


def _faecher(kopf: list[str]) -> tuple[list[str | None], list[str]]:
    """Spaltenköpfe → Fachspalten. Ein unlesbarer Kopf zwischen zwei erkannten wird aus der Reihenfolge der Fachspalten
    erschlossen, wenn genau eine dazwischen liegt (z. B. «KJU» zwischen AN und KJC(2) → KIJU) – mit Hinweis."""

    def erkenne(k: str) -> str | None:
        if k.strip().lower() == GESAMT:
            return GESAMT
        for kandidat in (k, k.replace("I", "J")):  # I/J verwechselt: «KIC(1)» → KJC, «KIP(7)» → KJP
            f = fachspalte(kandidat) or fachspalte(re.sub(r"\(?\d+\)$", "", kandidat))
            if f:
                return f
        return None

    roh = [erkenne(k) for k in kopf]
    reihe = [*FACHSPALTEN, GESAMT]
    hinweise: list[str] = []
    out = list(roh)
    for i, f in enumerate(roh):
        if f is not None:
            continue
        vor = roh[i - 1] if i > 0 else None
        nach = roh[i + 1] if i + 1 < len(roh) else None
        if vor in reihe and nach in reihe and reihe.index(nach) - reihe.index(vor) == 2:
            out[i] = reihe[reihe.index(vor) + 1]
            hinweise.append(f"Spaltenkopf «{kopf[i]}» als {out[i]} gelesen (zwischen {vor} und {nach})")
        else:
            hinweise.append(f"Spaltenkopf «{kopf[i]}» unbekannt")
    return out, hinweise


def lese(pfad: Path, zuordnung: dict[tuple[str, str, str], str]) -> Lesung:
    les = Lesung()
    block, abschnitt, kopf = BLOCK_HAUPT, None, None
    faecher: list[str | None] = []
    letzte_stellen: str | None = None
    zellen: list[dict] = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        if zeile.startswith("#Abschnitt"):
            titel = zeile.split("\t", 1)[1] if "\t" in zeile else ""
            k = kompakt(titel)
            if _AEQ_MARKER.search(k):
                block = BLOCK_AEQ
            for muster, ab, bereich in _ABSCHNITT_DEFS:
                if muster.search(k):
                    abschnitt = ("PLAN" if "plan" in k else "IST") if bereich == "umr" else ab
                    letzte_stellen = None
            continue
        if zeile.startswith("#Kopf"):
            kopf = zeile.split("\t")[1:]
            faecher, hinweise = _faecher(kopf)
            les.unbekannt += hinweise
            continue
        if zeile.startswith("#"):
            les.kopf.append(zeile)
            continue
        if kopf is None:
            les.unbekannt.append(f"Wertezeile vor dem ersten Kopf: {zeile[:60]}")
            continue
        teile = zeile.split("\t")
        label, werte = teile[0], teile[1:]
        if not any(w.strip() for w in werte):  # Leerzeile (z. B. leere Wahlärzt:innen-Zeile ohne Beschriftung)
            continue
        norm = _norm(label)
        if norm.startswith("istanzahlambulatorien") or norm.startswith("anzahlambulatorien"):
            abschnitt = "IST"
        if PROZENT.search(norm):
            zeile_id = f"{letzte_stellen}_max_vaep_prozent" if letzte_stellen else None
        else:
            zeile_id = zuordnung.get((block, abschnitt or "", norm)) or _zeile_per_muster(
                kompakt(re.sub(r"[\u2010-\u2015\u2212]", "-", label)), abschnitt
            )
        if zeile_id is None:
            zeile_id = _verkuerzt(label, block, abschnitt or "", zuordnung)
            if zeile_id is not None:
                les.unbekannt.append(
                    f"{block} {abschnitt}: Zeile «{label}» verkürzt gelesen, als {zeile_id} verglichen"
                )
        if zeile_id is None:
            les.unbekannt.append(f"{block} {abschnitt}: Zeile «{label}»")
            continue
        if zeile_id.startswith(("slst_", "planstellen_")) and zeile_id != "slst_eva":
            letzte_stellen = zeile_id
        if zeile_id in OHNE_WERTE:
            continue
        if len(werte) < len(kopf):  # fehlende Zelle irgendwo in der Zeile: Werte würden in falsche Spalten rutschen
            les.unvollstaendig.add((block, abschnitt or "", zeile_id))
            les.unbekannt.append(f"{block} {abschnitt}: «{label}» unvollständig ({len(werte)} von {len(kopf)} Werten)")
            continue
        for k_text, fach, roh in zip(kopf, faecher, werte):
            if fach is None:
                continue
            zellen.append(
                dict(
                    Block=block,
                    Abschnitt=abschnitt,
                    Zeile=label,
                    Zeile_ID=zeile_id,
                    Kopf=k_text,
                    Fach=fach,
                    Roh=roh.strip(),
                )
            )
    les.zellen = pd.DataFrame(zellen, columns=["Block", "Abschnitt", "Zeile", "Zeile_ID", "Kopf", "Fach", "Roh"])
    les.unbekannt = list(dict.fromkeys(les.unbekannt))
    return les


@dataclass
class Vergleich:
    matrizen: int = 0
    """Matrizen mit Zweitlesung."""
    fehlend: list[str] = field(default_factory=list)
    """Matrizen ohne Zweitlesung (Dateiname)."""
    verglichen: int = 0
    abweichungen: pd.DataFrame = field(default_factory=pd.DataFrame)
    """Zellen, in denen A und B verschieden sind (inkl. Zelle nur in A bzw. nur in B mit Text)."""
    nicht_verglichen: pd.DataFrame = field(default_factory=pd.DataFrame)
    """Zellen mit Text in A, deren Zeile B unvollständig gelesen hat (Spalte unsicher) – entscheidet ein Mensch."""
    unbekannt: list[str] = field(default_factory=list)


def vergleiche(
    raw: pd.DataFrame, matrizen: list[tuple[str, str, str, str, int]], pfad: Path | None = None
) -> Vergleich:
    """Lesung A (`raw`: Parser + Abschrift, vor Korrekturen) gegen Lesung B, je Matrix (Land, Ebene, Region_ID, PDF, Seite).

    Verglichen werden die Texte wie gedruckt (`roh_gleich`: «2,0» = «2,00», sonst «-» ≠ leer ≠ «n.v.»)."""
    from rsg2030.freigabe import roh_gleich
    from rsg2030.manuell import ManuelleMatrix, lese_manuell

    pfad = pfad or ordner()
    zuordnung = zuordnung_zeilen(raw)
    erg = Vergleich()
    teile: list[pd.DataFrame] = []
    unvollst: list[pd.DataFrame] = []
    for land, ebene, region_id, pdf, seite in matrizen:
        datei = pfad / dateiname(land, ebene, region_id)
        if not datei.is_file():
            erg.fehlend.append(datei.name)
            continue
        erg.matrizen += 1
        eigene = dict(zuordnung)
        blatt = lese_manuell(
            ManuelleMatrix(f"{land} {'BL' if ebene == 'BL' else 'VR' + region_id}", "", "", "", "", "", 0)
        )
        if blatt is not None:  # Bildseite: Beschriftungen wie in der Abschrift
            for b, ab, t, z in blatt[["Block", "Abschnitt", "Zeile", "Zeile_ID"]].itertuples(index=False):
                if not str(z).endswith("_max_vaep_prozent"):
                    eigene[(b, ab, _norm(str(t)))] = z
        les = lese(datei, eigene)
        erg.unbekannt += [f"{datei.name}: {u}" for u in les.unbekannt]
        b = les.zellen.drop_duplicates(["Block", "Abschnitt", "Zeile_ID", "Fach"])
        a = raw[(raw["Land"] == land) & (raw["Ebene"] == ebene) & (raw["Region_ID"].astype(str) == str(region_id))]
        a = a[["Block", "Abschnitt", "Zeile_ID", "Fach", "Roh", "Zeile_PDF_roh", "Seite"]]
        ohne_b = pd.Series(
            [
                (bl, ab, z) in les.unvollstaendig
                for bl, ab, z in a[["Block", "Abschnitt", "Zeile_ID"]].itertuples(index=False)
            ],
            index=a.index,
            dtype=bool,
        )
        nv = a[ohne_b & a["Roh"].fillna("").astype(str).str.strip().ne("")].rename(columns={"Roh": "Roh_A"})
        if len(nv):
            nv = nv.assign(Roh_B="", Zeile="", Land=land, Ebene=ebene, Region_ID=region_id, PDF=pdf)
            nv["Seite"] = nv["Seite"].fillna(seite)
            unvollst.append(nv)
        a = a[~ohne_b]
        m = a.merge(b, on=["Block", "Abschnitt", "Zeile_ID", "Fach"], how="outer", suffixes=("_A", "_B"))
        m["Roh_A"] = m["Roh_A"].fillna("").astype(str)
        m["Roh_B"] = m["Roh_B"].fillna("").astype(str)
        m = m[(m["Roh_A"].str.strip() != "") | (m["Roh_B"].str.strip() != "")]
        erg.verglichen += len(m)
        gleich = [x.strip() == y.strip() or roh_gleich(x, y) for x, y in zip(m["Roh_A"], m["Roh_B"])]
        d = m[~pd.Series(gleich, index=m.index)].copy()
        d.insert(0, "Region_ID", region_id)
        d.insert(0, "Ebene", ebene)
        d.insert(0, "Land", land)
        d["PDF"], d["Seite"] = pdf, d["Seite"].fillna(seite)
        teile.append(d)
    erg.abweichungen = pd.concat(teile, ignore_index=True) if teile else pd.DataFrame()
    erg.nicht_verglichen = pd.concat(unvollst, ignore_index=True) if unvollst else pd.DataFrame()
    return erg


def matrizen_aus(quellen) -> list[tuple[str, str, str, str, int]]:
    """(Land, Ebene, Region_ID, PDF, Seite 1-basiert) je Matrix laut Seitenregister."""
    out: list[tuple[str, str, str, str, int]] = []
    for q in quellen:
        out.append((q.land, "BL", q.land, q.pdf.name, q.seite_idx + 1))
        out += [(q.land, "VR", vr.region_id, q.pdf.name, vr.seite_idx + 1) for vr in q.vr]
    return out
