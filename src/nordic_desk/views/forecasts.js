// Forecasts page: one stock and amount drive every section. No statistics here: the script picks precomputed sets,
// scales per-euro values by the amount, and draws charts at their measured width.
(function () {
  const D = JSON.parse(document.getElementById("fc-data").textContent);
  const MINUS = "−", THIN = " ";  // narrow no-break space: amounts never wrap
  const BUY = ["pullback", "steady"], WAIT = ["stretched", "wait_down", "wait_mixed"];
  const LABEL = { pullback: "Good entry · pullback", steady: "Good entry · steady", stretched: "Stretched",
    wait_down: "Wait · trend down", wait_mixed: "Wait · no clear trend" };
  const TONE = { pullback: "t-helps", steady: "t-helps", stretched: "t-str", wait_down: "t-against", wait_mixed: "t-against" };
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const sg = (x, d) => (x > 0 ? "+" : x < 0 ? MINUS : "") + Math.abs(x).toFixed(d);
  const pc = (x, d = 1, sign = true) => x == null ? "–" : (sign ? sg(x * 100, d) : Math.abs(x * 100).toFixed(d)) + "%";
  const grp = n => String(Math.round(Math.abs(n))).replace(/\B(?=(\d{3})+(?!\d))/g, THIN);
  const eur = (x, sign = false) => (x < 0 ? MINUS : sign && x > 0 ? "+" : "") + "€" + grp(x);
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const tagCls = r => ({ "helps": "t-helps", "works against": "t-against", "no clear edge": "t-noedge", "too few": "t-few",
    "consistent with the pooled reading": "t-consistent", "too noisy to trust alone": "t-noisy" })[r] || "t-noedge";
  const names = Object.fromEntries(D.subjects.map(s => [s.ticker, s.name]));
  names.SPY = "S&P 500";

  // state, kept in the URL hash so a reload or a link returns to the same view
  const h = new URLSearchParams(location.hash.slice(1));
  const first = (D.subjects.find(s => s.groups[0] === "held") || D.subjects[0] || { ticker: "SPY" }).ticker;
  const st = { t: Object.prototype.hasOwnProperty.call(names, h.get("t")) ? h.get("t") : first, a: +h.get("a") || +$("fc-amount").value,
    hz: ["63", "126", "252"].includes(h.get("h")) ? h.get("h") : "126", k: ["3", "6", "12"].includes(h.get("k")) ? h.get("k") : "6",
    scope: h.get("s") === "one" ? "one" : "all" };
  $("fc-stock").value = st.t; $("fc-amount").value = st.a || "";
  const save = () => history.replaceState(null, "", "#" + new URLSearchParams({ t: st.t, a: st.a || "", h: st.hz, k: st.k, s: st.scope }));
  const amountOk = () => st.a > 0 && st.a <= 1e7;

  function summary() {
    const t = st.t, name = esc(names[t] || t), today = (D.today || {})[t], g = today && today.group;
    const per = g && ((D.scorecard["126"].per_stock[t] || {})[g]), pooled = g && D.scorecard["126"].groups[g];
    const head = t === "SPY" ? `<p class="now">${name}: the yardstick every signal is compared with.</p>`
      : g ? `<p class="now">${name} today: <span class="tag ${TONE[g]}">${LABEL[g]}</span></p>`
      : `<p class="now">${name}: no verdict today (not enough price history).</p>`;
    let f1;
    if (t === "SPY" || !g) f1 = `<div><h3>Its signal before</h3><p>${t === "SPY" ? "Not scored against itself." : "Nothing to score yet."}</p></div>`;
    else if (!per) f1 = `<div><h3>Its signal before</h3><p>No past ${LABEL[g]} months for this stock.${pooled ? ` Across all stocks: ${pc(pooled.mean)} vs SPY at 6 m, ${esc(pooled.reading)}.` : ""}</p></div>`;
    else f1 = `<div><h3>When it said ${LABEL[g]} before</h3><p class="big">${pc(per.mean)} <span class="fine">vs SPY, 6 m</span></p>` +
      `<p>Average of ${plural(per.n_months, "month")} since ${esc(per.since)}; ahead of SPY ${pc(per.beat, 0, false)} of the time. <span class="tag ${tagCls(per.reading)}">${esc(per.reading)}</span></p></div>`;
    const e = (D.expected || {})[t], anc = D.anchor;
    const f0 = e ? `<div><h3>Expected return, 12 m</h3><p class="big">${pc(e.combined)} <span class="fine">combined</span></p>` +
        `<p>Market anchor ${pc(e.anchor)}${e.analyst != null ? `, analyst ${pc(e.analyst, 0)}` : ""}${e.signal != null ? `, signal ${pc(e.signal)}` : ""}. ` +
        `${e.pieces ? "Pulled halfway to the anchor." : "Anchor only: nothing stock-specific to add."} <a href="#expected">How</a></p></div>`
      : t === "SPY" && anc ? `<div><h3>Expected return, 12 m</h3><p class="big">${pc(anc.rate)} <span class="fine">a year, ${esc(anc.from)}–${esc(anc.to)}</span></p><p>SPY's own past return: the anchor for every stock.</p></div>`
      : `<div><h3>Expected return, 12 m</h3><p>Not available for this stock.</p></div>`;
    const vs = ((D.volsize || {})[t] || {}).now;
    const rec = ((D.volsize || {})[t] || {})["6"];
    const record = !rec ? "" : rec.held_back ? ` On this stock it beat the lump ${pc(rec.beat_lump, 0, false)} of the ${rec.held_back} times it held back.` : " It never held back on this stock before.";
    const hint = !vs ? "" : vs.first < 1
      ? ` Jumpy now: volatility ${pc(vs.current, 0, false)} against a usual ${pc(vs.usual, 0, false)}; a rule of thumb would put about ${pc(vs.first, 0, false)} in now${amountOk() ? ` (${eur(vs.first * st.a)})` : ""} and the rest over the next months.${record}`
      : " Volatility is close to usual: the rule would buy it all now.";
    const r = (D.lump[t] || {})["6"];
    const f2 = !r ? `<div><h3>Lump now or spread over 6 m</h3><p>Not enough price history.</p></div>`
      : `<div><h3>Lump now or spread over 6 m</h3><p class="big">${pc(r.lump_ahead, 0, false)} <span class="fine">lump ahead</span></p>` +
        `<p>Of ${plural(r.starts, "past start")}.${amountOk() ? ` Median difference ${eur(r.median_diff * st.a, true)} on ${eur(st.a)}.` : ""}${hint}</p></div>`;
    const row = D.targets.rows.find(x => x.ticker === t);
    const f3 = !row ? `<div><h3>Analyst target</h3><p>No target: this stock has no Ideas card with analyst coverage.</p></div>`
      : `<div><h3>Analyst target, made realistic</h3><p class="big">${pc(row.realistic, 0)} <span class="fine">realistic upside</span></p>` +
        `<p>Analysts imply ${pc(row.upside, 0)}; ${D.targets.rates.n_checked >= 30 ? "the desk's own record" : "a published study"} says targets run about ${pc(D.targets.rates.overshoot, 0, false)} high.</p></div>`;
    $("fc-summary").innerHTML = head + `<div class="facts">${f0}${f1}${f2}${f3}</div>` +
      (amountOk() ? "" : `<p class="fine">Enter an amount between €1 and €${grp(1e7)} to see euros.</p>`);
  }

  function forest(el, rows, ext, good, cur) {
    const W = Math.max(280, el.clientWidth), labW = Math.min(190, W * 0.42), R = W - 12, rowH = 40, top = 26, H = top + rows.length * rowH + 8;
    const X = v => labW + (R - labW) * (v + ext) / (2 * ext);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(el.getAttribute("aria-label") || "")}">`;
    s += good > 0 ? `<rect class="good" x="${X(0)}" y="${top - 8}" width="${R - X(0)}" height="${H - top}"/>` : `<rect class="good" x="${labW}" y="${top - 8}" width="${X(0) - labW}" height="${H - top}"/>`;
    s += `<text class="ax" x="${labW}" y="12">${pc(-ext, 0)}</text><text class="ax" x="${X(0)}" y="12" text-anchor="middle">0</text><text class="ax" x="${R}" y="12" text-anchor="end">${pc(ext, 0)}</text>`;
    s += `<line class="zero" x1="${X(0)}" x2="${X(0)}" y1="${top - 8}" y2="${H}"/>`;
    rows.forEach(([g, st_], i) => {
      const y = top + i * rowH + rowH / 2, isCur = g === cur;
      const col = /helps|consistent/.test(st_.reading) ? "var(--color-up)" : st_.reading === "works against" ? "var(--color-down)" : "var(--color-muted)";
      s += `<text class="lab halo${isCur ? " cur" : ""}" x="0" y="${y + 4}">${LABEL[g]}${isCur ? " · today" : ""}</text>`;
      if (st_.lo != null && st_.hi != null) s += `<line class="ci" x1="${X(st_.lo)}" x2="${X(st_.hi)}" y1="${y}" y2="${y}"/>`;
      if (isCur) s += `<circle class="ring" cx="${X(st_.mean)}" cy="${y}" r="10"/>`;
      s += `<circle class="dot" cx="${X(st_.mean)}" cy="${y}" r="6" fill="${col}"/>`;
    });
    el.innerHTML = rows.length ? s + "</svg>" : `<p class="fine">No months with ${Math.round(+st.hz / 21)}-month results for this choice.</p>`;
  }

  function scorecard() {
    const set = D.scorecard[st.hz], src = st.scope === "one" ? (set.per_stock[st.t] || {}) : set.groups;
    const cur = ((D.today || {})[st.t] || {}).group;
    const all = [...BUY, ...WAIT].filter(g => src[g]);
    const ext = Math.max(0.02, ...all.flatMap(g => [src[g].lo, src[g].hi, src[g].mean].filter(v => v != null).map(Math.abs))) * 1.1;
    $("sc-buy").setAttribute("aria-label", "Buy signals: average return against SPY with 95% intervals");
    $("sc-wait").setAttribute("aria-label", "Wait signals: average return against SPY with 95% intervals");
    forest($("sc-buy"), BUY.filter(g => src[g]).map(g => [g, src[g]]), ext, 1, cur);
    forest($("sc-wait"), WAIT.filter(g => src[g]).map(g => [g, src[g]]), ext, -1, cur);
    const m = Math.round(+st.hz / 21);
    $("sc-avg").textContent = `Average vs SPY, ${m} m`;
    $("sc-rows").innerHTML = all.length ? all.map(g => { const s = src[g];
      return `<tr${g === cur ? ' aria-current="true"' : ""}><th scope="row">${LABEL[g]}${g === cur ? " · today" : ""}</th><td class="num r" data-l="Months">${s.n_months}</td>` +
        `<td class="num r" data-l="Beat SPY">${pc(s.beat, 0, false)}</td><td class="num r" data-l="Average">${pc(s.mean)}</td>` +
        `<td class="num r" data-l="95%">${s.lo == null ? "too few months" : `${pc(s.lo)} to ${pc(s.hi)}`}</td><td><span class="tag ${tagCls(s.reading)}">${esc(s.reading)}</span></td></tr>`; }).join("")
      : `<tr><td colspan="6">${st.scope === "one" && st.t === "SPY" ? "SPY isn't scored against itself." : `No verdicts with ${m} months of later prices for this choice.`}</td></tr>`;
  }

  function lump() {
    const r = (D.lump[st.t] || {})[st.k], out = $("ls-out"), plot = $("ls-plot");
    if (!r) { out.innerHTML = `<p class="fine">Not enough history for ${esc(names[st.t] || st.t)}: it needs about ${12 + +st.k} months of prices.</p>`; plot.innerHTML = ""; return; }
    let html = `<p class="headline">${pc(r.lump_ahead, 0, false)}</p><p>of ${plural(r.starts, "past start month")}, buying all at once was ahead after 12 months.</p>`;
    if (amountOk()) {
      const a = st.a, med = r.median_diff * a, tail = (r.spread_p5 - r.lump_p5) * a;
      html += `<p>${med >= 0 ? `Spreading typically cost ${eur(med)}` : `Spreading typically gained ${eur(-med)}`} on ${eur(a)} (median). ` +
        (tail > 0 ? `In return, its worst 5% was ${eur(tail)} better than the lump's.` : `It did not soften the worst 5% (${eur(-tail)} worse).`) + `</p>` +
        `<div class="table-wrap"><table><thead><tr><th scope="col"></th><th scope="col" class="r">Lump now</th><th scope="col" class="r">Spread ${st.k} m</th></tr></thead><tbody>` +
        `<tr><th scope="row">Median after 12 m</th><td class="num r">${eur(r.lump_median * a)}</td><td class="num r">${eur(r.spread_median * a)}</td></tr>` +
        `<tr><th scope="row">Worst 5%</th><td class="num r">${eur(r.lump_p5 * a)}</td><td class="num r">${eur(r.spread_p5 * a)}</td></tr>` +
        `<tr><th scope="row">Worst regret</th><td class="num r">${eur(r.worst_lump_regret * a, true)}</td><td class="num r">${eur(r.worst_spread_regret * a, true)}</td></tr>` +
        `</tbody></table></div><p class="fine">Worst regret: the most one choice ended behind the other in any past start month.</p>`;
    } else html += `<p class="fine">Enter an amount between €1 and €${grp(1e7)} to see euros.</p>`;
    html += volBlock();
    out.innerHTML = html;
    const W = Math.max(280, plot.clientWidth), H = 220, L = 34, B = 176, T = 30, e = r.hist.edges, c = r.hist.counts, mx = Math.max(...c, 1);
    const x0 = e[0], x1 = e[e.length - 1], X = v => L + (W - L - 8) * (v - x0) / ((x1 - x0) || 1), Y = n => B - (B - T) * n / mx;
    let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Lump minus spread after 12 months across ${plural(r.starts, "start month")}; median ${pc(r.median_diff)}">`;
    s += `<line class="gl" x1="${L}" x2="${W - 8}" y1="${B}" y2="${B}"/><line class="gl" x1="${L}" x2="${L}" y1="${T}" y2="${B}"/>`;
    s += `<text class="ax" x="${L - 4}" y="${T + 4}" text-anchor="end">${mx}</text><text class="ax" x="${L - 4}" y="${B}" text-anchor="end">0</text>`;
    s += `<text class="ax" x="${L}" y="${T - 14}">start months</text>`;
    c.forEach((n, i) => { const mid = (e[i] + e[i + 1]) / 2;
      s += `<rect class="bar${mid > 0 ? " pos" : ""}" x="${X(e[i]) + 1}" y="${Y(n)}" width="${Math.max(1, X(e[i + 1]) - X(e[i]) - 2)}" height="${B - Y(n)}"/>`; });
    if (x0 < 0 && x1 > 0) s += `<line class="zero" x1="${X(0)}" x2="${X(0)}" y1="${T}" y2="${B + 4}"/>`;
    const mxX = X(r.median_diff), anchor = mxX > W * 0.7 ? "end" : "start";
    s += `<line class="med" x1="${mxX}" x2="${mxX}" y1="${T - 6}" y2="${B}"/><text class="ax halo" x="${mxX + (anchor === "start" ? 4 : -4)}" y="${T - 14}" text-anchor="${anchor}">median ${pc(r.median_diff)}</text>`;
    s += `<text class="ax" x="${L}" y="${B + 18}">${pc(x0, 0)}</text><text class="ax" x="${W - 8}" y="${B + 18}" text-anchor="end">${pc(x1, 0)}</text>` +
      `<text class="ax" x="${(L + W) / 2}" y="${B + 36}" text-anchor="middle">← spread better · lump better →</text></svg>`;
    plot.innerHTML = s;
  }

  function volBlock() {
    const v = ((D.volsize || {})[st.t] || {})[st.k], now = ((D.volsize || {})[st.t] || {}).now;
    let s = `<h3 class="vs-h">Vol-sized: less now when it's jumpy</h3>`;
    if (now) s += `<p>${now.first < 1 ? `Today: volatility ${pc(now.current, 0, false)} against a usual ${pc(now.usual, 0, false)}, so about ${pc(now.first, 0, false)} now${amountOk() ? ` (${eur(now.first * st.a)})` : ""} and the rest over ${st.k} months.` : `Today: volatility ${pc(now.current, 0, false)} is about usual (${pc(now.usual, 0, false)}), so the rule says buy it all now.`}</p>`;
    if (!v) return s + `<p class="fine">${st.k === "12" ? "Can't be tested with a 12-month spread: the last part would fall after the 12-month valuation date. Pick 3 or 6 months." : "Not enough history to test it: it needs a year of volatility before each start."}</p>`;
    if (!v.held_back) return s + `<p class="fine">Never triggered in this history: on all ${plural(v.starts, "start month")} volatility was close to usual.</p>`;
    s += `<p>It held back on ${v.held_back} of ${plural(v.starts, "start month")} (median first part ${pc(v.f_median, 0, false)}). On those months it beat the lump ${pc(v.beat_lump, 0, false)} of the time and the ${st.k}-month spread ${pc(v.beat_spread, 0, false)}.</p>`;
    if (amountOk()) { const a = st.a;
      s += `<div class="table-wrap"><table><thead><tr><th scope="col">On those months</th><th scope="col" class="r">Lump</th><th scope="col" class="r">Spread</th><th scope="col" class="r">Vol-sized</th></tr></thead><tbody>` +
        `<tr><th scope="row">Median after 12 m</th><td class="num r">${eur(v.lump_median * a)}</td><td class="num r">${eur(v.spread_median * a)}</td><td class="num r">${eur(v.median * a)}</td></tr>` +
        `<tr><th scope="row">Worst 5%</th><td class="num r">${eur(v.lump_p5 * a)}</td><td class="num r">${eur(v.spread_p5 * a)}</td><td class="num r">${eur(v.p5 * a)}</td></tr></tbody></table></div>`; }
    return s;
  }

  function targets() { document.querySelectorAll("#tg-rows tr, #ex-rows tr").forEach(tr => tr.dataset.t === st.t ? tr.setAttribute("aria-current", "true") : tr.removeAttribute("aria-current")); }

  const all = () => { summary(); scorecard(); lump(); targets(); save(); };
  const seg = (attr, key, fn) => document.querySelectorAll(`[data-${attr}]`).forEach(b => {
    b.setAttribute("aria-pressed", b.dataset[attr] === st[key]);
    b.addEventListener("click", () => { st[key] = b.dataset[attr]; document.querySelectorAll(`[data-${attr}]`).forEach(x => x.setAttribute("aria-pressed", x === b)); fn(); save(); }); });
  seg("hz", "hz", scorecard); seg("scope", "scope", scorecard); seg("k", "k", lump);
  $("fc-stock").addEventListener("change", e => { st.t = e.target.value; all(); });
  let timer;
  $("fc-amount").addEventListener("input", e => { st.a = parseFloat(e.target.value); clearTimeout(timer); timer = setTimeout(() => { summary(); lump(); save(); }, 300); });
  let w = 0;
  new ResizeObserver(() => { const nw = $("sc-buy").clientWidth; if (Math.abs(nw - w) > 8) { w = nw; scorecard(); lump(); } }).observe(document.body);
  all();
})();
