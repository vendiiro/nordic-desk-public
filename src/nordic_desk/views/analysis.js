// Analysis page: draws the chart and the hover boxes from the embedded data. No indicator maths here: every number is read from the payload.
(function () {
  const D = JSON.parse(document.getElementById("analysis-data").textContent);
  const N = D.dates.length, MINUS = "−";
  const OVER = ["sma50", "sma200", "bb", "h52"], PANELS = ["rsi", "macd", "dd", "pe"];
  const COL = { sma50: "var(--color-s2)", sma200: "var(--color-s1)", bb: "var(--color-s3)", h52: "var(--color-s4)", rsi: "var(--color-s1)", macd: "var(--color-s2)", dd: "var(--color-down)", pe: "var(--color-s1)" };
  const st = { h: "entry", range: 252, style: "line", on: new Set(), hi: N - 1 };
  const chart = document.getElementById("chart"), pop = document.getElementById("pop");
  const tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true;
  const nf = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sgn = (x, d) => (x > 0 ? "+" : x < 0 ? MINUS : "") + Math.abs(x).toFixed(d);
  const F = {
    price: v => (D.currency ? D.currency + " " : "") + nf.format(v),
    pct: v => sgn(v * 100, 1) + "%", pct0: v => Math.round(v * 100) + "%",
    num1: v => v.toFixed(1).replace("-", MINUS), num2: v => v.toFixed(2).replace("-", MINUS), date: v => v,
  };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const fill = (t, i) => t.replace(/\{(\w+)\|(\w+)\}/g, (m, f, k) => { const v = D[f] && D[f][i]; return v == null ? "–" : F[k](v); });
  const fdate = s => new Date(s + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const val = (k, i, f) => { const v = D[k][i]; return v == null ? "–" : F[f](v); };

  function explainHTML(k, i) {
    const e = D.explain[k];
    return `<h4>${esc(e.title)}</h4><p>${esc(e.what)}</p>${e.formula ? `<p class="formula">${esc(e.formula)}</p>` : ""}` +
      `<p><span class="k">How to use it:</span> ${esc(e.use)}</p>${e.now ? `<p class="now"><b>${fdate(D.dates[i])}:</b> ${esc(fill(e.now, i))}</p>` : ""}`;
  }
  function priceHTML(i) {
    const vi = (st.h === "entry" ? D.entry_day : D.long_day)[i], v = vi == null ? null : D.verdicts[vi];
    const rows = [["1 week", val("chg_1w", i, "pct")], ["1 month", val("chg_1m", i, "pct")], ["1 year", val("chg_1y", i, "pct")],
      ["From 52-week high", val("dist52", i, "pct")], ["Trend (200-day)", D.trend[i] || "–"], ["RSI", val("rsi", i, "num1")]];
    if (st.h === "long" && D.kind === "stock") rows.push(["P/E", val("pe", i, "num1")]);
    return `<h4>${fdate(D.dates[i])} · <span class="num">${val("c", i, "price")}</span></h4><dl class="rows">` +
      rows.map(([a, b]) => `<dt>${a}</dt><dd class="num">${esc(b)}</dd>`).join("") + "</dl>" +
      (v ? `<p><span class="tag ${v.cls}">${esc(v.v)}</span> ${esc(v.line)}.</p>` : "");
  }
  function showPop(html, el) {
    pop.innerHTML = html; pop.hidden = false;
    const r = el.getBoundingClientRect(), w = pop.offsetWidth;
    let y = r.bottom + 8; if (y + pop.offsetHeight > innerHeight - 8) y = Math.max(8, r.top - pop.offsetHeight - 8);
    pop.style.left = Math.min(innerWidth - w - 8, Math.max(8, r.left)) + "px"; pop.style.top = y + "px";
  }
  const hidePop = () => { pop.hidden = true; };
  document.querySelectorAll("[data-k]").forEach(el => {
    const show = () => showPop(explainHTML(el.dataset.k, st.hi), el);
    el.addEventListener("mouseenter", show); el.addEventListener("focus", show);
    el.addEventListener("mouseleave", hidePop); el.addEventListener("blur", hidePop);
    if (el.classList.contains("chip")) el.addEventListener("click", () => { toggle(el.dataset.k); });
    else el.addEventListener("click", show);
  });
  function toggle(k) { st.on.has(k) ? st.on.delete(k) : st.on.add(k); sync(); draw(); }
  function setH(h) {
    const d = D.defaults[h]; st.h = h; st.range = d.range; st.style = D.has_ohlc ? d.style : "line"; st.on = new Set(d.on); st.hi = N - 1;
    document.querySelectorAll("[data-h-panel]").forEach(p => { p.hidden = p.dataset.hPanel !== h; });
    sync(); draw();
  }
  function sync() {
    document.querySelectorAll("[data-h]").forEach(b => b.setAttribute("aria-pressed", b.dataset.h === st.h));
    document.querySelectorAll(".chip[data-k]").forEach(b => b.setAttribute("aria-pressed", st.on.has(b.dataset.k)));
    document.querySelectorAll("[data-r]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.r === st.range));
    document.querySelectorAll("[data-s]").forEach(b => b.setAttribute("aria-pressed", b.dataset.s === st.style));
  }
  document.querySelectorAll("[data-h]").forEach(b => b.addEventListener("click", () => setH(b.dataset.h)));
  document.querySelectorAll("[data-r]").forEach(b => b.addEventListener("click", () => { st.range = +b.dataset.r; sync(); draw(); }));
  document.querySelectorAll("[data-s]").forEach(b => b.addEventListener("click", () => { st.style = b.dataset.s; sync(); draw(); }));
  const pick = document.getElementById("pick"); if (pick) pick.addEventListener("change", () => { location.href = pick.value; });

  let geo = null;
  function draw() {
    const W = Math.max(320, chart.clientWidth), panels = PANELS.filter(k => st.on.has(k) && document.querySelector(`.chip[data-k="${k}"]`));
    const PH = Math.round(Math.min(560, Math.max(320, innerHeight * 0.5))), SH = 80, G = 24, padL = 4, padR = 56, Ht = PH + panels.length * (SH + G) + 22;
    const n = Math.min(st.range, N), start = N - n, candle = st.style === "candle" && D.has_ohlc;
    const step = Math.max(1, Math.ceil(n / (candle ? 150 : 600))), bars = [];
    for (let s = start; s < N; s += step) {
      const e = Math.min(N - 1, s + step - 1); let h = -Infinity, l = Infinity;
      for (let k = s; k <= e; k++) { h = Math.max(h, D.h[k] ?? D.c[k]); l = Math.min(l, D.l[k] ?? D.c[k]); }
      bars.push({ i: e, o: D.o[s] ?? D.c[s], h, l, c: D.c[e] });
    }
    const nb = bars.length, bw = (W - padL - padR) / nb, X = j => padL + bw * (j + 0.5);
    let lo = Infinity, hi = -Infinity;
    const seen = v => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } };
    bars.forEach(b => { seen(candle ? b.l : b.c); seen(candle ? b.h : b.c);
      if (st.on.has("sma50")) seen(D.sma50[b.i]); if (st.on.has("sma200")) seen(D.sma200[b.i]);
      if (st.on.has("bb")) { seen(D.bb_up[b.i]); seen(D.bb_lo[b.i]); } if (st.on.has("h52")) seen(D.high52[b.i]); });
    const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
    const Y = v => 10 + (PH - 20) * (1 - (v - lo) / (hi - lo));
    const path = (arr, yf) => { let d = "", pen = false; bars.forEach((b, j) => { const v = arr[b.i]; if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + X(j).toFixed(1) + " " + yf(v).toFixed(1); pen = true; }); return d; };
    let s = `<svg viewBox="0 0 ${W} ${Ht}" height="${Ht}" role="img" aria-label="Price chart of ${esc(D.name)}">`;
    for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4, y = Y(v); s += `<line class="gl" x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}"/><text class="ax" x="${W - padR + 6}" y="${y + 4}">${nf.format(v)}</text>`; }
    if (st.on.has("bb")) {
      let band = ""; bars.forEach((b, j) => { if (D.bb_up[b.i] != null) band += (band ? "L" : "M") + X(j).toFixed(1) + " " + Y(D.bb_up[b.i]).toFixed(1); });
      for (let j = nb - 1; j >= 0; j--) { const b = bars[j]; if (D.bb_lo[b.i] != null) band += "L" + X(j).toFixed(1) + " " + Y(D.bb_lo[b.i]).toFixed(1); }
      if (band) s += `<path d="${band}Z" class="bb-fill"/>`;
      s += `<path d="${path(D.bb_up, Y)}" class="ln" style="stroke:${COL.bb}" stroke-width="1.2"/><path d="${path(D.bb_lo, Y)}" class="ln" style="stroke:${COL.bb}" stroke-width="1.2"/><path d="${path(D.bb_mid, Y)}" class="ln dash" style="stroke:${COL.bb}" stroke-width="1"/>`;
    }
    if (st.on.has("h52")) s += `<path d="${path(D.high52, Y)}" class="ln dash2" style="stroke:${COL.h52}" stroke-width="1.2"/>`;
    if (candle) bars.forEach((b, j) => { const up = b.c >= b.o, x = X(j), w = Math.max(1, bw * 0.62);
      s += `<g class="${up ? "cu" : "cd"}"><line x1="${x}" x2="${x}" y1="${Y(b.h)}" y2="${Y(b.l)}"/><rect x="${x - w / 2}" y="${Y(Math.max(b.o, b.c))}" width="${w}" height="${Math.max(1, Math.abs(Y(b.o) - Y(b.c)))}"/></g>`; });
    else s += `<path d="${path(D.c, Y)}" class="ln price"/>`;
    if (st.on.has("sma50")) s += `<path d="${path(D.sma50, Y)}" class="ln" style="stroke:${COL.sma50}" stroke-width="1.6"/>`;
    if (st.on.has("sma200")) s += `<path d="${path(D.sma200, Y)}" class="ln" style="stroke:${COL.sma200}" stroke-width="2"/>`;
    const pg = []; let top = PH + G;
    panels.forEach(k => {
      const y0 = top, y1 = top + SH; let a, b, ser, ref = [];
      const vals = arrs => bars.flatMap(x => arrs.map(r => r[x.i])).filter(v => v != null);
      if (k === "rsi") { a = 0; b = 100; ser = [[D.rsi, COL.rsi]]; ref = [30, 70]; }
      if (k === "macd") { const v = vals([D.macd, D.macd_signal]); a = Math.min(...v, 0); b = Math.max(...v, 0); ser = [[D.macd, COL.macd], [D.macd_signal, "var(--color-muted)"]]; ref = [0]; }
      if (k === "dd") { a = Math.min(...vals([D.drawdown]), -0.01); b = 0; ser = [[D.drawdown, COL.dd]]; ref = [0]; }
      if (k === "pe") { const v = vals([D.pe]); a = v.length ? Math.min(...v) * 0.95 : 0; b = v.length ? Math.max(...v) * 1.05 : 1; ser = [[D.pe, COL.pe]]; const m = D.pe_median[N - 1]; if (m != null) ref = [m]; }
      const Yp = v => y0 + SH * (1 - (v - a) / ((b - a) || 1));
      s += `<rect class="pbg" x="${padL}" y="${y0}" width="${W - padL - padR}" height="${SH}"/><text class="plab" x="${padL + 6}" y="${y0 + 13}">${esc(D.explain[k].title)}</text>`;
      if (k === "rsi") s += `<rect class="rsi-band" x="${padL}" y="${Yp(70)}" width="${W - padL - padR}" height="${Yp(30) - Yp(70)}"/>`;
      if (k === "dd") { let d = "M" + X(0) + " " + Yp(0); bars.forEach((x, j) => { const v = D.drawdown[x.i]; if (v != null) d += "L" + X(j).toFixed(1) + " " + Yp(v).toFixed(1); }); s += `<path d="${d}L${X(nb - 1)} ${Yp(0)}Z" class="dd-fill"/>`; }
      ref.forEach(v => { s += `<line class="gl dash" x1="${padL}" x2="${W - padR}" y1="${Yp(v)}" y2="${Yp(v)}"/><text class="ax" x="${W - padR + 6}" y="${Yp(v) + 4}">${k === "dd" ? "0%" : k === "pe" ? "median" : v}</text>`; });
      if (k === "macd") bars.forEach((x, j) => { const v = D.macd_hist[x.i]; if (v != null) s += `<line class="${v > 0 ? "hu" : "hd"}" x1="${X(j)}" x2="${X(j)}" y1="${Yp(0)}" y2="${Yp(v)}" stroke-width="${Math.max(1, bw * 0.6)}"/>`; });
      ser.forEach(([arr, col]) => { s += `<path d="${path(arr, Yp)}" class="ln" style="stroke:${col}" stroke-width="1.4"/>`; });
      if (k === "dd") s += `<text class="ax" x="${W - padR + 6}" y="${y1}">${Math.round(a * 100)}%</text>`;
      if (k === "pe" && !vals([D.pe]).length) s += `<text class="plab" x="${padL + 6}" y="${y0 + 40}">${esc(D.pe_reason || "not enough P/E history")}</text>`;
      pg.push({ k, y0, y1 }); top += SH + G;
    });
    const every = Math.max(1, Math.ceil(nb / Math.max(2, Math.min(6, Math.floor(W / 110)))));  // fewer labels on a phone
    for (let j = 0; j < nb; j += every) { const d = D.dates[bars[j].i]; s += `<text class="ax" x="${j ? X(j) : padL}" y="${Ht - 4}" text-anchor="${j ? "middle" : "start"}">${n > 300 ? d.slice(0, 7) : d.slice(5)}</text>`; }
    s += `<g class="xh" hidden><line/><circle r="4"/></g></svg>`;
    chart.innerHTML = s; chart.appendChild(tip);
    geo = { W, Ht, PH, bars, X, Y, bw, padL, pg };
  }
  function hover(px, py) {
    if (!geo) return;
    const { bars, X, Y, bw, padL, PH, pg, Ht } = geo;
    const j = Math.max(0, Math.min(bars.length - 1, Math.round((px - padL) / bw - 0.5))), b = bars[j];
    st.hi = b.i;
    const g = chart.querySelector(".xh"); g.removeAttribute("hidden");
    const ln = g.querySelector("line"), dot = g.querySelector("circle");
    ln.setAttribute("x1", X(j)); ln.setAttribute("x2", X(j)); ln.setAttribute("y1", 0); ln.setAttribute("y2", Ht - 16);
    dot.setAttribute("cx", X(j)); dot.setAttribute("cy", Y(b.c));
    let key = "price";
    if (py > PH) { const p = pg.find(p => py >= p.y0 - 6 && py <= p.y1 + 6); if (p) key = p.k; }
    else {
      let best = Math.abs(Y(b.c) - py); const cand = [];
      if (st.on.has("sma50")) cand.push(["sma50", D.sma50[b.i]]); if (st.on.has("sma200")) cand.push(["sma200", D.sma200[b.i]]);
      if (st.on.has("bb")) cand.push(["bb", D.bb_up[b.i]], ["bb", D.bb_lo[b.i]], ["bb", D.bb_mid[b.i]]);
      if (st.on.has("h52")) cand.push(["h52", D.high52[b.i]]);
      cand.forEach(([k, v]) => { if (v == null) return; const d = Math.abs(Y(v) - py); if (d < 8 && d < best) { best = d; key = k; } });
    }
    tip.innerHTML = key === "price" ? priceHTML(b.i) : explainHTML(key, b.i); tip.hidden = false;
    const cw = chart.clientWidth, sc = cw / geo.W, tw = tip.offsetWidth; let x = X(j) * sc + 16; if (x + tw > cw) x = X(j) * sc - tw - 16;
    tip.style.left = Math.max(0, x) + "px"; tip.style.top = Math.max(0, Math.min(py * sc - 20, Ht * sc - tip.offsetHeight)) + "px";
  }
  function leave() { const g = chart.querySelector(".xh"); if (g) g.setAttribute("hidden", ""); tip.hidden = true; st.hi = N - 1; }
  const pt = e => { const r = chart.getBoundingClientRect(), k = geo.W / r.width; return [(e.clientX - r.left) * k, (e.clientY - r.top) * k]; };
  chart.addEventListener("pointermove", e => hover(...pt(e)));
  chart.addEventListener("pointerdown", e => hover(...pt(e)));
  chart.addEventListener("pointerleave", e => { if (e.pointerType !== "touch") leave(); });  // a tap keeps its box until the next tap elsewhere
  document.addEventListener("pointerdown", e => { if (!chart.contains(e.target)) leave(); if (!e.target.closest("[data-k]")) hidePop(); });
  chart.addEventListener("keydown", e => {
    if (!geo || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    e.preventDefault(); let j = geo.bars.findIndex(b => b.i >= st.hi); if (j < 0) j = geo.bars.length - 1;
    j = Math.max(0, Math.min(geo.bars.length - 1, j + (e.key === "ArrowLeft" ? -1 : 1)));
    hover(geo.X(j), geo.Y(geo.bars[j].c));
  });
  chart.addEventListener("blur", leave);
  new ResizeObserver(() => draw()).observe(chart);
  setH("entry");
})();
