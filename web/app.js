/* Webseite zur Tabelle Versorgungsdichte. Zeigt nur, was in data.json steht; data.json erzeugt
   «python -m rsg2030 web» aus RSG_2030_Versorgungsdichte.csv. Aufbau und Regeln: docs/WEB.md. */
"use strict";

fetch("data.json")
  .then((r) => { if (!r.ok) throw new Error(`data.json: HTTP ${r.status}`); return r.json(); })
  .then(start)
  .catch((e) => {
    document.querySelector(".wrap").insertAdjacentHTML("afterbegin",
      `<p class="notice"><b>Die Daten konnten nicht geladen werden.</b> ${String(e.message || e)}</p>`);
  });

function start(D) {
const M = D.meta;
const fachInfo = Object.fromEntries(D.faecher.map((f) => [f.id, f]));
const regionById = Object.fromEntries(D.regionen.map((r) => [r.id, r]));
const DATEN_MD = `${M.repo}/blob/${M.version}/docs/DATEN.md#fallstricke`;

const nf = (d) => new Intl.NumberFormat("de-AT", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmt = (x, d = 1) => x == null ? "–" : nf(d).format(x).replace("-", "−");
const sgn = (x, d = 1) => x == null ? "–" : (x > 0 ? "+" : "") + fmt(x, d);
const vdDig = (f) => (f.max < 2 ? 2 : 1);
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
const trunc = (t, n) => t.length > n ? t.slice(0, n - 1) + "…" : t;

const STANDARD = { VR: "41", BL: "OÖ" };
const S = { abschnitt: "PLAN", ebene: "VR", fach: "IM", region: STANDARD.VR, hatch: true };
try { Object.assign(S, JSON.parse(localStorage.getItem("rsg-vd") || "{}")); } catch (e) { /* ohne gespeicherte Ansicht */ }
const save = () => { try { localStorage.setItem("rsg-vd", JSON.stringify(S)); } catch (e) { /* egal */ } };

const get = (rid, ab, f) => {
  const w = D.werte[`${rid}|${ab}|${f}`];
  return w ? { vd: w[0], aave: w[1], bev: w[2], jahr: w[3], lage: w[4], pos: w[5], abst: w[6], zuschnitt: w[7] } : null;
};
/* Farbstufe aus der Position: Abstand zur Grenze in Intervallbreiten, Stufen bis ¼, bis ½, darüber (docs/WEB.md) */
const klasse = (w) => {
  if (!w) return "na";
  if (w.lage === "im") return "in";
  const d = w.lage === "unter" ? -w.pos : w.pos - 1;
  const s = d < .25 ? 1 : d < .5 ? 2 : 3;
  return (w.lage === "unter" ? "u" : "o") + s;
};
/* Randfall: weniger als 1 ÄAVE vom Intervall entfernt (Fallstrick 6) */
const klein = (w) => w && w.lage !== "im" && Math.abs(w.abst) < 1;
const regionen = () => D.regionen.filter((r) => r.ebene === S.ebene);
const titel = (r) => r.ebene === "VR" ? r.name : r.land_name;
const lageText = (w) => !w ? "kein Wert" : w.lage === "im" ? "im Intervall" : w.lage === "unter" ? "unter VDmin" : "über VDmax";
const pill = (w) => `<span class="pill"><i class="k-${klasse(w)}"></i>${lageText(w)}</span>`;

/* Kopf und Fußzeile: Datenstand und Stand der Seite */
document.getElementById("eyebrow").textContent = `RSG-2030-Verordnungen · Release ${M.version}`;
document.getElementById("footer").innerHTML = `
  <div>Quelle: <span class="nb">${esc(M.datei)}</span>, <a href="${M.repo}/releases/tag/${M.version}" target="_blank" rel="noopener">Release ${esc(M.version)}</a> von <a href="${M.repo}" target="_blank" rel="noopener">${esc(M.repo.replace("https://github.com/", ""))}</a> · SHA-256 <span class="num" style="word-break:break-all">${esc(M.sha256)}</span></div>
  <div>Stand der Seite: <a href="${M.repo}/commit/${M.commit}" target="_blank" rel="noopener" class="num">${esc(M.commit.slice(0, 7))}</a> · Alle Vorbehalte: <a href="${DATEN_MD}" target="_blank" rel="noopener">docs/DATEN.md, Fallstricke</a> · Daten CC BY 4.0</div>`;

/* Tooltip */
const tip = document.getElementById("tip");
function showTip(ev, html) {
  /* nur bei Maus: bei Touch gibt es kein «Verlassen», die Box bliebe stehen; dort zeigt die Detailspalte dasselbe */
  if (ev.pointerType !== "mouse") return hideTip();
  tip.innerHTML = html; tip.hidden = false;
  const r = tip.getBoundingClientRect(), pad = 14;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - pad;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - pad;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
}
function hideTip() { tip.hidden = true; }
addEventListener("scroll", hideTip, { passive: true, capture: true });
function tipHtml(r, f, ab) {
  const w = get(r.id, ab, f), fi = fachInfo[f];
  const head = `<b>${r.ebene === "VR" ? r.id + " " : ""}${esc(titel(r))}</b><br><span class="t2">${esc(fi.name)} · ${ab === "IST" ? "IST " + (w ? w.jahr : "") : "PLAN 2030"}</span>`;
  if (!w) return head + "<br>kein Wert";
  const dg = vdDig(fi);
  return `${head}<br>VD <span class="num">${fmt(w.vd, dg)}</span> · Soll <span class="num">${fmt(fi.min, dg)}–${fmt(fi.max, dg)}</span><br>${lageText(w)} · ÄAVE-Abstand <span class="num">${sgn(w.abst)}</span>`;
}

/* Bedienung */
const selF = document.getElementById("sel-fach");
selF.innerHTML = D.faecher.map((f) => `<option value="${f.id}">${f.id} · ${esc(f.name)}</option>`).join("");
function bindSeg(id, key) {
  document.querySelectorAll(`#${id} button`).forEach((b) => b.addEventListener("click", () => { S[key] = b.dataset.v; render(); }));
}
bindSeg("seg-abschnitt", "abschnitt"); bindSeg("seg-ebene", "ebene");
selF.addEventListener("change", () => { S.fach = selF.value; render(); });
document.getElementById("chk-hatch").addEventListener("change", (e) => { S.hatch = e.target.checked; render(); });

/* Wenn die Detailspalte unter der Matrix steht (schmale Ansicht), nach der Auswahl dorthin scrollen;
   der Knopf in der Detailspalte führt zurück zur angetippten Stelle (src = Selektor des gewählten Elements) */
const stacked = () => matchMedia("(max-width: 1020px)").matches;
const motion = () => matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
let backTo = null;
function pick(rid, f, src) {
  const jump = src && rid && stacked();
  if (jump) backTo = src;
  if (rid) S.region = rid;
  if (f) S.fach = f;
  render();
  if (!jump) return;
  const det = document.getElementById("detail"), tb = document.querySelector(".toolbar");
  det.style.scrollMarginTop = (getComputedStyle(tb).position === "sticky" ? tb.offsetHeight : 0) + 12 + "px";
  det.scrollIntoView({ behavior: motion(), block: "start" });
}
document.getElementById("detail").addEventListener("click", (e) => {
  if (!e.target.closest("#d-back") || !backTo) return;
  const el = document.querySelector(backTo);
  if (el) el.scrollIntoView({ behavior: motion(), block: "center" });
});

/* Matrix und Anteilsbalken */
function renderMatrix() {
  const regs = regionen(), F = D.faecher;
  let h = `<thead><tr><th></th>${F.map((f) => `<th scope="col" data-f="${f.id}" class="${f.teil_von ? "part" : ""} ${f.id === S.fach ? "sel" : ""}" title="${esc(f.name)}${f.teil_von ? " – Teil von " + f.teil_von : ""}">${f.id}</th>`).join("")}</tr></thead><tbody>`;
  let land = null;
  for (const r of regs) {
    if (S.ebene === "VR" && r.land !== land) { land = r.land; h += `<tr class="land"><th colspan="${F.length + 1}">${esc(r.land_name)}</th></tr>`; }
    const lab = S.ebene === "VR" ? `<span class="vr">${r.id}</span>${esc(r.name)}` : esc(r.land_name);
    h += `<tr><th scope="row" class="rh ${r.id === S.region ? "sel" : ""}" data-r="${esc(r.id)}">${lab}</th>`;
    for (const f of F) {
      const w = get(r.id, S.abschnitt, f.id);
      const cls = ["cell", "k-" + klasse(w)];
      if (S.hatch && klein(w)) cls.push("hatched");
      if (r.id === S.region && f.id === S.fach) cls.push("sel"); else if (f.id === S.fach) cls.push("colsel");
      const al = `${titel(r)}, ${f.id}: ${lageText(w)}${w ? ", ÄAVE-Abstand " + sgn(w.abst) : ""}`;
      h += `<td><button type="button" class="${cls.join(" ")}" data-r="${esc(r.id)}" data-f="${f.id}" aria-label="${esc(al)}"></button></td>`;
    }
    h += "</tr>";
  }
  document.getElementById("mx").innerHTML = h + "</tbody>";
  /* Anteilsbalken: alle Fächer mit Soll-Intervall, auch PUL und KFO (der ÖSG bewertet beide; docs/WEB.md) */
  const c = { unter: 0, uk: 0, im: 0, "über": 0, ok: 0 };
  regs.forEach((r) => F.forEach((f) => {
    const w = get(r.id, S.abschnitt, f.id); if (!w) return;
    c[w.lage]++;
    if (S.hatch && klein(w)) c[w.lage === "unter" ? "uk" : "ok"]++;
  }));
  const n = c.unter + c.im + c["über"], pc = (v) => Math.round(v / n * 100);
  const seg = (v, k, hat) => v ? `<span class="k-${k}${hat ? " hatched" : ""}" style="flex:${v}"></span>` : "";
  document.getElementById("mx-sub").textContent = `${S.abschnitt === "IST" ? "IST" : "PLAN 2030"} · ${n} Zellen mit Wert`;
  document.getElementById("mx-share").innerHTML =
    `<div class="sbar" role="img" aria-label="${c.unter} unter, ${c.im} im Intervall, ${c["über"]} über">${seg(c.unter - c.uk, "u2")}${seg(c.uk, "u2", 1)}${seg(c.im, "in")}${seg(c.ok, "o2", 1)}${seg(c["über"] - c.ok, "o2")}</div>
    <div class="slab"><span><b>${pc(c.unter)} %</b> unter (${c.unter})</span><span><b>${pc(c.im)} %</b> im Intervall (${c.im})</span><span><b>${pc(c["über"])} %</b> über (${c["über"]})</span>${S.hatch ? `<span class="t2">schraffiert: weniger als 1 ÄAVE (${c.uk + c.ok})</span>` : ""}</div>`;
}
const mxEl = document.getElementById("mx");
mxEl.addEventListener("click", (e) => {
  const c = e.target.closest("[data-r],[data-f]"); if (!c) return;
  pick(c.dataset.r, c.dataset.f, c.classList.contains("cell") ? ".cell.sel" : c.classList.contains("rh") ? ".mx th.rh.sel" : null);
});
mxEl.addEventListener("pointermove", (e) => {
  const c = e.target.closest(".cell"); if (!c) return hideTip();
  showTip(e, tipHtml(regionById[c.dataset.r], c.dataset.f, S.abschnitt));
});
mxEl.addEventListener("pointerleave", hideTip);

/* Detailspalte. Jeder Vorbehalt nennt seinen Fallstrick in docs/DATEN.md (geprüft in tests/test_web.py). */
function vorbehalte(r, f, wI, wP) {
  const out = [], w = S.abschnitt === "IST" ? wI : wP, fi = fachInfo[f];
  if (fi.teil_von) out.push({ fallstrick: 4, text: `<b>Teil von ${fi.teil_von}.</b> ${f} steckt schon in ${fi.teil_von} und hat zusätzlich ein eigenes Soll-Intervall. Nicht addieren.` });
  const am = get(r.id, S.abschnitt, "AM");
  if ((f === "AM" || f === "IM") && am && /ZAE nicht getrennt/.test(am.zuschnitt))
    out.push({ fallstrick: 4, text: `<b>ZAE nicht getrennt ausgewiesen.</b> Die zentrale ambulante Erstversorgung steckt hier in den Fachspalten, vor allem IM. AM ist zu niedrig, IM zu hoch.` });
  if (wI && wP && (f === "AM" || f === "IM")) {
    const ai = get(r.id, "IST", "AM"), ap = get(r.id, "PLAN", "AM");
    if (ai && ap && /ZAE nicht getrennt/.test(ai.zuschnitt) !== /ZAE nicht getrennt/.test(ap.zuschnitt))
      out.push({ fallstrick: 10, text: `<b>IST → PLAN enthält eine Umbuchung</b> der ZAE von den Fachspalten nach AM, nicht nur Wachstum oder Abbau.` });
  }
  if (w && /Korrekturregel|KFO nicht getrennt/.test(w.zuschnitt))
    out.push({ fallstrick: 4, text: `<b>KFO in Oberösterreich:</b> nur als Fußnote zu ZMK gedruckt, ein Wert je Region, per Korrekturregel übernommen.` });
  if (r.land === "OÖ" && S.abschnitt === "PLAN")
    out.push({ fallstrick: 8, text: `<b>OÖ PLAN spitalsambulant</b> ist laut Fußnote das fortgeschriebene IST 2022, kein neuer Plan.` });
  if (r.land === "Wien")
    out.push({ fallstrick: 11, text: `<b>Wien</b> ist nicht Basis der Soll-Intervalle (Bundesdurchschnitt ohne Wien) und versorgt das Umland mit; Werte über VDmax sind hier zu erwarten.` });
  if (klein(w))
    out.push({ fallstrick: 6, text: `<b>Weniger als 1 ÄAVE vom Intervall entfernt.</b> Lage und Position sind hier nicht belastbar.` });
  if (S.ebene === "VR")
    out.push({ fallstrick: 11, text: `<b>Ohne Patientenströme.</b> Regionen mit Zentrumsfunktion liegen eher höher, ihr Umland eher tiefer.` });
  if (S.abschnitt === "IST")
    out.push({ fallstrick: 11, text: `<b>IST an der Norm 2030 gemessen.</b> Das zeigt den Abstand zur Norm 2030, keine Verletzung im IST-Jahr. IST-Jahr dieses Landes: ${wI ? wI.jahr : "–"}.` });
  return out;
}
function satz(w, label) {
  if (!w) return `<p>${label}: kein Wert.</p>`;
  if (w.lage === "im") return `<p>${label}: <b>im Soll-Intervall</b>.</p>`;
  if (w.lage === "unter") return `<p>${label}: Bis zur Untergrenze fehlen <b class="num">${fmt(-w.abst)}</b> ÄAVE Sachleistung.</p>`;
  return `<p>${label}: <b class="num">${fmt(w.abst)}</b> ÄAVE über der Obergrenze.</p>`;
}
function renderDetail() {
  const r = regionById[S.region], f = S.fach, fi = fachInfo[f], dg = vdDig(fi);
  const wI = get(r.id, "IST", f), wP = get(r.id, "PLAN", f);
  const row = (l, a, b) => `<div class="l">${l}</div><div class="v">${a}</div><div class="v">${b}</div>`;
  const val = (w, fn) => w ? fn(w) : "–";
  const num = (x) => `<span class="num">${x}</span>`;
  const first = S.abschnitt === "IST" ? [wI, "IST"] : [wP, "PLAN 2030"], second = S.abschnitt === "IST" ? [wP, "PLAN 2030"] : [wI, "IST"];
  document.getElementById("detail").innerHTML = `
    ${backTo ? `<button type="button" class="d-back" id="d-back">↑ Zurück zur Auswahl</button>` : ""}
    <h2 class="d-title">${r.ebene === "VR" ? `<span class="num" style="color:var(--muted);font-weight:400">${r.id}</span> ` : ""}${esc(titel(r))}</h2>
    <p class="d-meta">${r.ebene === "VR" ? esc(r.land_name) + " · " : ""}${esc(fi.name)} · Soll-Intervall <span class="num">${fmt(fi.min, dg)}–${fmt(fi.max, dg)}</span></p>
    <div class="d-grid">
      <div></div><div class="h v">IST ${wI ? wI.jahr : ""}</div><div class="h v">PLAN 2030</div>
      ${row("Versorgungsdichte", val(wI, (w) => num(fmt(w.vd, dg))), val(wP, (w) => num(fmt(w.vd, dg))))}
      ${row("ÄAVE", val(wI, (w) => num(fmt(w.aave))), val(wP, (w) => num(fmt(w.aave))))}
      ${row("Bevölkerung", val(wI, (w) => num(fmt(w.bev, 0))), val(wP, (w) => num(fmt(w.bev, 0))))}
      ${row("Lage", wI ? pill(wI) : "–", wP ? pill(wP) : "–")}
      ${row("Position", val(wI, (w) => num(fmt(w.pos, 2))), val(wP, (w) => num(fmt(w.pos, 2))))}
      ${row("ÄAVE-Abstand", val(wI, (w) => num(sgn(w.abst))), val(wP, (w) => num(sgn(w.abst))))}
    </div>
    <div class="minibar">${miniBar(wI, wP, fi, dg)}</div>
    <div class="say">${satz(first[0], first[1])}${satz(second[0], second[1])}</div>
    <ul class="cav">${vorbehalte(r, f, wI, wP).map((v) => `<li>${v.text} <a href="${DATEN_MD}" target="_blank" rel="noopener">Fallstrick ${v.fallstrick}</a></li>`).join("")}</ul>`;
}
function miniBar(wI, wP, fi, dg) {
  const W = 320, H = 46, x0 = 12, x1 = W - 12;
  const vals = [fi.min, fi.max, wI && wI.vd, wP && wP.vd].filter((v) => v != null);
  const span = fi.max - fi.min;
  let lo = Math.min(...vals, fi.min - span * .3);
  const hi = Math.max(...vals, fi.max + span * .3);
  lo = Math.max(0, lo);
  const x = (v) => x0 + (v - lo) / (hi - lo) * (x1 - x0);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Versorgungsdichte IST und PLAN im Soll-Intervall">`;
  s += `<rect class="band" x="${x(fi.min)}" y="8" width="${x(fi.max) - x(fi.min)}" height="16" rx="3"/>`;
  s += `<text class="mono muted" x="${x(fi.min)}" y="40" font-size="10.5" text-anchor="middle">${fmt(fi.min, dg)}</text><text class="mono muted" x="${x(fi.max)}" y="40" font-size="10.5" text-anchor="middle">${fmt(fi.max, dg)}</text>`;
  if (wI && wP) s += `<line class="s-link" x1="${x(wI.vd)}" x2="${x(wP.vd)}" y1="16" y2="16"/>`;
  if (wI) s += `<circle class="s-ring" cx="${x(wI.vd)}" cy="16" r="5"/>`;
  if (wP) s += `<circle class="f-${klasse(wP)} dot-ring" cx="${x(wP.vd)}" cy="16" r="6"/><circle cx="${x(wP.vd)}" cy="16" r="6" fill="none" stroke="var(--ink)" stroke-width="1"/>`;
  return s + "</svg>";
}

/* Positions-Plot */
const stripEl = document.getElementById("strip");
function renderStrip() {
  const f = S.fach, fi = fachInfo[f], dg = vdDig(fi);
  const regs = regionen().map((r) => ({ r, i: get(r.id, "IST", f), p: get(r.id, "PLAN", f) }));
  const key = (o) => { const w = S.abschnitt === "IST" ? o.i : o.p; return w ? w.pos : Infinity; };
  regs.sort((a, b) => key(a) - key(b));
  const W = Math.max(320, stripEl.clientWidth), narrow = W < 560;
  const LW = narrow ? 120 : 190, RW = 58, top = 34, rh = 21, H = top + regs.length * rh + 30;
  const X0 = LW + 8, X1 = W - RW - 8, LO = -1.5, HI = 3;
  const x = (p) => X0 + (Math.max(LO, Math.min(HI, p)) - LO) / (HI - LO) * (X1 - X0);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="Position im Soll-Intervall je Region, ${f}">`;
  s += `<rect class="band" x="${x(0)}" y="${top - 6}" width="${x(1) - x(0)}" height="${regs.length * rh + 6}"/>`;
  /* VDmin links und VDmax rechts vom Band ausrichten; die Zahlen −1, 2, 3 nur, wenn daneben Platz ist */
  const unit = x(1) - x(0);
  for (const t of [-1, 0, 1, 2, 3]) {
    s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${top - 6}" y2="${top + regs.length * rh}"/>`;
    if (t === 0) s += `<text class="mono" x="${x(0) - 3}" y="${top - 12}" font-size="10.5" text-anchor="end">VDmin ${fmt(fi.min, dg)}</text>`;
    else if (t === 1) s += `<text class="mono" x="${x(1) + 3}" y="${top - 12}" font-size="10.5" text-anchor="start">VDmax ${fmt(fi.max, dg)}</text>`;
    else if (unit >= 95) s += `<text class="muted mono" x="${x(t)}" y="${top - 12}" font-size="10.5" text-anchor="middle">${fmt(t, 0)}</text>`;
  }
  s += `<text class="muted" x="${X1 + RW}" y="${top - 12}" font-size="10.5" text-anchor="end">ÄAVE</text>`;
  regs.forEach((o, k) => {
    const y = top + k * rh + rh / 2, sel = o.r.id === S.region, w = S.abschnitt === "IST" ? o.i : o.p;
    const name = S.ebene === "VR" ? `${o.r.id} ${o.r.name}` : o.r.land_name;
    s += `<g class="row ${sel ? "sel" : ""}" data-r="${esc(o.r.id)}"><rect class="rowbg" x="0" y="${y - rh / 2}" width="${W}" height="${rh}" rx="3"/>`;
    s += `<text class="lab" x="${LW}" y="${y + 4}" font-size="12" text-anchor="end">${esc(trunc(name, narrow ? 16 : 28))}</text>`;
    if (o.i && o.p) s += `<line class="s-link" x1="${x(o.i.pos)}" x2="${x(o.p.pos)}" y1="${y}" y2="${y}"/>`;
    if (o.i) s += `<circle class="s-ring" cx="${x(o.i.pos)}" cy="${y}" r="4"/>`;
    if (o.p) s += `<circle class="f-${klasse(o.p)} dot-ring" cx="${x(o.p.pos)}" cy="${y}" r="5.5"/><circle cx="${x(o.p.pos)}" cy="${y}" r="5.5" fill="none" stroke="var(--ink)" stroke-width=".8" opacity=".55"/>`;
    for (const ww of [o.i, o.p]) if (ww && ww.pos > HI) s += `<text class="muted" x="${x(HI) + 8}" y="${y + 4}" font-size="11">›</text>`;
    s += `<text class="mono ${w && w.lage === "im" ? "muted" : ""}" x="${X1 + RW}" y="${y + 4}" font-size="11.5" text-anchor="end">${w ? (w.lage === "im" ? "0" : sgn(w.abst)) : "–"}</text></g>`;
  });
  s += `<text class="muted" x="${(X0 + X1) / 2}" y="${H - 6}" font-size="11" text-anchor="middle">Position: 0 = VDmin, 1 = VDmax${regs.some((o) => (o.i && o.i.pos > HI) || (o.p && o.p.pos > HI)) ? " · › Wert über 3, abgeschnitten" : ""}</text>`;
  stripEl.innerHTML = s + "</svg>";
}
stripEl.addEventListener("click", (e) => { const g = e.target.closest(".row"); if (g) pick(g.dataset.r, null, "#strip .row.sel"); });
stripEl.addEventListener("pointermove", (e) => {
  const g = e.target.closest(".row"); if (!g) return hideTip();
  const r = regionById[g.dataset.r], f = S.fach, i = get(r.id, "IST", f), p = get(r.id, "PLAN", f);
  showTip(e, `<b>${r.ebene === "VR" ? r.id + " " : ""}${esc(titel(r))}</b> · ${f}<br>IST: Position <span class="num">${i ? fmt(i.pos, 2) : "–"}</span>, ÄAVE <span class="num">${i ? sgn(i.abst) : "–"}</span><br>PLAN: Position <span class="num">${p ? fmt(p.pos, 2) : "–"}</span>, ÄAVE <span class="num">${p ? sgn(p.abst) : "–"}</span>`);
});
stripEl.addEventListener("pointerleave", hideTip);

/* Kachelkarte: Positionen aus web/kacheln.csv (über data.json) */
const mapEl = document.getElementById("map");
function renderMap() {
  const regs = regionen();
  const cols = Math.max(...regs.map((r) => r.spalte)) + 1, rows = Math.max(...regs.map((r) => r.zeile)) + 1;
  const W = Math.max(280, mapEl.clientWidth), g = 5, t = Math.min(64, (W - g * (cols - 1)) / cols);
  let s = `<svg viewBox="0 0 ${cols * (t + g)} ${rows * (t + g)}" width="100%" role="img" aria-label="Kachelkarte ${S.fach}">`;
  if (S.ebene === "VR") {
    /* Landesgrenzen: Kanten auf dem Raster der Fugenmitten; offene Enden enden bündig mit der Kachelkante */
    const land = {};
    for (const r of regs) land[[r.spalte, r.zeile].join()] = r.land;
    const seg = [], deg = {};
    for (const [k, l] of Object.entries(land)) {
      const [c, r] = k.split(",").map(Number);
      const re = land[[c + 1, r].join()], un = land[[c, r + 1].join()];
      if (re && re !== l) seg.push([c + 1, r, c + 1, r + 1]);
      if (un && un !== l) seg.push([c, r + 1, c + 1, r + 1]);
    }
    for (const [a, b, c, d] of seg) { deg[a + "," + b] = (deg[a + "," + b] || 0) + 1; deg[c + "," + d] = (deg[c + "," + d] || 0) + 1; }
    const P = (v) => v * (t + g) - g / 2;
    let d = "";
    for (const [a, b, c, e] of seg) {
      let ax = P(a), ay = P(b), bx = P(c), by = P(e);
      const dx = Math.sign(bx - ax) * g / 2, dy = Math.sign(by - ay) * g / 2;
      if (deg[a + "," + b] === 1) { ax += dx; ay += dy; }
      if (deg[c + "," + e] === 1) { bx -= dx; by -= dy; }
      d += `M${ax} ${ay}L${bx} ${by}`;
    }
    s += `<path class="blb" d="${d}"/>`;
  }
  for (const r of regs) {
    const w = get(r.id, S.abschnitt, S.fach), k = klasse(w), X = r.spalte * (t + g), Y = r.zeile * (t + g);
    s += `<g class="tile ${r.id === S.region ? "sel" : ""}" data-r="${esc(r.id)}" tabindex="0" role="button" aria-label="${esc(titel(r))}: ${lageText(w)}">`;
    s += `<rect class="t f-${k}" x="${X + 1}" y="${Y + 1}" width="${t - 2}" height="${t - 2}" rx="4"/>`;
    if (S.hatch && klein(w)) s += `<rect x="${X + 1}" y="${Y + 1}" width="${t - 2}" height="${t - 2}" rx="4" fill="url(#hp)"/>`;
    s += `<text class="${/[23]$/.test(k) ? "on" + k.slice(-1) : ""}" x="${X + t / 2}" y="${Y + t / 2 + 4}" text-anchor="middle">${esc(r.beschriftung)}</text></g>`;
  }
  s += `<defs><pattern id="hp" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(135)"><rect width="2" height="5" style="fill:var(--hatch)"/></pattern></defs>`;
  mapEl.innerHTML = s + "</svg>";
}
mapEl.addEventListener("click", (e) => { const g = e.target.closest(".tile"); if (g) pick(g.dataset.r, null, "#map .tile.sel"); });
mapEl.addEventListener("keydown", (e) => { const g = e.target.closest(".tile"); if (g && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); pick(g.dataset.r, null, "#map .tile.sel"); } });
mapEl.addEventListener("pointermove", (e) => { const g = e.target.closest(".tile"); if (!g) return hideTip(); showTip(e, tipHtml(regionById[g.dataset.r], S.fach, S.abschnitt)); });
mapEl.addEventListener("pointerleave", hideTip);

function render() {
  if (!regionById[S.region] || regionById[S.region].ebene !== S.ebene)
    S.region = regionById[STANDARD[S.ebene]] ? STANDARD[S.ebene] : regionen()[0].id;
  if (!fachInfo[S.fach]) S.fach = D.faecher[0].id;
  document.querySelectorAll("#seg-abschnitt button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === S.abschnitt));
  document.querySelectorAll("#seg-ebene button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.v === S.ebene));
  selF.value = S.fach;
  document.getElementById("chk-hatch").checked = S.hatch;
  document.getElementById("h-strip").textContent = `Position im Soll-Intervall · ${S.fach}`;
  document.getElementById("h-map").textContent = `Kachelkarte · ${S.fach} · ${S.abschnitt === "IST" ? "IST" : "PLAN 2030"}`;
  renderMatrix(); renderDetail(); renderStrip(); renderMap(); save();
}
let rt;
addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { renderStrip(); renderMap(); }, 120); });
render();
}
