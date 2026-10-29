"""Prüfungen auf der RSG-2030-Long-Tabelle (laute Fehler statt stiller Reparatur).

Toleranzen richten sich nach der Genauigkeit im PDF: jeder Summand darf um eine halbe
Einheit seiner letzten Stelle gerundet sein («12,1» → ±0,05; «1.288» → ±0,5).
Bekannte, begründete Abweichungen stehen in `eingaben/2026/bekannte_abweichungen.csv`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rsg2030.ableitungen import ABGELEITET, gewichtetes_mittel
from rsg2030.config import bekannte_abweichungen_csv
from rsg2030.korrekturen import halbe_einheit, rundung_je_zelle
from rsg2030.matrix_extract import PROZENT_SUFFIX
from rsg2030.schema import BLOCK_AEQ, BLOCK_HAUPT, GESAMT, MATRIX

_EPS = 1e-6

# Additive Teilzeilen → Summenzeile (nur wenn alle Zeilen in der Matrix vorkommen)
TEILE: dict[str, tuple[str, ...]] = {
    "IST": ("spitalsambulant", "niedergelassen", "selbst_amb", "kassen_amb"),
    "PLAN": ("spitalsambulant", "extramural"),
}
# Weitere Summenzeilen, die nur manche Länder ausweisen: (Abschnitt, Summenzeile, Teilzeilen, Check).
# Geprüft nur, wo die Summenzeile im PDF steht (nicht, wo `ableitungen.py` sie gebildet hat).
SUMMENZEILEN: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    # extramural = niedergelassen + selbständige Ambulatorien + Kassenambulatorien (alle mit Kassenvertrag); IST: Wien
    ("IST", "extramural", ("niedergelassen", "selbst_amb", "kassen_amb"), "teile_extramural"),
    # Summe extramural inkl. Wahlärzt:innen (Wien)
    ("IST", "extramural_inkl_wahl", ("extramural", "wahl"), "teile_extramural_wahl"),
    # PLAN Sachleistungsstellen gesamt = gemeinsame + zusätzliche je Träger (Wien)
    (
        "PLAN",
        "slst_gesamt",
        ("slst_gemeinsam", "slst_zus_oegk", "slst_zus_svs", "slst_zus_bvaeb"),
        "teile_slst",
    ),
)
# Teilmenge ≤ Obermenge
DAVON: tuple[tuple[str, str], ...] = (
    ("vgf", "insgesamt"),
    ("pve", "vgf"),  # je Abschnitt; PLAN-VGF nur OÖ und Steiermark
    ("pve", "insgesamt"),
    ("slst_eva", "slst_gemeinsam"),
)
# Zeilen, deren Beschriftung nicht sagt, was sie sind: Der Parser hält sie fest, eine Korrektur muss sie zuordnen
# (Wien VR 92: «IST ÄAVE gesamt extramural» ist die Zeile insgesamt). Bleibt eine übrig, ist das eine Abweichung.
ZUORDNEN: dict[str, str] = {
    "insgesamt_als_extramural": "insgesamt (= spitalsambulant + extramural) oder extramural? Summen vergleichen",
}
# Einheiten, die sich nicht summieren lassen
NICHT_ADDITIV = {"Prozent", "Faktor"}
# Zeilen, deren Angabe laut ÖSG optional ist (Tabellenband S.231: Wahlärzt:innen «Angabe optional»;
# im PDF meist grün als «optionale Angabe» markiert). Steht darin in keinem Fach eine Zahl > 0, ist die
# Zeile nicht ausgefüllt – «-»/«0» heißen dort nicht «keine», sondern «nicht angegeben».
OPTIONALE_ZEILEN = ("wahl",)


def _pruefzeile(
    check: str, keys: dict, zeile: str, fach: str, ist: float, soll: float, tol: float, detail: str
) -> dict:
    diff = ist - soll
    return {
        "Check": check,
        **keys,
        "Zeile_ID": zeile,
        "Fach": fach,
        "Wert": round(ist, 4),
        "Soll": round(soll, 4),
        "Differenz": round(diff, 4),
        "Toleranz": round(tol, 4),
        "Status": "ok" if abs(diff) <= tol + _EPS else "abweichung",
        "Detail": detail,
    }


def pruefe_zeilensumme(long: pd.DataFrame) -> list[dict]:
    """Summe der Fachspalten = Spalte «gesamt»."""
    out: list[dict] = []
    df = long[~long["Einheit"].isin(NICHT_ADDITIV) & long["Wert"].notna()]
    for keys, g in df.groupby(MATRIX + ["Zeile_ID"], dropna=False):
        ges = g[g["Fach"] == GESAMT]
        teile = g[g["Fach"] != GESAMT]
        if ges.empty or teile.empty:
            continue
        tol = teile["Rundung"].sum() + ges["Rundung"].iloc[0]
        k = dict(zip(MATRIX, keys[:-1]))
        out.append(
            _pruefzeile(
                "zeilensumme",
                k,
                keys[-1],
                GESAMT,
                teile["Wert"].sum(),
                ges["Wert"].iloc[0],
                tol,
                f"{len(teile)} Fachspalten",
            )
        )
    return out


def pruefe_teile(long: pd.DataFrame) -> list[dict]:
    """IST: spital+nied+selbst+kassen = insgesamt · PLAN: spital+niederg_amb = insgesamt."""
    out: list[dict] = []
    df = long[long["Wert"].notna()]
    for keys, g in df.groupby(MATRIX, dropna=False):
        k = dict(zip(MATRIX, keys))
        teile = TEILE.get(k["Abschnitt"])
        if not teile or "insgesamt" not in set(g["Zeile_ID"]):
            continue
        present = [t for t in teile if t in set(g["Zeile_ID"])]
        if len(present) < 2:
            continue
        piv = g[g["Zeile_ID"].isin(present)]
        ins = g[g["Zeile_ID"] == "insgesamt"].set_index("Fach")
        for fach in sorted(set(piv["Fach"]) | set(ins.index)):
            parts = piv[piv["Fach"] == fach]
            if fach not in ins.index or parts.empty:
                continue
            tol = parts["Rundung"].sum() + ins.at[fach, "Rundung"]
            out.append(
                _pruefzeile(
                    "teile_insgesamt",
                    k,
                    "insgesamt",
                    fach,
                    parts["Wert"].sum(),
                    ins.at[fach, "Wert"],
                    tol,
                    "+".join(present),
                )
            )
    return out


def pruefe_summenzeilen(long: pd.DataFrame) -> list[dict]:
    """Summenzeile laut `SUMMENZEILEN` = Summe ihrer Teilzeilen, je Fach; nur wo alle Teilzeilen in der Matrix stehen
    und die Summenzeile aus dem PDF kommt."""
    out: list[dict] = []
    df = long[long["Wert"].notna()]
    for keys, g in df.groupby(MATRIX, dropna=False):
        k = dict(zip(MATRIX, keys))
        zeilen = set(g["Zeile_ID"])
        for abschnitt, summe, teile, check in SUMMENZEILEN:
            if k["Abschnitt"] != abschnitt or summe not in zeilen or not set(teile) <= zeilen:
                continue
            s = g[(g["Zeile_ID"] == summe) & (g["Quelle"] != "abgeleitet")].set_index("Fach")
            for fach, z in s.iterrows():
                parts = g[g["Zeile_ID"].isin(teile) & (g["Fach"] == fach)]
                if parts.empty:
                    continue
                tol = parts["Rundung"].sum() + z["Rundung"]
                out.append(_pruefzeile(check, k, summe, fach, parts["Wert"].sum(), z["Wert"], tol, "+".join(teile)))
    return out


# SVE-Länder: Teilzeile im Block «haupt» (SVE) × Umrechnungsfaktor = dieselbe Zeile im Block «aequivalent» (ÄAVE-Ä)
FAKTOREN: tuple[tuple[str, str], ...] = (
    ("spitalsambulant", "umr_spitalsambulant"),
    ("niedergelassen", "umr_niedergelassen"),
    ("selbst_amb", "umr_selbst_amb"),
    ("kassen_amb", "umr_kassen_amb"),
    ("wahl", "umr_wahl"),
)


OHNE_EIGENEN_FAKTOR: dict[str, tuple[str, ...]] = {
    "extramural": ("niedergelassen", "selbst_amb", "kassen_amb"),
    "vgf": ("niedergelassen", "selbst_amb", "kassen_amb"),
    "pve": ("niedergelassen", "selbst_amb", "kassen_amb"),
}
"""Zeilen ohne eigene Faktorzeile: Sie fassen Sektoren zusammen; umgerechnet wird nur, wenn keiner davon einen Faktor hat
(dann Faktor 1) – sonst ist die Zeile hier nicht prüfbar."""


def pruefe_faktor(long: pd.DataFrame) -> list[dict]:
    """ÄAVE-Äquivalente = Wert im Block «haupt» × Umrechnungsfaktor seines Sektors, je Fach, in IST und PLAN.

    Tabellenband S.234: Faktoren «je Sektor und je Fachrichtung für die IST-Werte»; «unter Anwendung dieser
    Umrechnungsfaktoren sind für die PLAN-Werte ÄAVE-Äquivalente … auszuweisen». Gerechnet wird mit dem Faktor der
    Matrix selbst (BL bzw. VR), gleich in welchem Abschnitt er steht. Zeilen in ÄAVE (niedergelassen, Ambulatorien …)
    haben keinen Faktor («-»): Faktor 1, also in beiden Blöcken gleich, auch «gesamt». SVE ohne Faktor lassen sich nicht
    umrechnen und bleiben ungeprüft (laut Vorlage (Tabellenband S.239) kein Faktor für RAD, NUK, PMR, PAT, LAB; die ZAE stehen direkt in
    ÄAVE). Ein Wert > 0 in einem Block und keiner im anderen ist ebenso eine Abweichung. Hat jede Region mit Wert ihren
    eigenen Faktor, ist das BL die Summe der umgerechneten Regionen (Kärnten Anhang S.30: «je Versorgungsregion ein
    Umrechnungsfaktor»), und das prüft `vr_summe_gleich_bl`. Mit dem BL-Faktor gerechnet wird das BL dann nur in dem
    Abschnitt, in dem der BL-Faktor steht: Dort ist er das Verhältnis der Landeswerte (Tabellenband S.234: «auf Ebene des
    Bundeslandes … für die IST-Werte»; die Steiermark druckt ihn unter PLAN, METHODIK R6). Toleranz aus der Rundung
    aller drei Werte: ½ULP(haupt)·Faktor + haupt·½ULP(Faktor) + ½ULP(ÄAVE-Ä).
    """
    out: list[dict] = []
    teil_faktor = dict(FAKTOREN)
    # je Land, Abschnitt, Sektor, Fach: Haben alle Regionen mit einem Wert im Block «haupt» einen eigenen Faktor?
    vr = long[long["Ebene"] == "VR"]
    vr_faktor = set(
        map(
            tuple,
            vr.loc[
                vr["Zeile_ID"].str.startswith("umr_") & vr["Wert"].notna(), ["Land", "Region_ID", "Zeile_ID", "Fach"]
            ].values,
        )
    )
    vr_wert = vr[(vr["Block"] == BLOCK_HAUPT) & (vr["Wert"].fillna(0) > 0)]
    ueber_regionen = {
        (land, ab, teil, fach)
        for (land, ab, teil, fach), g in vr_wert[vr_wert["Zeile_ID"].isin(teil_faktor)].groupby(
            ["Land", "Abschnitt", "Zeile_ID", "Fach"]
        )
        if all((land, r, teil_faktor[teil], fach) in vr_faktor for r in g["Region_ID"])
    }
    for (land, ebene, region), m in long[long["Block"].isin([BLOCK_HAUPT, BLOCK_AEQ])].groupby(
        ["Land", "Ebene", "Region_ID"], sort=False
    ):
        a = m[m["Block"] == BLOCK_AEQ]
        if a.empty:
            continue
        h = m[m["Block"] == BLOCK_HAUPT]
        faktor = {}  # Sektor → Fach → (Wert, Rundung), erster Abschnitt mit Wert
        faktor_abschnitt = {}  # Sektor → Fach → Abschnitt, in dem der Faktor steht
        for teil, umr in FAKTOREN:
            f = a[(a["Zeile_ID"] == umr) & a["Wert"].notna()].drop_duplicates("Fach").set_index("Fach")
            faktor[teil] = {fach: (float(r["Wert"]), float(r["Rundung"])) for fach, r in f.iterrows()}
            faktor_abschnitt[teil] = {fach: str(r["Abschnitt"]) for fach, r in f.iterrows()}
        for abschnitt in dict.fromkeys(a["Abschnitt"]):
            ha, aa = h[h["Abschnitt"] == abschnitt], a[a["Abschnitt"] == abschnitt]
            for zeile in [z for z in dict.fromkeys(aa["Zeile_ID"]) if z in set(ha["Zeile_ID"])]:
                sektoren = (zeile,) if zeile in teil_faktor else OHNE_EIGENEN_FAKTOR.get(zeile)
                if sektoren is None:
                    continue
                hz = ha[ha["Zeile_ID"] == zeile].set_index("Fach")
                az = aa[aa["Zeile_ID"] == zeile].set_index("Fach")
                mit_faktor = any(faktor[t] for t in sektoren)
                for fach in dict.fromkeys([*hz.index, *az.index]):
                    if fach == GESAMT and mit_faktor:
                        continue  # «gesamt» umgerechneter Zeilen ist die Summe der umgerechneten Fächer
                    if (
                        ebene == "BL"
                        and (land, abschnitt, zeile, fach) in ueber_regionen
                        and faktor_abschnitt.get(zeile, {}).get(fach) != abschnitt
                    ):
                        continue  # BL = Summe der Regionen, je mit eigenem Faktor; der BL-Faktor gilt in seinem Abschnitt
                    fs = [faktor[t][fach] for t in sektoren if fach in faktor[t]]
                    if len(sektoren) > 1 and fs:
                        continue  # Sammelzeile mit Faktor in einem Sektor: nicht prüfbar
                    zh = hz.loc[fach] if fach in hz.index else None
                    za = az.loc[fach] if fach in az.index else None
                    if not fs and zh is not None and zh["Einheit"] == "SVE":
                        continue  # SVE ohne Faktor: nicht umzurechnen
                    f, f_rund = fs[0] if fs else (1.0, 0.0)
                    if ABGELEITET in {str(z["Quelle"]) for z in (zh, za) if z is not None and "Quelle" in z}:
                        continue  # abgeleitete Zeile: dieselbe Rechnung wie ihre Teile, die hier geprüft werden
                    w_h = float(zh["Wert"]) if zh is not None and pd.notna(zh["Wert"]) else 0.0
                    w_a = float(za["Wert"]) if za is not None and pd.notna(za["Wert"]) else 0.0
                    if w_h == 0 and w_a == 0:
                        continue
                    r_h = float(zh["Rundung"]) if zh is not None else 0.0
                    r_a = float(za["Rundung"]) if za is not None else 0.0
                    leer = za is None or pd.isna(za["Wert"]) or zh is None or pd.isna(zh["Wert"])
                    k = {"Land": land, "Ebene": ebene, "Region_ID": region, "Block": BLOCK_AEQ, "Abschnitt": abschnitt}
                    r = _pruefzeile(
                        "faktor_aequivalente",
                        k,
                        zeile,
                        fach,
                        w_a,
                        w_h * f,
                        r_h * f + w_h * f_rund + r_a,
                        f"haupt {w_h:g} × Faktor {f:g}" + (" (ohne Faktor: 1)" if not fs else ""),
                    )
                    if leer and (w_h > 0) != (w_a > 0):
                        r["Status"] = "abweichung"  # Wert nur in einem Block
                        r["Detail"] += " – nur in einem Block ein Wert"
                    out.append(r)
    return out


def pruefe_leere_summenzelle(long: pd.DataFrame) -> list[dict]:
    """Summenzelle leer, obwohl ihre Teile Werte ≠ 0 haben – Spalte «gesamt» einer Zeile bzw. Zeile
    «insgesamt» eines Fachs (Teilzeilen laut `TEILE`; auch wenn die Zeile «insgesamt» ganz fehlt,
    außer im SVE-Block einer Matrix mit Äquivalente-Block). Teile nur aus «-» (= 0) sind keine Lücke. Eine einzige
    befüllte Teilzeile genügt (Burgenland PLAN: ZAE nur in SON/IDB spitalsambulant, insgesamt «n.v.»)."""
    out: list[dict] = []
    df = long[~long["Einheit"].isin(NICHT_ADDITIV)]
    mit_aeq = set(map(tuple, df.loc[df["Block"] == BLOCK_AEQ, ["Land", "Ebene", "Region_ID"]].values))
    for keys, g in df.groupby(MATRIX, dropna=False):
        k = dict(zip(MATRIX, keys))
        hat = g[g["Wert"].notna()]
        if GESAMT in set(g["Fach"]):
            for zeile, z in hat.groupby("Zeile_ID"):
                teile = z[z["Fach"] != GESAMT]
                if GESAMT not in set(z["Fach"]) and teile["Wert"].abs().sum() > 0:
                    out.append(
                        _leer(k, zeile, GESAMT, teile["Wert"].sum(), f"gesamt leer, {len(teile)} Fachspalten befüllt")
                    )
        teile = hat[hat["Zeile_ID"].isin(TEILE.get(k["Abschnitt"], ()))]
        if k["Block"] == BLOCK_HAUPT and (k["Land"], k["Ebene"], k["Region_ID"]) in mit_aeq:
            continue  # SVE-Planung: insgesamt «nicht darstellbar», steht im Äquivalente-Block
        if "insgesamt" not in set(g["Zeile_ID"]) and teile["Zeile_ID"].nunique() < 2:
            continue
        ins = set(hat.loc[hat["Zeile_ID"] == "insgesamt", "Fach"])
        for fach, t in teile.groupby("Fach"):
            if fach not in ins and t["Wert"].abs().sum() > 0:
                out.append(
                    _leer(
                        k,
                        "insgesamt",
                        fach,
                        t["Wert"].sum(),
                        "insgesamt leer, Teile: " + "+".join(sorted(set(t["Zeile_ID"]))),
                    )
                )
    return out


def pruefe_zuordnen(long: pd.DataFrame) -> list[dict]:
    """Je Matrix und Zeile aus `ZUORDNEN`, die noch da ist, ein Befund – Spalte «gesamt», sonst die erste Fachspalte."""
    out: list[dict] = []
    df = long[long["Zeile_ID"].isin(ZUORDNEN)]
    for (keys, zeile), g in df.groupby([df[MATRIX].apply(tuple, axis=1), "Zeile_ID"]):
        z = g[g["Fach"] == GESAMT] if GESAMT in set(g["Fach"]) else g.head(1)
        r = _pruefzeile(
            "zeile_zuordnen",
            dict(zip(MATRIX, keys)),
            zeile,
            z["Fach"].iloc[0],
            z["Wert"].iloc[0],
            float("nan"),
            0,
            ZUORDNEN[zeile],
        )
        r["Status"] = "abweichung"
        out.append(r)
    return out


def _leer(k: dict, zeile: str, fach: str, summe: float, detail: str) -> dict:
    r = _pruefzeile("leere_summenzelle", k, zeile, fach, summe, float("nan"), 0, detail)
    r["Status"] = "abweichung"
    return r


def pruefe_optional_nicht_ausgewiesen(long: pd.DataFrame) -> list[dict]:
    """Optionale Zeile (`OPTIONALE_ZEILEN`) einer Matrix ohne eine einzige Zahl > 0, aber mit Werten 0
    (aus «-» oder «0»): je Zelle mit Wert ein Befund. Nach der Korrektur `nicht_ausgewiesen` sind die
    Zellen leer und der Befund verschwindet."""
    out: list[dict] = []
    df = long[long["Zeile_ID"].isin(OPTIONALE_ZEILEN)]
    for keys, g in df.groupby([*MATRIX, "Zeile_ID"], dropna=False):
        k = dict(zip(MATRIX, keys[:-1]))
        werte = g[g["Wert"].notna()]
        if len(werte) and not (werte["Wert"] > 0).any():
            for _, z in werte.iterrows():
                r = _pruefzeile(
                    "optional_nicht_ausgewiesen",
                    k,
                    keys[-1],
                    z["Fach"],
                    float(z["Wert"]),
                    float("nan"),
                    0,
                    "optionale Zeile ohne Zahl > 0 (nur «-», «0», «n.v.»): nicht ausgefüllt",
                )
                r["Status"] = "abweichung"
                out.append(r)
    return out


def pruefe_davon(long: pd.DataFrame) -> list[dict]:
    """«davon»-Zeilen dürfen ihre Obermenge nicht überschreiten."""
    out: list[dict] = []
    df = long[long["Wert"].notna()]
    for keys, g in df.groupby(MATRIX, dropna=False):
        k = dict(zip(MATRIX, keys))
        by = {z: s.set_index("Fach") for z, s in g.groupby("Zeile_ID")}
        for sub, sup in DAVON:
            if sub not in by or sup not in by:
                continue
            for fach in by[sub].index.intersection(by[sup].index):
                a, b = by[sub].at[fach, "Wert"], by[sup].at[fach, "Wert"]
                tol = by[sub].at[fach, "Rundung"] + by[sup].at[fach, "Rundung"]
                r = _pruefzeile("davon_le_obermenge", k, sub, fach, a, b, tol, f"{sub} ≤ {sup}")
                r["Status"] = "ok" if a <= b + tol + _EPS else "abweichung"
                out.append(r)
    return out


IN_CH: tuple[str, ...] = ("KJC", "PCH")
"""Fächer, deren ÄAVE in CH enthalten sind: Vorlage (Tabellenband S.239) Fußnote (2) «zugeordnet zu CH»; Tabellenband
S.252: «ÄAVE für PCH sind unter der CH subsummiert und werden nur in Bezug auf die vertragsärztlichen Planstellen der
KV-Träger im IST-Stand ausgewiesen». Die Kennzahlen zählen sie zu CH (`oesg_methodik.faecher.ZUSCHNITT`)."""


def pruefe_in_ch(long: pd.DataFrame) -> list[dict]:
    """KJC und PCH ohne eigene ÄAVE: Steht dort doch ein Wert, ist unklar, ob er in CH schon enthalten ist."""
    out: list[dict] = []
    df = long[long["Einheit"].isin(["ÄAVE", "SVE"]) & long["Fach"].isin(IN_CH) & long["Wert"].notna()]
    for _, r in df.iterrows():
        k = {c: r[c] for c in MATRIX}
        out.append(
            _pruefzeile("kjc_pch_in_ch", k, r["Zeile_ID"], r["Fach"], r["Wert"], 0.0, 0.0, "ÄAVE in CH enthalten")
        )
    return out


def pruefe_prozent(long: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    df = long[(long["Einheit"] == "Prozent") & long["Wert"].notna()]
    for _, r in df.iterrows():
        k = {c: r[c] for c in MATRIX}
        row = _pruefzeile("prozent_0_100", k, r["Zeile_ID"], r["Fach"], r["Wert"], min(max(r["Wert"], 0), 100), 0, "")
        out.append(row)
    return out


# Mindesttoleranz: Stellenzahlen sind im PDF teils gerundet ausgewiesen (Wien: ganzzahlig, intern
# mit Nachkommastellen gerechnet); echte Lesefehler (Spalte verrutscht) liegen weit darüber.
PROZENT_MIN_TOLERANZ = 0.5


def _gewichtet(w: pd.Series, p: pd.Series, w_roh: pd.Series, p_roh: pd.Series, roh: str) -> tuple[float, float]:
    """Gewichtetes Mittel (`ableitungen.gewichtetes_mittel`) und Toleranz: dessen Rundung plus die Rundung des
    Vergleichswerts (`roh`), mindestens `PROZENT_MIN_TOLERANZ`."""
    soll, rundung = gewichtetes_mittel(w, p, w_roh, p_roh)
    return soll, max(halbe_einheit(roh) + rundung, PROZENT_MIN_TOLERANZ)


def pruefe_prozent_gewichtet(long: pd.DataFrame, *, vollstaendig: set[str]) -> list[dict]:
    """BL-% = Mittel der VR-% gewichtet mit den VR-Sachleistungsstellen (je Stellen-Zeile × Fachspalte).

    Geht von den Stellen aus: Zu jeder Stellenzahl > 0 gehört ein % («ist auszuweisen», Tabellenband S.232). Fehlt es
    im BL oder in einer VR, ist die Zelle «nicht_pruefbar» – auch wenn in diesem Fach gar kein % steht. Die Spalte
    «gesamt» rechnet `pruefe_prozent_gesamt` waagrecht nach; senkrecht folgt sie dann aus den Fachspalten.
    """
    out: list[dict] = []
    df = long[long["Land"].isin(vollstaendig)]
    ist_pct = df["Zeile_ID"].str.endswith(PROZENT_SUFFIX)
    gruppe = ["Land", "Block", "Abschnitt", "Zeile_ID", "Fach"]
    pct = {k: g for k, g in df[ist_pct & (df["Fach"] != GESAMT)].groupby(gruppe)}
    mit_pct = set(map(tuple, df.loc[ist_pct, ["Land", "Block", "Abschnitt", "Zeile_ID"]].drop_duplicates().values))
    stellen = df[~ist_pct & (df["Fach"] != GESAMT)]
    for (land, block, abschnitt, basis, fach), st in stellen.groupby(gruppe):
        zeile = basis + PROZENT_SUFFIX
        if (land, block, abschnitt, zeile) not in mit_pct:
            continue  # Zeile ohne %-Zeile darunter
        vr_st = st[st["Ebene"] == "VR"].set_index("Region_ID")
        w = vr_st["Wert"][vr_st["Wert"].fillna(0) > 0]
        bl_hat_stellen = bool((st.loc[st["Ebene"] == "BL", "Wert"].fillna(0) > 0).any())
        if w.empty and not bl_hat_stellen:
            continue
        g = pct.get((land, block, abschnitt, zeile, fach), pd.DataFrame(columns=df.columns))
        bl = g[g["Ebene"] == "BL"]
        b = float(bl["Wert"].iloc[0]) if len(bl) and pd.notna(bl["Wert"].iloc[0]) else float("nan")
        vr = g[g["Ebene"] == "VR"].set_index("Region_ID")
        p = vr["Wert"].reindex(w.index)
        fehlt = (["BL"] if bl_hat_stellen and pd.isna(b) else []) + [f"VR {r}" for r in p.index[p.isna()]]
        k = {"Land": land, "Ebene": "BL", "Region_ID": land, "Block": block, "Abschnitt": abschnitt}
        if fehlt:
            r = _pruefzeile(
                "prozent_gewichtet", k, zeile, fach, 0, 0, 0, f"% fehlt bei Stellen > 0: {', '.join(fehlt)}"
            )
            r["Status"] = "nicht_pruefbar"
            out.append(r)
            continue
        if w.empty or pd.isna(b):
            continue  # Stellen nur im BL: Σ VR = BL meldet das
        soll, tol = _gewichtet(w, p, vr_st["Roh"].reindex(w.index), vr["Roh"].reindex(w.index), bl["Roh"].iloc[0])
        out.append(
            _pruefzeile("prozent_gewichtet", k, zeile, fach, b, soll, tol, f"{len(w)} VR, Σ Stellen {w.sum():g}")
        )
    return out


def pruefe_prozent_gesamt(long: pd.DataFrame) -> list[dict]:
    """Gedrucktes gesamt-% = Mittel der Fach-% derselben Zeile, gewichtet mit den Stellen der Fachspalten – in jeder
    Matrix, die es ausweist. Fehlt ein Fach-% bei Stellen > 0, ist die Zelle «nicht_pruefbar»; ohne Stellen prüft
    `pruefe_prozent_ohne_stellen`. Abgeleitete gesamt-% (`ableitungen.py`) sind dieselbe Rechnung und bleiben außen vor."""
    out: list[dict] = []
    quelle = long["Quelle"].fillna("") if "Quelle" in long else pd.Series("", index=long.index)
    ges = long[
        long["Zeile_ID"].str.endswith(PROZENT_SUFFIX)
        & (long["Fach"] == GESAMT)
        & long["Wert"].notna()
        & (quelle != ABGELEITET)
    ]
    for _, z in ges.iterrows():
        k = {c: z[c] for c in MATRIX}
        matrix = (long[MATRIX] == z[MATRIX].values).all(axis=1)
        zeile = long[matrix & (long["Fach"] != GESAMT)]
        st = zeile[zeile["Zeile_ID"] == z["Zeile_ID"].removesuffix(PROZENT_SUFFIX)].set_index("Fach")
        w = st["Wert"][st["Wert"].fillna(0) > 0]
        if w.empty:
            continue
        pz = zeile[zeile["Zeile_ID"] == z["Zeile_ID"]].set_index("Fach")
        p = pz["Wert"].reindex(w.index)
        b = float(z["Wert"])
        if p.isna().any():
            r = _pruefzeile(
                "prozent_gesamt",
                k,
                z["Zeile_ID"],
                GESAMT,
                b,
                b,
                0,
                f"Fach-% fehlt bei Stellen > 0: {list(p.index[p.isna()])}",
            )
            r["Status"] = "nicht_pruefbar"
            out.append(r)
            continue
        soll, tol = _gewichtet(w, p, st["Roh"].reindex(w.index), pz["Roh"].reindex(w.index), z["Roh"])
        out.append(_pruefzeile("prozent_gesamt", k, z["Zeile_ID"], GESAMT, b, soll, tol, f"{len(w)} Fachspalten"))
    return out


def pruefe_prozent_ohne_stellen(long: pd.DataFrame) -> list[dict]:
    """%-Wert bei 0/keinen Stellen: nur 0 oder 100 (Vorbelegung der Länder) sind plausibel.

    Fängt Werte ab, die nicht in die Zeile gehören (z. B. Seitenzahl als %-Wert, OÖ VR 41–46).
    """
    out: list[dict] = []
    pct = long[long["Zeile_ID"].str.endswith(PROZENT_SUFFIX) & long["Wert"].notna()]
    basis = long.set_index(["Land", "Ebene", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"])["Wert"]
    for _, r in pct.iterrows():
        key = (
            r["Land"],
            r["Ebene"],
            r["Region_ID"],
            r["Block"],
            r["Abschnitt"],
            r["Zeile_ID"].removesuffix(PROZENT_SUFFIX),
            r["Fach"],
        )
        stellen = basis.get(key)
        if stellen is not None and pd.notna(stellen) and stellen != 0:
            continue
        k = {c: r[c] for c in MATRIX}
        row = _pruefzeile(
            "prozent_ohne_stellen", k, r["Zeile_ID"], r["Fach"], r["Wert"], r["Wert"], 0, "Stellen = 0/leer"
        )
        row["Status"] = "ok" if r["Wert"] in (0, 100) else "abweichung"
        out.append(row)
    return out


def pruefe_vr_summe(
    long: pd.DataFrame, *, vollstaendig: set[str], nur_bl_zeilen: set[str] | frozenset[str] = frozenset()
) -> list[dict]:
    """Summe aller VR = BL, je Block × Abschnitt × Zeile × Fach.

    Nur für Bundesländer, deren VR vollständig vorliegen (`vollstaendig`). Prüft auch, ob
    Werte, die auf BL-Ebene stehen, in keiner VR fehlen (und umgekehrt). Für Länder in
    `nur_bl_zeilen` (manuell erfasste BL-Matrix) nur Zeilen, die auf BL-Ebene erfasst sind.
    """
    out: list[dict] = []
    df = long[~long["Einheit"].isin(NICHT_ADDITIV) & long["Land"].isin(vollstaendig)]
    keys = ["Land", "Block", "Abschnitt", "Zeile_ID", "Fach"]
    bl = df[df["Ebene"] == "BL"].set_index(keys)
    vr = df[df["Ebene"] == "VR"]
    if nur_bl_zeilen:
        bl_rows = set(
            zip(
                bl.index.get_level_values("Land"),
                bl.index.get_level_values("Block"),
                bl.index.get_level_values("Abschnitt"),
                bl.index.get_level_values("Zeile_ID"),
            )
        )
        row_key = list(zip(vr["Land"], vr["Block"], vr["Abschnitt"], vr["Zeile_ID"]))
        keep = [k[0] not in nur_bl_zeilen or k in bl_rows for k in row_key]
        vr = vr[keep]
    vr_sum = vr.groupby(keys).agg(
        Wert=("Wert", lambda s: s.sum(min_count=1)),
        Tol=("Rundung", "sum"),
        n=("Wert", "count"),
    )
    for idx in bl.index.union(vr_sum.index):
        b = bl["Wert"].get(idx) if idx in bl.index else None
        v = vr_sum["Wert"].get(idx) if idx in vr_sum.index else None
        b = None if b is None or pd.isna(b) else float(b)
        v = None if v is None or pd.isna(v) else float(v)
        if b is None and v is None:
            continue
        k = dict(zip(keys, idx))
        m = {"Land": k["Land"], "Ebene": "BL", "Region_ID": k["Land"], "Block": k["Block"], "Abschnitt": k["Abschnitt"]}
        tol = (vr_sum["Tol"].get(idx, 0) if idx in vr_sum.index else 0) + (
            bl["Rundung"].get(idx) if idx in bl.index else 0
        )
        if b is None or v is None:
            # Nur auf einer Ebene befüllt: ok, solange der vorhandene Wert 0 ist
            val = b if b is not None else v
            assert val is not None  # eine Ebene ist befüllt (oben geprüft)
            r = _pruefzeile(
                "vr_summe_gleich_bl",
                m,
                k["Zeile_ID"],
                k["Fach"],
                v or 0.0,
                b or 0.0,
                tol,
                "nur BL" if v is None else "nur VR",
            )
            r["Status"] = "ok" if abs(val) <= tol + _EPS else "abweichung"
            out.append(r)
            continue
        out.append(
            _pruefzeile(
                "vr_summe_gleich_bl", m, k["Zeile_ID"], k["Fach"], v, b, tol, f"{int(vr_sum['n'].get(idx, 0))} VR"
            )
        )
    return out


def lade_bekannte_abweichungen(path: Path | None = None) -> pd.DataFrame:
    path = path or bekannte_abweichungen_csv()
    if not path.is_file():
        return pd.DataFrame(columns=["Check", "Land", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach", "Grund"])
    return pd.read_csv(path, dtype=str).fillna("*")


OFFEN = ("abweichung", "nicht_pruefbar")
"""Status, die eine Begründung brauchen: Ohne Eintrag in bekannte_abweichungen.csv ist der Lauf nicht freigegeben –
eine Zelle, die keine Prüfung nachrechnen kann, so wenig wie eine, die nicht aufgeht."""


def markiere_bekannte(checks: pd.DataFrame, known: pd.DataFrame) -> pd.DataFrame:
    """Markiert Abweichungen und nicht prüfbare Zellen, die in bekannte_abweichungen.csv begründet sind
    (Status → «bekannt»)."""
    checks = checks.copy()
    checks["Grund"] = ""
    cols = ["Check", "Land", "Region_ID", "Block", "Abschnitt", "Zeile_ID", "Fach"]
    for _, k in known.iterrows():
        sel = checks["Status"].isin(OFFEN)
        for c in cols:
            if k[c] != "*":
                sel &= checks[c].astype(str) == k[c]
        checks.loc[sel, ["Status", "Grund"]] = ["bekannt", k["Grund"]]
    return checks


def pruefe_alle(
    long: pd.DataFrame, *, vr_vollstaendig: set[str], nur_bl_zeilen: set[str] | frozenset[str] = frozenset()
) -> pd.DataFrame:
    if "Rundung" not in long:
        long = long.assign(Rundung=rundung_je_zelle(long))
    rows = (
        pruefe_zeilensumme(long)
        + pruefe_teile(long)
        + pruefe_summenzeilen(long)
        + pruefe_faktor(long)
        + pruefe_leere_summenzelle(long)
        + pruefe_zuordnen(long)
        + pruefe_davon(long)
        + pruefe_in_ch(long)
        + pruefe_prozent(long)
        + pruefe_vr_summe(long, vollstaendig=vr_vollstaendig, nur_bl_zeilen=nur_bl_zeilen)
        + pruefe_prozent_gewichtet(long, vollstaendig=vr_vollstaendig)
        + pruefe_prozent_gesamt(long)
        + pruefe_prozent_ohne_stellen(long)
        + pruefe_optional_nicht_ausgewiesen(long)
    )
    return markiere_bekannte(pd.DataFrame(rows), lade_bekannte_abweichungen())


def pruefe_vollstaendigkeit(long: pd.DataFrame, sources, oesg: pd.DataFrame) -> list[str]:
    """Register (seiten.csv) = alle Versorgungsregionen laut ÖSG, je Bundesland; jede VR hat Werte.

    Zuordnung über die Bundeslandnummer der ÖSG-Liste (VR-Nummern 11–93: erste Ziffer = BL-Nr.).
    """
    probleme: list[str] = []
    soll = oesg.groupby("BL_Nr")["VR"].apply(lambda s: {str(v) for v in s}).to_dict()
    namen = oesg.drop_duplicates("BL_Nr").set_index("BL_Nr")["Bundesland"].to_dict()
    gesehen: set[int] = set()
    mit_werten = set(
        zip(long.loc[long["Wert"].notna(), "Land"], long.loc[long["Wert"].notna(), "Region_ID"].astype(str))
    )
    for src in sources:
        ist = {vr.region_id for vr in src.vr}
        bl_nr = {int(v[0]) for v in ist}
        if len(bl_nr) != 1:
            probleme.append(f"{src.land}: VR-Nummern gehören zu mehreren Bundesländern: {sorted(ist)}")
            continue
        (nr,) = bl_nr
        gesehen.add(nr)
        if ist != soll.get(nr, set()):
            probleme.append(f"{src.land}: VR laut seiten.csv {sorted(ist)} ≠ laut ÖSG {sorted(soll.get(nr, set()))}")
        for rid in sorted(ist):
            if (src.land, rid) not in mit_werten:
                probleme.append(f"{src.land} VR {rid}: keine Werte ausgelesen")
        if (src.land, src.land) not in mit_werten:
            probleme.append(f"{src.land} BL: keine Werte ausgelesen")
    for nr in sorted(set(soll) - gesehen):
        probleme.append(f"{namen[nr]}: fehlt in seiten.csv (VR laut ÖSG {sorted(soll[nr])})")
    return probleme
