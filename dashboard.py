"""Build the website (outputs/site/index.html) from the latest picks and headlines:  python dashboard.py

Reads outputs/forecast.json (made by forecast.py) and data/news/headlines.csv (made by news.py).
Everything is embedded in one self-contained page, so it works from GitHub Pages or straight from disk.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import config
import news

SITE_DIR = os.path.join(config.OUTPUT_DIR, "site")
PAGE = os.path.join(SITE_DIR, "index.html")
FORECAST = os.path.join(config.OUTPUT_DIR, "forecast.json")


def _recent_news():
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.NEWS_PAGE_DAYS)
    rows = []
    for r in news.load_archive():
        pub = news._parse_date(r["published"])
        if pub and pub >= cutoff:
            rows.append({"t": pub.isoformat(), "source": r["source"], "title": r["title"],
                         "link": r["link"], "summary": r["summary"], "seen": r["first_seen"]})
    rows.sort(key=lambda r: r["t"], reverse=True)
    return rows


def build():
    forecast = None
    if os.path.exists(FORECAST):
        with open(FORECAST) as f:
            forecast = json.load(f)
    payload = {"forecast": forecast, "news": _recent_news(),
               "built": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.replace("__DATA__", blob))
    return PAGE


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bhrugu's Stock Model</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f7f6f3; --panel:#ffffff; --text:#1c1917; --muted:#6b6560; --line:#e7e3da; --soft:#f3f1ec;
  --brand:#1c1917; --brand-text:#ffffff; --brand-2:#b45309; --up:#15803d; --up-bg:#dcfce7; --down:#b91c1c; --down-bg:#fee2e2;
  --gold:#d97706; --bar:#d97706; --bar-2:#a8a29e; --head:#1c1917; --head-text:#e7e5e4; --logo:#d97706;
  --shadow:0 1px 2px rgba(28,25,23,.05), 0 1px 3px rgba(28,25,23,.08);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#12110f; --panel:#1c1a17; --text:#ede9e3; --muted:#a39e96; --line:#2e2a25; --soft:#171512;
  --brand:#f59e0b; --brand-text:#1c1917; --brand-2:#fbbf24; --up:#4ade80; --up-bg:#052e16; --down:#f87171; --down-bg:#450a0a;
  --gold:#fbbf24; --bar:#f59e0b; --bar-2:#57534e; --head:#0d0c0a; --head-text:#d6d3d1; --logo:#f59e0b; --shadow:none; } }
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--text);
  font:14px/1.5 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-feature-settings:"tnum"; }
a { color:var(--brand-2); }
header { background:var(--head); color:var(--head-text); position:sticky; top:0; z-index:5; }
.bar { max-width:1180px; margin:0 auto; padding:0 16px; display:flex; align-items:center; gap:24px; min-height:58px; flex-wrap:wrap; }
.logo { display:flex; align-items:center; gap:10px; font-weight:700; font-size:16px; color:#fff; letter-spacing:-.01em; }
.logo svg { width:26px; height:26px; }
nav { display:flex; gap:4px; flex-wrap:wrap; }
nav button { background:none; border:0; color:var(--head-text); font:inherit; font-weight:500; padding:8px 12px; border-radius:6px; cursor:pointer; opacity:.75; }
nav button:hover { opacity:1; background:rgba(255,255,255,.06); }
nav button.on { opacity:1; background:rgba(255,255,255,.12); color:#fff; }
.stamp { margin-left:auto; font-size:12px; opacity:.7; }
main { max-width:1180px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:24px; letter-spacing:-.02em; margin:0 0 4px; }
h2 { font-size:16px; margin:28px 0 10px; }
.lede { color:var(--muted); margin:0 0 20px; max-width:760px; }
.seg { display:inline-flex; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:3px; margin-bottom:18px; box-shadow:var(--shadow); }
.seg button { border:0; background:none; font:inherit; font-weight:600; color:var(--muted); padding:7px 16px; border-radius:6px; cursor:pointer; }
.seg button.on { background:var(--brand); color:var(--brand-text); }
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:12px; margin-bottom:20px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; box-shadow:var(--shadow); }
.card .k { font-size:12px; color:var(--muted); font-weight:500; text-transform:uppercase; letter-spacing:.04em; }
.card .v { font-size:24px; font-weight:700; letter-spacing:-.02em; margin:4px 0 2px; }
.card .s { font-size:12px; color:var(--muted); }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); overflow:hidden; }
.scroll { overflow-x:auto; }
table { width:100%; border-collapse:collapse; }
th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); font-weight:600; padding:10px 12px; border-bottom:1px solid var(--line); background:var(--soft); white-space:nowrap; }
td { padding:11px 12px; border-bottom:1px solid var(--line); vertical-align:middle; }
#period-table td { white-space:nowrap; }
tr:last-child td { border-bottom:0; }
.num { text-align:right; white-space:nowrap; }
.tk { font-weight:700; }
.nm { color:var(--muted); font-size:12px; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.prob { display:flex; align-items:center; gap:8px; min-width:130px; }
.prob .track { flex:1; height:6px; background:var(--soft); border-radius:3px; overflow:hidden; border:1px solid var(--line); }
.prob .fill { height:100%; background:var(--bar); }
.stars { color:var(--gold); letter-spacing:1px; white-space:nowrap; }
.stars .off { color:var(--line); }
.range { position:relative; height:18px; min-width:150px; }
.range .axis { position:absolute; top:8px; left:0; right:0; height:2px; background:var(--soft); }
.range .span { position:absolute; top:5px; height:8px; border-radius:4px; background:linear-gradient(90deg, var(--down), var(--bar-2) 45%, var(--up)); opacity:.75; }
.range .zero { position:absolute; top:1px; width:1px; height:16px; background:var(--muted); }
.range-txt { font-size:11px; color:var(--muted); white-space:nowrap; }
.chip { display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px; background:var(--soft); border:1px solid var(--line); margin:2px 4px 2px 0; white-space:nowrap; }
.pill { display:inline-block; font-size:12px; font-weight:600; padding:2px 8px; border-radius:6px; }
.pill.up { color:var(--up); background:var(--up-bg); } .pill.down { color:var(--down); background:var(--down-bg); }
.note { color:var(--muted); font-size:12px; margin:10px 2px 0; max-width:900px; }
.grid2 { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:16px; }
.chart { padding:14px 16px; }
.chart svg { width:100%; height:auto; display:block; }
.legend { display:flex; gap:14px; font-size:12px; color:var(--muted); margin-bottom:6px; flex-wrap:wrap; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.hbar { display:grid; grid-template-columns:150px 1fr 54px; align-items:center; gap:10px; margin:7px 0; font-size:13px; }
.hbar .t { height:10px; background:var(--soft); border-radius:5px; overflow:hidden; position:relative; }
.hbar .f { height:100%; background:var(--bar); border-radius:5px; }
.hbar .mid { position:absolute; left:50%; top:-3px; bottom:-3px; width:1px; background:var(--muted); }
.search { width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:var(--panel); color:var(--text); font:inherit; font-size:15px; box-shadow:var(--shadow); }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 6px; }
.fchip { border:1px solid var(--line); background:var(--panel); color:var(--text); border-radius:999px; padding:4px 11px; font:inherit; font-size:12px; cursor:pointer; }
.fchip.on { background:var(--brand); border-color:var(--brand); color:var(--brand-text); }
.day { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); font-weight:600; margin:22px 0 8px; }
.story { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px 16px; margin:8px 0; box-shadow:var(--shadow); }
.story a { color:var(--text); text-decoration:none; font-weight:600; font-size:15px; }
.story a:hover { color:var(--brand-2); }
.story p { margin:4px 0 0; color:var(--muted); font-size:13px; }
.meta { font-size:12px; color:var(--muted); margin-bottom:2px; }
.new { color:var(--up); font-weight:600; }
.prose { max-width:780px; }
.prose p, .prose li { color:var(--text); }
.prose h2 { margin-top:26px; }
.warn { background:var(--down-bg); color:var(--down); border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:16px; }
footer { max-width:1180px; margin:0 auto; padding:0 16px 40px; color:var(--muted); font-size:12px; }
.hidden { display:none !important; }
.clickable { cursor:pointer; }
.clickable:hover td { background:var(--soft); }
a.tk { color:inherit; text-decoration:none; } a.tk:hover { color:var(--brand-2); text-decoration:underline; }
.detail { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:18px 20px; margin:16px 0 20px; box-shadow:var(--shadow); }
.detail-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 14px; margin-bottom:4px; }
.detail-head .big { font-size:26px; font-weight:700; letter-spacing:-.02em; }
.detail-head .co { font-size:16px; font-weight:600; }
.detail-head .x { margin-left:auto; background:none; border:1px solid var(--line); border-radius:6px; color:var(--muted); font:inherit; padding:3px 10px; cursor:pointer; }
.badge { display:inline-block; font-size:12px; font-weight:600; padding:3px 10px; border-radius:999px; background:var(--brand); color:var(--brand-text); }
.detail .cards { margin:14px 0 6px; }
.detail h3 { font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:16px 0 6px; }
@media (max-width:640px) { .stamp { margin-left:0; width:100%; padding-bottom:8px; } .bar { gap:10px; padding-top:8px; } .hbar { grid-template-columns:110px 1fr 46px; } }
</style></head>
<body>
<header><div class="bar">
  <div class="logo"><svg viewBox="0 0 26 26" fill="none"><rect width="26" height="26" rx="6" fill="var(--logo)"/><path d="M5 18l5-6 4 3 7-9" stroke="#1c1917" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>Bhrugu&rsquo;s Stock Model</div>
  <nav id="nav">
    <button data-tab="picks">Today's picks</button><button data-tab="live">Live record</button><button data-tab="record">Backtest</button>
    <button data-tab="lookup">Stock lookup</button>    <button data-tab="news">Market news</button><button data-tab="method">How it works</button>
  </nav>
  <div class="stamp" id="stamp"></div>
</div></header>

<main>
<section id="tab-picks">
  <h1>Today's picks</h1>
  <p class="lede" id="picks-lede"></p>
  <div id="picks-warn"></div>
  <div class="seg" id="seg-picks"></div>
  <div class="cards" id="pick-cards"></div>
  <div class="panel scroll"><table id="pick-table"></table></div>
  <p class="note"><b>Model score</b>: <span id="score-note"></span>
  <b>Conviction</b>: how far the score stands out from the other ~500 stocks today.
  <b>Likely range</b>: where 8 out of 10 outcomes would land if the stock moves as much as it has over the last 3 years (assumes the market's long-run ~8% yearly return).
  <b>Chance of loss</b>: probability of ending the period below today's price, from the same assumption; in brackets, how often this stock actually lost money over periods this long since 2010.</p>
</section>

<section id="tab-live" class="hidden">
  <h1>Live record</h1>
  <p class="lede" id="live-lede"></p>
  <div class="seg" id="seg-live"></div>
  <div class="cards" id="live-cards"></div>
  <h2 id="first-title"></h2>
  <div class="panel scroll"><table id="first-table"></table></div>
  <h2>Every day's picks</h2>
  <div class="panel scroll"><table id="cohort-table"></table></div>
  <p class="note">Each row is one morning's picks for this holding period, scored from that day's closing price. A pick stays <b>open</b>
  until its holding period ends; then its result is <b>final</b> and never changes. The record is saved on GitHub, where every change is dated.</p>
</section>

<section id="tab-lookup" class="hidden">
  <h1>Stock lookup</h1>
  <p class="lede" id="lookup-lede"></p>
  <input id="lq" class="search" type="search" placeholder="Search by ticker or company: AAPL, Nvidia, bank..." autocomplete="off">
  <div id="stock-detail"></div>
  <div class="chips" id="lookup-filters"></div>
  <div class="seg" id="seg-lookup"></div>
  <div class="panel scroll"><table id="stock-table"></table></div>
  <p class="note" id="stock-count"></p>
</section>

<section id="tab-record" class="hidden">
  <h1>Backtest</h1>
  <p class="lede" id="record-lede"></p>
  <div class="seg" id="seg-record"></div>
  <div class="cards" id="record-cards"></div>
  <div class="panel chart"><div class="legend"><span><i style="background:var(--up)"></i>Picks beat the S&amp;P 500</span><span><i style="background:var(--down)"></i>Picks trailed the S&amp;P 500</span></div><div id="excess-chart"></div></div>
  <p class="note">Each bar is one set of picks made at the start of a quarter and held for the full period: the picks' return minus the S&amp;P 500's return over the same dates.</p>
  <div class="grid2" style="margin-top:16px">
    <div class="panel chart"><h2 style="margin:0 0 4px">Does a higher score mean more winners?</h2>
      <p class="note" style="margin:0 0 8px">Share of stocks that beat the typical stock, grouped by how the model ranked them. 50% = coin flip.</p><div id="calib"></div></div>
    <div class="panel chart"><h2 style="margin:0 0 4px">What the model pays attention to</h2>
      <p class="note" style="margin:0 0 8px" id="importance-note">Share of the model's decisions driven by each input.</p><div id="importance"></div></div>
  </div>
  <h2>Every period</h2>
  <div class="panel scroll"><table id="period-table"></table></div>
</section>

<section id="tab-news" class="hidden">
  <h1>Market news</h1>
  <p class="lede" id="news-lede"></p>
  <input id="q" class="search" type="search" placeholder="Search headlines: Nvidia, Fed, earnings...">
  <div class="chips" id="news-chips"></div>
  <div id="news-list"></div>
</section>

<section id="tab-method" class="hidden"><div class="prose">
  <h1>How it works</h1>
  <p class="lede">A research project, not investment advice. Here is exactly what the numbers mean and where they can mislead.</p>
  <h2>What the model looks at</h2>
  <p>Company financials from SEC filings: how cheap the stock is versus its earnings and book value, gross profitability, return on assets,
  revenue growth and debt. Each number only becomes visible to the model a few months after the period it covers, roughly when it was filed,
  so the model never uses information investors didn't have yet.</p>
  <h2>What it predicts</h2>
  <p>For each holding period, the chance that a stock beats the median S&amp;P 500 stock. Today's picks are the stocks with the highest chance,
  using a model trained on everything up to today.</p>
  <h2>How the track record is made</h2>
  <p>The model is replayed on past dates: each January it is retrained using only outcomes already known, then it makes picks every quarter that year.
  Those picks are compared with buying the S&amp;P 500 on the same day. The stock list on each date is the S&amp;P 500 as it actually was, including
  companies later removed, so failed companies are not quietly left out.</p>
  <p>Results from <span class="holdout"></span> on are deliberately hidden. They are kept for one final, honest check: once a period has been used
  to tune the model, it can no longer tell you whether the model really works.</p>
  <h2>Limits</h2>
  <ul>
    <li>A few hundred past picks is a small sample. A small edge can easily be luck.</li>
    <li>Free price data is missing some companies that were bought out or went bankrupt, especially before 2018.</li>
    <li>The likely range and chance of loss assume the future moves like the recent past. Markets regularly break that assumption.</li>
    <li>No taxes; trading costs are a rough estimate.</li>
  </ul>
</div></section>
</main>
<footer>Educational project. Nothing here is investment advice. Past results do not predict future returns. Data: SEC EDGAR, Yahoo Finance, public RSS feeds.</footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const F = D.forecast;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct = (x, d=1) => x == null ? "–" : (x * 100).toFixed(d) + "%";
const signed = (x, d=1) => x == null ? "–" : (x >= 0 ? "+" : "") + (x * 100).toFixed(d) + "%";
const when = s => new Date(s).toLocaleString(undefined, {month:"short", day:"numeric", hour:"numeric", minute:"2-digit"});

$("stamp").textContent = "Updated " + when(D.built);
document.querySelectorAll(".holdout").forEach(e => e.textContent = F ? F.holdout_from : "");

// ---------- tabs ----------
function show(tab, hash) {
  document.querySelectorAll("main > section").forEach(s => s.classList.toggle("hidden", s.id !== "tab-" + tab));
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  try { history.replaceState(null, "", "#" + (hash || tab)); } catch (e) {}
}
document.querySelectorAll("#nav button").forEach(b => b.onclick = () => show(b.dataset.tab));
const START = location.hash.slice(1).split(":");
show(["picks","live","record","lookup","news","method"].includes(START[0]) ? START[0] : "picks");

// ---------- horizon switch ----------
let H = 1;
function segs(id, render) {
  $(id).innerHTML = F.horizons.map((h, i) => `<button data-i="${i}">${esc(h.label)}</button>`).join("");
  $(id).querySelectorAll("button").forEach(b => b.onclick = () => { H = +b.dataset.i; renderAll(); });
}
function markSegs() { document.querySelectorAll(".seg").forEach(s => s.querySelectorAll("button").forEach(b => b.classList.toggle("on", +b.dataset.i === H))); }

function card(k, v, s) { return `<div class="card"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`; }
function stars(p) { const n = p >= .995 ? 3 : p >= .98 ? 2 : 1; return `<span class="stars">${"★".repeat(n)}<span class="off">${"★".repeat(3-n)}</span></span>`; }

const SIMPLE = F && F.model === "simple";
if (F) $("score-note").textContent = SIMPLE
  ? "how strong the stock's financials are overall: the average of its rank on six measures (cheapness vs earnings and book value, gross profitability, return on assets, revenue growth, low debt) against the other ~500 stocks. 100 = best on everything."
  : "the model's estimated chance this stock beats the typical S&P 500 stock over the period.";

function renderPicks() {
  const h = F.horizons[H], s = h.summary, top = (h.calibration || []).find(c => c.bucket === "Top 20%");
  $("picks-lede").textContent = SIMPLE
    ? `The ${h.picks.length} S&P 500 stocks with the strongest combination of value, profitability, growth and low debt, out of ${h.universe} current members. `
      + `The list is the same for every holding period; the track record and risk numbers change with the period. Prices as of ${F.data_through}.`
    : `The ${h.picks.length} stocks the model rates most likely to beat the typical S&P 500 stock over the next ${h.label}, `
      + `out of ${h.universe} current members. Prices as of ${F.data_through}.`;
  $("pick-cards").innerHTML = s.periods ? [
    card("Backtest record vs S&P 500", `${s.beat_sp500}–${s.periods - s.beat_sp500}`, `Pick sets that beat / trailed the index, ${s.first} to ${s.last}`),
    card("Avg return per period", pct(s.avg_picks), `vs ${pct(s.avg_sp500)} for the S&P 500 and ${pct(s.avg_average_stock)} for the average stock`),
    card("Individual picks", `${s.pick_wins.toLocaleString()}–${s.pick_losses.toLocaleString()}`, `${pct(s.pick_wins / (s.pick_wins + s.pick_losses))} of single picks beat the S&P 500`),
    top ? card("Top-rated hit rate", pct(top.hit_rate), `of top-20% rated stocks beat the typical stock (coin flip = 50%)`) : ""
  ].join("") : "";
  const lo = Math.min(...h.picks.map(p => p.range_low), -0.2), hi = Math.max(...h.picks.map(p => p.range_high), 0.3);
  const X = v => ((v - lo) / (hi - lo) * 100).toFixed(1);
  $("pick-table").innerHTML = `<thead><tr><th>#</th><th>Stock</th><th>Model score</th><th>Conviction</th><th>Likely range (80%)</th>
    <th class="num">Chance of loss</th><th>What stands out</th><th class="num">Price</th></tr></thead><tbody>` +
    h.picks.map(p => `<tr><td>${p.rank}</td>
      <td><a class="tk" href="#lookup:${esc(p.ticker)}" onclick="openStock('${esc(p.ticker)}'); return false;">${esc(p.ticker)}</a><div class="nm" title="${esc(p.name)}">${esc(p.name)}</div></td>
      <td><div class="prob"><div class="track"><div class="fill" style="width:${(p.probability*100).toFixed(0)}%"></div></div><b>${SIMPLE ? Math.round(p.probability * 100) : pct(p.probability, 0)}</b></div></td>
      <td>${stars(p.percentile)}</td>
      <td><div class="range"><div class="axis"></div><div class="span" style="left:${X(p.range_low)}%;width:${X(p.range_high)-X(p.range_low)}%"></div><div class="zero" style="left:${X(0)}%"></div></div>
          <div class="range-txt">${signed(p.range_low,0)} to ${signed(p.range_high,0)}</div></td>
      <td class="num">${pct(p.chance_of_loss,0)}<div class="range-txt">(${p.hist_chance_of_loss == null ? "–" : pct(p.hist_chance_of_loss,0)} in history)</div></td>
      <td>${p.traits.length ? p.traits.map(t => `<span class="chip">${esc(t)}</span>`).join("") : '<span class="nm">Balanced profile</span>'}</td>
      <td class="num">$${p.price.toFixed(2)}</td></tr>`).join("") + "</tbody>";
}

function verdict(s, edge) {
  const share = s.beat_sp500 / s.periods;
  if (Math.abs(edge) < 0.01 && share >= 0.4 && share <= 0.6)
    return card("Did following the picks win?", "About even", "no meaningful difference from just buying the S&P 500");
  const ahead = edge > 0 && share > 0.5;
  return card("Did following the picks win?", ahead ? "Picks ahead" : "Index ahead",
    ahead ? "the picks beat the S&P 500 on average and more often than not" : "simply buying the S&P 500 did as well or better");
}

function renderRecord() {
  const h = F.horizons[H], s = h.summary, P = h.periods;
  $("record-lede").textContent = s.periods
    ? `If you had bought the model's top ${Math.round(F.top_fraction*100)}% of stocks at the start of each quarter and held them for ${h.label}, `
      + `here is how you would have done against simply buying the S&P 500 on the same day. Periods ending in ${F.holdout_from} or later are held back for a final test.`
    : "Not enough history for this holding period yet.";
  const edge = s.periods ? s.avg_picks - s.avg_sp500 : null;
  $("record-cards").innerHTML = s.periods ? [
    card("Beat the S&P 500", `${s.beat_sp500} of ${s.periods}`, `${pct(s.beat_sp500 / s.periods, 0)} of pick sets`),
    card("Average edge per period", `<span class="pill ${edge >= 0 ? "up" : "down"}">${signed(edge)}</span>`, `picks ${pct(s.avg_picks)} vs S&P 500 ${pct(s.avg_sp500)}`),
    card("Beat the average stock", `${s.beat_average_stock} of ${s.periods}`, `the "pick at random" benchmark`),
    verdict(s, edge)
  ].join("") : "";
  // excess-return bars
  const W = 760, Hh = 220, pad = 34, ex = P.map(p => p.picks - p.sp500), m = Math.max(0.05, ...ex.map(Math.abs));
  const y = v => Hh / 2 - v / m * (Hh / 2 - 14), bw = (W - pad) / Math.max(P.length, 1);
  let svg = `<svg viewBox="0 0 ${W} ${Hh + 24}" role="img" aria-label="Excess return per period">`;
  [m, m/2, 0, -m/2, -m].forEach(v => svg += `<line x1="${pad}" x2="${W}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${pad-6}" y="${y(v)+4}" font-size="10" text-anchor="end" fill="var(--muted)">${signed(v,0)}</text>`);
  P.forEach((p, i) => { const v = ex[i], x = pad + i * bw + bw * .15, top = Math.min(y(v), y(0));
    svg += `<rect x="${x}" y="${top}" width="${bw*.7}" height="${Math.max(1, Math.abs(y(v)-y(0)))}" rx="2" fill="${v >= 0 ? "var(--up)" : "var(--down)"}"><title>${p.start} → ${p.end}: picks ${pct(p.picks)}, S&P ${pct(p.sp500)}</title></rect>`;
    if (p.start.endsWith("-01")) svg += `<text x="${x + bw*.35}" y="${Hh + 16}" font-size="10" text-anchor="middle" fill="var(--muted)">${p.start.slice(0,4)}</text>`; });
  $("excess-chart").innerHTML = svg + "</svg>";
  $("calib").innerHTML = (h.calibration || []).map(c => `<div class="hbar"><span>${esc(c.bucket)} rated</span>
    <div class="t"><div class="f" style="width:${(c.hit_rate*100).toFixed(0)}%"></div><div class="mid"></div></div><b class="num">${pct(c.hit_rate,0)}</b></div>`).join("");
  const names = {earnings_yield:"Earnings yield", book_to_market:"Book-to-market", gross_prof:"Gross profitability", roa:"Return on assets", rev_growth:"Revenue growth", leverage:"Debt level"};
  const mx = Math.max(...h.importance.map(i => i.importance));
  $("importance").innerHTML = h.importance.map(i => `<div class="hbar"><span>${esc(names[i.feature] || i.feature)}</span>
    <div class="t"><div class="f" style="width:${(i.importance/mx*100).toFixed(0)}%"></div></div><b class="num">${pct(i.importance,0)}</b></div>`).join("");
  $("period-table").innerHTML = `<thead><tr><th>Bought</th><th>Sold</th><th class="num">Picks</th><th class="num">S&amp;P 500</th><th class="num">Average stock</th><th class="num">Edge vs S&amp;P</th><th class="num">Picks beating S&amp;P</th></tr></thead><tbody>`
    + P.slice().reverse().map(p => { const e = p.picks - p.sp500; return `<tr><td>${p.start}</td><td>${p.end}</td><td class="num">${pct(p.picks)}</td><td class="num">${pct(p.sp500)}</td>
      <td class="num">${pct(p.average_stock)}</td><td class="num"><span class="pill ${e >= 0 ? "up" : "down"}">${signed(e)}</span></td><td class="num">${p.pick_wins} / ${p.pick_count}</td></tr>`; }).join("") + "</tbody>";
}

function renderLive() {
  const L = F.live, h = L && L.horizons.find(x => x.months === F.horizons[H].months);
  if (!h) {
    $("live-lede").textContent = "The live record starts with the next morning update: from then on, every day's picks are saved and scored here.";
    ["live-cards", "first-table", "cohort-table"].forEach(id => $(id).innerHTML = ""); $("first-title").textContent = "";
    return;
  }
  const start = new Date(L.started + "T12:00:00"), firstClose = new Date(start); firstClose.setMonth(firstClose.getMonth() + h.months);
  const fmt = d => d.toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"});
  $("live-lede").textContent = `Real picks, made before the results were known. Started ${fmt(start)}: every morning's top ${F.horizons[H].picks.length} `
    + `${h.label} picks are saved permanently and compared with buying the S&P 500 on the same day.`;
  const edge = h.avg_ret - h.avg_sp_ret;
  $("live-cards").innerHTML = [
    card("Finished picks vs S&P 500", h.closed ? `${h.closed_wins}–${h.closed_losses}` : "None yet",
         h.closed ? `${pct(h.closed_wins / h.closed, 0)} beat the index over the full ${h.label}` : `first ${h.label} picks finish ${fmt(firstClose)}`),
    card("Open picks beating the S&P now", `${h.open_beating} of ${h.open}`, "since the day each was picked"),
    card("Average return since picked", pct(h.avg_ret), `vs ${pct(h.avg_sp_ret)} for the S&P 500 over the same days`),
    card("Edge so far", `<span class="pill ${edge >= 0 ? "up" : "down"}">${signed(edge)}</span>`, `across ${h.picks.toLocaleString()} recorded picks (repeats count each day)`)
  ].join("");
  $("first-title").textContent = `The first ${h.label} picks (${fmt(start)})`;
  $("first-table").innerHTML = `<thead><tr><th>Stock</th><th class="num">Price then</th><th class="num">Price now</th><th class="num">Return</th><th class="num">S&amp;P 500</th><th class="num">vs S&amp;P</th></tr></thead><tbody>`
    + h.first_picks.map(p => { const e = p.ret - p.sp_ret; return `<tr><td class="tk">${esc(p.ticker)}</td><td class="num">$${p.price.toFixed(2)}</td><td class="num">$${p.now.toFixed(2)}</td>
      <td class="num">${signed(p.ret)}</td><td class="num">${signed(p.sp_ret)}</td><td class="num"><span class="pill ${e >= 0 ? "up" : "down"}">${signed(e)}</span></td></tr>`; }).join("") + "</tbody>";
  $("cohort-table").innerHTML = `<thead><tr><th>Picked</th><th>Top picks</th><th class="num">Return</th><th class="num">S&amp;P 500</th><th class="num">Edge</th><th class="num">Beating S&amp;P</th><th>Status</th></tr></thead><tbody>`
    + h.cohorts.map(c => { const e = c.ret - c.sp_ret; return `<tr><td style="white-space:nowrap">${c.date}</td><td class="nm">${esc(c.tickers)}</td><td class="num">${signed(c.ret)}</td><td class="num">${signed(c.sp_ret)}</td>
      <td class="num"><span class="pill ${e >= 0 ? "up" : "down"}">${signed(e)}</span></td><td class="num">${c.beat} / ${c.n}</td><td>${c.closed ? "Final" : "Open"}</td></tr>`; }).join("") + "</tbody>";
}

if (SIMPLE) $("importance-note").textContent = "The simple score weighs all six measures equally.";

// ---------- stock lookup ----------
const S = (F && F.stocks) || [], MEASURES = [
  ["earnings_yield", "Cheap vs. earnings"], ["book_to_market", "Cheap vs. book value"], ["gross_prof", "Gross profitability"],
  ["roa", "Return on assets"], ["rev_growth", "Revenue growth"], ["leverage", "Low debt"]];
let picked = null, industry = "";
const hz = st => st.horizons.find(x => x.months === F.horizons[H].months) || st.horizons[0];
const scoreTxt = v => SIMPLE ? String(Math.round(v * 100)) : pct(v, 0);
const topTxt = p => p >= .5 ? `Top ${Math.max(1, Math.round((1 - p) * 100))}%` : `Bottom ${Math.max(1, Math.round(p * 100))}%`;

function openStock(t) {
  picked = S.find(s => s.ticker === t) || null; show("lookup", picked ? "lookup:" + t : "lookup");
  renderLookup(); window.scrollTo({top: 0, behavior: "smooth"});
}
function renderDetail() {
  const st = picked;
  if (!st) { $("stock-detail").innerHTML = ""; return; }
  const h = hz(st), n = S.length, inPicks = h.rank <= F.horizons[H].picks.length;
  $("stock-detail").innerHTML = `<div class="detail">
    <div class="detail-head"><span class="big">${esc(st.ticker)}</span><span class="co">${esc(st.name)}</span>
      ${inPicks ? `<span class="badge">In today's top ${F.horizons[H].picks.length}</span>` : ""}
      <button class="x" onclick="picked=null; show('lookup'); renderLookup()">Close</button></div>
    <div class="nm" style="max-width:none">${esc(st.industry)} · $${st.price.toFixed(2)} · ${st.ret_1y == null ? "" : signed(st.ret_1y) + " over the past year"}</div>
    <div class="cards">
      ${card("Rank today", `#${h.rank} <span style="font-size:14px;color:var(--muted);font-weight:500">of ${n}</span>`, `${topTxt(h.percentile)} of current S&P 500 members`)}
      ${card("Model score", scoreTxt(h.score), SIMPLE ? "0–100, average rank on the six measures" : `chance of beating the typical stock over ${F.horizons[H].label}`)}
      ${card(`Likely range, ${F.horizons[H].label}`, `${signed(h.range_low, 0)} to ${signed(h.range_high, 0)}`, "8 in 10 outcomes, from its last 3 years of swings")}
      ${card("Chance of loss", pct(h.chance_of_loss, 0), h.hist_chance_of_loss == null ? "not enough history" : `${pct(h.hist_chance_of_loss, 0)} of past ${F.horizons[H].label} periods lost money`)}
    </div>
    <h3>How it compares on each measure</h3>
    ${MEASURES.map(([k, label]) => { const v = st.measures[k]; return `<div class="hbar"><span>${label}</span>
      <div class="t">${v == null ? "" : `<div class="f" style="width:${(v*100).toFixed(0)}%"></div>`}<div class="mid"></div></div>
      <b class="num">${v == null ? "n/a" : topTxt(v)}</b></div>`; }).join("")}
    <p class="note" style="margin-top:4px">The middle line is the typical S&P 500 stock. n/a = not reported in its SEC filings.</p>
    ${st.traits.length ? `<h3>What stands out</h3>${st.traits.map(t => `<span class="chip">${esc(t)}</span>`).join("")}` : ""}
  </div>`;
}
function renderLookup() {
  if (!S.length) { $("lookup-lede").textContent = "The stock list appears after the next morning update."; return; }
  $("lookup-lede").textContent = `Every current S&P 500 member, ranked by today's model score for the chosen holding period. `
    + `Search for a stock or click any row to see why it ranks where it does.`;
  renderDetail();
  const q = $("lq").value.trim().toLowerCase();
  const rows = S.filter(st => (!industry || st.industry === industry)
    && (!q || st.ticker.toLowerCase().startsWith(q) || st.name.toLowerCase().includes(q) || st.industry.toLowerCase().includes(q)))
    .map(st => [st, hz(st)]).sort((a, b) => a[1].rank - b[1].rank);
  $("stock-table").innerHTML = `<thead><tr><th class="num">Rank</th><th>Stock</th><th>Industry</th><th>Model score</th><th class="num">Chance of loss</th>
    <th class="num">Past year</th><th class="num">Price</th></tr></thead><tbody>` + rows.slice(0, 600).map(([st, h]) =>
    `<tr class="clickable" onclick="openStock('${esc(st.ticker)}')"><td class="num">${h.rank}</td>
      <td><div class="tk">${esc(st.ticker)}</div><div class="nm" title="${esc(st.name)}">${esc(st.name)}</div></td>
      <td class="nm">${esc(st.industry)}</td>
      <td><div class="prob"><div class="track"><div class="fill" style="width:${(h.score*100).toFixed(0)}%"></div></div><b>${scoreTxt(h.score)}</b></div></td>
      <td class="num">${pct(h.chance_of_loss, 0)}</td><td class="num">${signed(st.ret_1y, 0)}</td><td class="num">$${st.price.toFixed(2)}</td></tr>`).join("") + "</tbody>";
  $("stock-count").textContent = rows.length ? `${rows.length} of ${S.length} stocks shown.` : "No stocks match.";
}
if (S.length) {
  const inds = [...new Set(S.map(s => s.industry))].sort();
  $("lookup-filters").innerHTML = inds.map(i => `<button class="fchip" data-i="${esc(i)}">${esc(i)}</button>`).join("");
  $("lookup-filters").querySelectorAll(".fchip").forEach(c => c.onclick = () => {
    industry = industry === c.dataset.i ? "" : c.dataset.i;
    $("lookup-filters").querySelectorAll(".fchip").forEach(x => x.classList.toggle("on", x.dataset.i === industry)); renderLookup(); });
  $("lq").oninput = renderLookup;
  $("lq").onkeydown = e => { if (e.key === "Enter") { const q = $("lq").value.trim().toUpperCase(),
    hit = S.find(s => s.ticker === q) || S.find(s => s.ticker.startsWith(q) || s.name.toUpperCase().includes(q)); if (hit) openStock(hit.ticker); } };
  if (START[0] === "lookup" && START[1]) picked = S.find(s => s.ticker === START[1].toUpperCase()) || null;
}
window.addEventListener("hashchange", () => { const [tab, t] = location.hash.slice(1).split(":");
  if (tab === "lookup" && t) openStock(t.toUpperCase()); });

function renderAll() { markSegs(); renderPicks(); renderLive(); renderRecord(); renderLookup(); }

if (F) {
  if (F.demo) $("picks-warn").innerHTML = '<div class="warn">Demo data: these picks and results are made up for testing.</div>';
  H = Math.max(0, F.horizons.findIndex(h => h.months === 12));
  segs("seg-picks"); segs("seg-live"); segs("seg-record"); segs("seg-lookup"); renderAll();
} else {
  $("picks-lede").textContent = "No picks yet. Run python forecast.py, then python dashboard.py.";
}

// ---------- news ----------
const N = D.news, latest = N.reduce((m, r) => r.seen > m ? r.seen : m, "");
$("news-lede").textContent = `${N.length} headlines from the last few days across ${new Set(N.map(r => r.source.split(":")[0])).size} sources, newest first.`;
const srcs = [...new Set(N.map(r => r.source.split(":")[0]))].sort(), on = new Set();
$("news-chips").innerHTML = srcs.map(s => `<button class="fchip" data-s="${esc(s)}">${esc(s)}</button>`).join("");
function renderNews() {
  const q = $("q").value.toLowerCase(); let day = "", out = [];
  N.filter(r => (!on.size || on.has(r.source.split(":")[0])) && (r.title + " " + r.summary + " " + r.source).toLowerCase().includes(q)).slice(0, 400).forEach(r => {
    const d = new Date(r.t), dl = d.toLocaleDateString(undefined, {weekday:"long", month:"long", day:"numeric"});
    if (dl !== day) { day = dl; out.push(`<div class="day">${dl}</div>`); }
    const safe = /^https?:/.test(r.link) ? r.link : "#";
    out.push(`<div class="story"><div class="meta">${d.toLocaleTimeString(undefined, {hour:"numeric", minute:"2-digit"})} · ${esc(r.source)}${r.seen === latest ? ' · <span class="new">New</span>' : ""}</div>
      <a href="${esc(safe)}" target="_blank" rel="noopener">${esc(r.title)}</a>${r.summary ? `<p>${esc(r.summary)}</p>` : ""}</div>`);
  });
  $("news-list").innerHTML = out.join("") || '<p class="note">No headlines match.</p>';
}
$("q").oninput = renderNews;
document.querySelectorAll(".fchip").forEach(c => c.onclick = () => { on.has(c.dataset.s) ? on.delete(c.dataset.s) : on.add(c.dataset.s); c.classList.toggle("on"); renderNews(); });
renderNews();
</script>
</body></html>
"""


if __name__ == "__main__":
    print("Saved", build())
