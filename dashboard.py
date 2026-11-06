"""Build the website (outputs/site/index.html) from the latest picks and headlines:  python dashboard.py

Reads outputs/forecast.json (made by forecast.py) and data/news/headlines.csv (made by news.py).
Everything is embedded in one self-contained page, so it works from GitHub Pages or straight from disk.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import config
import news
import newsmatch

SITE_DIR = os.path.join(config.OUTPUT_DIR, "site")
PAGE = os.path.join(SITE_DIR, "index.html")
FORECAST = os.path.join(config.OUTPUT_DIR, "forecast.json")


def _recent_news(forecast):
    """(headlines for the news page, headlines about S&P 500 companies for each stock), newest first.
    Each headline carries 'tk': the tickers it is about (newsmatch.py)."""
    now = datetime.now(timezone.utc)
    page_from, stock_from = now - timedelta(days=config.NEWS_PAGE_DAYS), now - timedelta(days=config.STOCK_NEWS_DAYS)
    rows = []
    for r in news.load_archive():
        pub = news._parse_date(r["published"])
        if pub and pub >= min(page_from, stock_from):
            rows.append({"t": pub.isoformat(), "source": r["source"], "title": r["title"],
                         "link": r["link"], "summary": r["summary"], "seen": r["first_seen"], "pub": pub})
    rows.sort(key=lambda r: r["t"], reverse=True)
    stocks = (forecast or {}).get("stocks") or []
    for r, tk in zip(rows, newsmatch.tag(rows, stocks) if stocks else [[] for _ in rows]):
        r["tk"] = tk
    page = [{k: v for k, v in r.items() if k != "pub"} for r in rows if r["pub"] >= page_from]
    tagged = [{"t": r["t"], "source": r["source"], "title": r["title"], "link": r["link"], "tk": r["tk"]}
              for r in rows if r["tk"] and r["pub"] >= stock_from]
    return page, tagged


def build():
    forecast = None
    if os.path.exists(FORECAST):
        with open(FORECAST) as f:
            forecast = json.load(f)
    page, tagged = _recent_news(forecast)
    payload = {"forecast": forecast, "news": page, "stock_news": tagged,
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
<meta name="description" content="Daily S&amp;P 500 stock picks from company financials, with an honest backtest, a live track record, stock lookup and market news.">
<meta name="theme-color" content="#0f2a1f">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 34 34'%3E%3Ccircle cx='17' cy='17' r='16.5' fill='%230f2a1f'/%3E%3Ccircle cx='17' cy='17' r='14' fill='none' stroke='%23b08d57' stroke-width='1.6'/%3E%3Ctext x='17' y='24' text-anchor='middle' font-family='Georgia,serif' font-size='19' font-weight='700' fill='%23b08d57'%3EB%3C/text%3E%3C/svg%3E">
<script>try { const t = localStorage.getItem("theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f8f6f0; --panel:#fffdf8; --text:#14231b; --muted:#5d6a61; --line:#e3ddcf; --soft:#f1ede2;
  --brand:#0f2a1f; --brand-text:#f8f6f0; --brand-2:#8a6a35; --up:#1f7a45; --up-bg:#e0f0e4; --down:#a8322d; --down-bg:#f8e3df;
  --gold:#b08d57; --bar:#b08d57; --bar-2:#b9b3a3; --head:#0f2a1f; --head-text:#d5e0d8; --logo:#b08d57; --logo-ink:#0f2a1f;
  --shadow:0 1px 2px rgba(15,42,31,.05), 0 1px 3px rgba(15,42,31,.08);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#0b1510; --panel:#122019; --text:#e8eee9; --muted:#9aa99f; --line:#1f3429; --soft:#0f1c15;
  --brand:#c9a46a; --brand-text:#0b1510; --brand-2:#d6b781; --up:#5fcf8a; --up-bg:#0d2b1a; --down:#f08a80; --down-bg:#3a1512;
  --gold:#c9a46a; --bar:#c9a46a; --bar-2:#3d4f44; --head:#071009; --head-text:#cfdcd3; --logo:#c9a46a; --logo-ink:#071009; --shadow:none; } }
:root[data-theme="dark"] {
  --bg:#0b1510; --panel:#122019; --text:#e8eee9; --muted:#9aa99f; --line:#1f3429; --soft:#0f1c15;
  --brand:#c9a46a; --brand-text:#0b1510; --brand-2:#d6b781; --up:#5fcf8a; --up-bg:#0d2b1a; --down:#f08a80; --down-bg:#3a1512;
  --gold:#c9a46a; --bar:#c9a46a; --bar-2:#3d4f44; --head:#071009; --head-text:#cfdcd3; --logo:#c9a46a; --logo-ink:#071009; --shadow:none; }
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--text);
  font:14px/1.5 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-feature-settings:"tnum"; }
a { color:var(--brand-2); }
header { background:var(--head); color:var(--head-text); position:sticky; top:0; z-index:5; }
.bar { max-width:1180px; margin:0 auto; padding:0 16px; display:flex; align-items:center; gap:28px; min-height:64px; flex-wrap:wrap; }
header { border-bottom:1px solid rgba(176,141,87,.45); }
.logo { display:flex; align-items:center; gap:11px; color:#fff; }
.logo svg { width:30px; height:30px; flex:none; }
.logo .wm { font-family:"Source Serif 4", Georgia, serif; font-weight:700; font-size:18px; letter-spacing:-.01em; line-height:1.1; display:block; }
.logo .sub { display:block; font-size:10px; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--logo); margin-top:2px; }
nav { display:flex; gap:2px; flex-wrap:wrap; align-self:stretch; }
nav button { background:none; border:0; color:var(--head-text); font:inherit; font-weight:500; padding:0 12px; min-height:64px; cursor:pointer; opacity:.72; box-shadow:inset 0 -2px 0 transparent; transition:opacity .15s, box-shadow .15s; }
nav button:hover { opacity:1; }
nav button.on { opacity:1; color:#fff; box-shadow:inset 0 -2px 0 var(--logo); }
.hright { margin-left:auto; display:flex; align-items:center; gap:14px; }
.stamp { font-size:12px; opacity:.7; white-space:nowrap; }
.theme { background:none; border:1px solid rgba(255,255,255,.18); color:var(--head-text); border-radius:6px; width:32px; height:30px; cursor:pointer; font-size:14px; line-height:1; }
.theme:hover { border-color:var(--logo); }
.eyebrow { font-size:11px; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--brand-2); margin:6px 0; }
.strip { display:grid; grid-template-columns:repeat(auto-fit, minmax(128px, 1fr)); background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); margin:0 0 18px; overflow:hidden; }
.strip > div { padding:12px 16px; border-left:1px solid var(--line); margin-left:-1px; }
.strip .k { font-size:11px; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.06em; }
.strip .v { font-size:17px; font-weight:600; margin-top:2px; }
tbody tr:hover td { background:var(--soft); }
.more-chip { color:var(--muted); font-size:11px; white-space:nowrap; }
.hl { max-width:260px; min-width:180px; }
.hl a { color:var(--text); text-decoration:none; font-size:13px; font-weight:500; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.35; }
.hl a:hover { color:var(--brand-2); text-decoration:underline; }
.hl .when { font-size:11px; color:var(--muted); margin-top:2px; white-space:nowrap; }
.newslist { list-style:none; margin:4px 0 0; padding:0; }
.newslist li { padding:8px 0; border-bottom:1px solid var(--line); }
.newslist li:last-child { border-bottom:0; }
.newslist a { color:var(--text); font-weight:500; text-decoration:none; } .newslist a:hover { color:var(--brand-2); text-decoration:underline; }
.tkchip { display:inline-block; font-size:11px; font-weight:700; letter-spacing:.03em; padding:1px 7px; border-radius:4px; margin:6px 4px 0 0; background:var(--soft); border:1px solid var(--line); color:var(--brand-2); cursor:pointer; }
.tkchip:hover { border-color:var(--gold); }
.offical { font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--brand-text); background:var(--brand); border-radius:4px; padding:1px 6px; margin-left:6px; vertical-align:1px; }
#versions-table td.desc { color:var(--muted); font-size:12px; min-width:220px; white-space:normal; }
.tkchip.held { background:var(--brand); color:var(--brand-text); border-color:var(--brand); }
.foot { display:grid; grid-template-columns:2fr 1fr 1fr; gap:24px; border-top:1px solid var(--line); padding-top:22px; }
.foot h4 { margin:0 0 6px; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--text); }
.foot p { margin:0 0 4px; } .foot a { color:var(--muted); }
.foot .wm { font-family:"Source Serif 4", Georgia, serif; font-weight:700; font-size:15px; color:var(--text); margin-bottom:6px; }
main { max-width:1180px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-family:"Source Serif 4", Georgia, serif; font-size:32px; font-weight:700; letter-spacing:-.015em; line-height:1.15; margin:0 0 8px; }
h2 { font-family:"Source Serif 4", Georgia, serif; font-size:19px; font-weight:600; margin:30px 0 10px; }
.lede { color:var(--muted); margin:0 0 20px; max-width:760px; }
.seg { display:inline-flex; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:3px; margin-bottom:18px; box-shadow:var(--shadow); }
.seg button { border:0; background:none; font:inherit; font-weight:600; color:var(--muted); padding:7px 16px; border-radius:6px; cursor:pointer; }
.seg button.on { background:var(--brand); color:var(--brand-text); }
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(175px, 1fr)); gap:12px; margin-bottom:20px; }
.card { background:var(--panel); border:1px solid var(--line); border-top:2px solid var(--gold); border-radius:10px; padding:14px 16px; box-shadow:var(--shadow); }
.card .k { font-size:12px; color:var(--muted); font-weight:500; text-transform:uppercase; letter-spacing:.04em; }
.card .v { font-size:26px; font-weight:700; letter-spacing:-.02em; margin:4px 0 2px; }
.card .s { font-size:12px; color:var(--muted); }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); overflow:hidden; }
.scroll { overflow-x:auto; }
table { width:100%; border-collapse:collapse; }
th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); font-weight:600; padding:10px 12px; border-bottom:1px solid var(--line); background:var(--soft); white-space:nowrap; }
td { padding:11px 12px; border-bottom:1px solid var(--line); vertical-align:middle; }
#period-table td { white-space:nowrap; }
tr:last-child td { border-bottom:0; }
.num { text-align:right; white-space:nowrap; }
.tk { font-weight:700; letter-spacing:.02em; }
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
footer { max-width:1180px; margin:0 auto; padding:0 16px 40px; color:var(--muted); font-size:12px; line-height:1.6; }
.hidden { display:none !important; }
:root { --mix-port:#b08d57; --mix-sp:#1f5c43; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --mix-port:#c9a46a; --mix-sp:#6f8a7c; } }
:root[data-theme="dark"] { --mix-port:#c9a46a; --mix-sp:#6f8a7c; }
.mix { position:relative; }
.mixrow { display:grid; grid-template-columns:190px 1fr 150px; align-items:center; gap:14px; padding:7px 6px; border-radius:6px; cursor:default; outline:none; }
.mixrow:hover, .mixrow:focus-visible { background:var(--soft); }
.mixrow .lab { font-size:13px; font-weight:500; }
.mixrow .lab small { display:block; color:var(--muted); font-weight:400; font-size:11px; }
.mixbars { display:flex; flex-direction:column; gap:2px; }
.mixbars i { display:block; height:8px; border-radius:0 4px 4px 0; min-width:2px; }
.mixbars .p { background:var(--mix-port); } .mixbars .s { background:var(--mix-sp); }
.mixval { text-align:right; font-size:13px; white-space:nowrap; }
.mixval b { font-weight:600; } .mixval span { color:var(--muted); }
.mixval em { font-style:normal; font-size:11px; display:block; }
.legend i.p { background:var(--mix-port); } .legend i.s { background:var(--mix-sp); }
.tip { position:absolute; z-index:3; pointer-events:none; background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:0 4px 14px rgba(0,0,0,.12); padding:10px 12px; font-size:12px; min-width:200px; max-width:260px; }
.tip b { font-size:13px; } .tip .r { display:flex; justify-content:space-between; gap:12px; margin-top:3px; }
.tip .sw { display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:6px; }
@media (max-width:640px) { .mixrow { grid-template-columns:110px 1fr 92px; gap:8px; } .mixval em { display:none; } }
.clickable { cursor:pointer; }
.share { display:flex; align-items:center; gap:8px; justify-content:flex-end; min-width:110px; }
.share .track { width:60px; height:6px; background:var(--soft); border-radius:3px; overflow:hidden; border:1px solid var(--line); }
.share .fill { height:100%; background:var(--brand); }
.more { margin:12px 0 0; border:1px solid var(--line); background:var(--panel); color:var(--text); font:inherit; font-weight:600; padding:8px 16px; border-radius:8px; cursor:pointer; box-shadow:var(--shadow); }
.more:hover { border-color:var(--gold); }
.clickable:hover td { background:var(--soft); }
a.tk { color:inherit; text-decoration:none; } a.tk:hover { color:var(--brand-2); text-decoration:underline; }
.detail { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:18px 20px; margin:16px 0 20px; box-shadow:var(--shadow); }
.detail-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 14px; margin-bottom:4px; }
.detail-head .big { font-size:26px; font-weight:700; letter-spacing:-.02em; }
.detail-head .co { font-size:16px; font-weight:600; }
.detail-head .x { margin-left:auto; background:none; border:1px solid var(--line); border-radius:6px; color:var(--muted); font:inherit; padding:3px 10px; cursor:pointer; }
.badge { display:inline-block; font-size:12px; font-weight:600; padding:3px 10px; border-radius:999px; background:var(--brand); color:var(--brand-text); }
.detail .cards { margin:14px 0 6px; }
.chev { color:var(--muted); width:28px; text-align:center; font-size:12px; transition:transform .15s; display:inline-block; }
tr.open .chev { transform:rotate(90deg); color:var(--brand-2); }
tr.open td { background:var(--soft); border-bottom-color:transparent; }
tr.drop > td { padding:0 12px 14px; background:var(--soft); white-space:normal; }
tr.drop .detail { margin:0; position:sticky; left:12px; box-sizing:border-box; }
.why { font-size:15px; line-height:1.6; margin:10px 0 4px; max-width:820px; }
.why b { color:var(--text); }
.mdesc { font-size:12px; color:var(--muted); margin:-4px 0 8px 0; }
.hbar.big { grid-template-columns:170px 1fr 92px; }
.detail .grid2 { gap:8px 28px; }
.detail ul { margin:6px 0 0; padding-left:18px; } .detail li { margin:3px 0; }
.detail h3 { font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:16px 0 6px; }
@media (max-width:1060px) { .bar { padding-top:10px; gap:0 20px; } nav { order:3; width:100%; margin:0 -12px; } nav button { min-height:44px; } .hright { order:2; } }
@media (max-width:640px) { .hright { position:absolute; top:14px; right:16px; } .stamp { display:none; } .bar { gap:4px; padding-top:10px; position:relative; }
  nav button { min-height:44px; padding:0 10px; } h1 { font-size:26px; } .foot { grid-template-columns:1fr; } .hbar { grid-template-columns:110px 1fr 46px; } }
</style></head>
<body>
<header><div class="bar">
  <div class="logo"><svg viewBox="0 0 34 34" fill="none" aria-hidden="true"><circle cx="17" cy="17" r="15.6" stroke="var(--logo)" stroke-width="1.5"/><circle cx="17" cy="17" r="12.6" stroke="var(--logo)" stroke-width=".7"/><text x="17" y="23.6" text-anchor="middle" font-family="'Source Serif 4', Georgia, serif" font-size="18" font-weight="700" fill="var(--logo)">B</text></svg><span><span class="wm">Bhrugu&rsquo;s Stock Model</span><span class="sub">S&amp;P 500 research</span></span></div>
  <nav id="nav">
    <button data-tab="picks">Today's picks</button><button data-tab="live">Live record</button><button data-tab="record">Backtest</button>
    <button data-tab="lookup">Stock lookup</button>    <button data-tab="news">Market news</button><button data-tab="method">How it works</button>
  </nav>
  <div class="hright"><div class="stamp" id="stamp"></div><button class="theme" id="theme" title="Switch light / dark" aria-label="Switch light or dark theme">◐</button></div>
</div></header>

<main>
<section id="tab-picks">
  <div class="eyebrow">Portfolio · updated every morning</div>
  <h1>Today's picks</h1>
  <p class="lede" id="picks-lede"></p>
  <div id="picks-warn"></div>
  <div class="strip" id="pick-strip"></div>
  <div class="seg" id="seg-picks"></div>
  <div class="cards" id="pick-cards"></div>
  <div class="panel scroll"><table id="pick-table"></table></div>
  <button class="more" id="pick-more"></button>
  <p class="note"><b>Share</b>: how much of the portfolio goes in each stock. The model holds the top 20% of stocks by score, each in proportion to its company's market value, the same way the S&amp;P 500 is built; so the biggest companies get the biggest share.
  <b>Model score</b>: <span id="score-note"></span>
  <b>Likely range</b>: where 8 out of 10 outcomes would land if the stock moves as much as it has over the last 3 years (assumes the market's long-run ~8% yearly return).
  <b>Chance of loss</b>: probability of ending the period below today's price, from the same assumption; in brackets, how often this stock actually lost money over periods this long since 2010.</p>
  <div id="mix-wrap" class="hidden">
  <h2>Industry mix</h2>
  <p class="note" id="mix-lede" style="margin:0 0 10px"></p>
  <div class="panel chart mix">
    <div class="legend"><span><i class="p"></i>Portfolio</span><span><i class="s"></i>S&amp;P 500 (by company value)</span></div>
    <div id="mix" role="table" aria-label="Share of the portfolio and of the S&P 500 in each industry"></div>
    <div class="tip hidden" id="mix-tip" role="status"></div>
  </div>
  <p class="note">Industries come from each company's SEC classification code, which can be broad (Alphabet and Meta count as software, Amazon as retail, medical devices as manufacturing).</p>
  </div>
</section>

<section id="tab-live" class="hidden">
  <div class="eyebrow">Real-time track record</div>
  <h1>Live record</h1>
  <p class="lede" id="live-lede"></p>
  <div class="seg" id="seg-live"></div>
  <div class="cards" id="live-cards"></div>
  <div id="versions-wrap" class="hidden">
    <h2>Alternative versions, tracked side by side</h2>
    <p class="note" id="versions-lede" style="margin:0 0 10px"></p>
    <div class="panel scroll"><table id="versions-table"></table></div>
  </div>
  <h2 id="first-title"></h2>
  <div class="panel scroll"><table id="first-table"></table></div>
  <h2>Every day's picks</h2>
  <div class="panel scroll"><table id="cohort-table"></table></div>
  <p class="note">Each row is one morning's picks for this holding period, scored from that day's closing price. A pick stays <b>open</b>
  until its holding period ends; then its result is <b>final</b> and never changes. The record is saved on GitHub, where every change is dated.</p>
</section>

<section id="tab-lookup" class="hidden">
  <div class="eyebrow">Research every S&amp;P 500 stock</div>
  <h1>Stock lookup</h1>
  <p class="lede" id="lookup-lede"></p>
  <input id="lq" class="search" type="search" placeholder="Search by ticker or company: AAPL, Nvidia, bank..." autocomplete="off">
  <div class="chips" id="lookup-filters"></div>
  <div class="seg" id="seg-lookup"></div>
  <div class="panel scroll"><table id="stock-table"></table></div>
  <p class="note" id="stock-count"></p>
</section>

<section id="tab-record" class="hidden">
  <div class="eyebrow">Historical replay, 2016–2022</div>
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
  <div class="eyebrow">Updated every hour</div>
  <h1>Market news</h1>
  <p class="lede" id="news-lede"></p>
  <input id="q" class="search" type="search" placeholder="Search headlines: Nvidia, Fed, earnings...">
  <div class="chips"><button class="fchip" id="held-only">Only stocks in the portfolio</button></div>
  <div class="chips" id="news-chips"></div>
  <div id="news-list"></div>
</section>

<section id="tab-method" class="hidden"><div class="prose">
  <div class="eyebrow">Methodology</div>
  <h1>How it works</h1>
  <p class="lede">A research project, not investment advice. Here is exactly what the numbers mean and where they can mislead.</p>
  <h2>What the model looks at</h2>
  <p>Company financials from SEC filings: how cheap the stock is versus its earnings and book value, gross profitability, return on assets,
  revenue growth and debt. Each number only becomes visible to the model a few months after the period it covers, roughly when it was filed,
  so the model never uses information investors didn't have yet.</p>
  <h2>How the picks are made</h2>
  <p>Each stock gets a score: the average of its rank on the six measures. The portfolio is the top 20% of stocks by score, about 100 companies,
  each held in proportion to its market value, like the S&amp;P 500 itself. So the model is the S&amp;P 500 with its weaker-scoring 80% removed.
  This means a few giant companies make up most of the money: check the Share column.</p>
  <h2>Alternative versions</h2>
  <p>Next to the official picks, every morning also saves the portfolios of a few alternative designs: one that caps any single stock at 10%,
  one that puts the same amount in each stock, and one that adds 12-month price momentum. They are never used for the official picks.
  Because their picks are saved before the results are known, comparing them over the next 6 to 12 months is a fair test of which design
  works, with no chance of tuning it to past data.</p>
  <h2>How the track record is made</h2>
  <p>The model is replayed on past dates: each January it is retrained using only outcomes already known, then it makes picks every quarter that year.
  Those picks are compared with buying the S&amp;P 500 on the same day. The stock list on each date is the S&amp;P 500 as it actually was, including
  companies later removed, so failed companies are not quietly left out.</p>
  <p>The backtest covers picks made up to <span class="holdout"></span>. Weighting by company value was adopted in November 2026 after reviewing
  results through 2026, so every past year has now been used to shape the model. That is why the live record matters most: it is the only
  test of picks made before anyone knew the results.</p>
  <h2>Limits</h2>
  <ul>
    <li>A few hundred past picks is a small sample. A small edge can easily be luck.</li>
    <li>The portfolio is concentrated: the largest handful of holdings decide most of the result.</li>
    <li>Free price data is missing some companies that were bought out or went bankrupt, especially before 2018.</li>
    <li>The likely range and chance of loss assume the future moves like the recent past. Markets regularly break that assumption.</li>
    <li>No taxes; trading costs are a rough estimate.</li>
  </ul>
</div></section>
</main>
<footer><div class="foot">
  <div><div class="wm"><svg viewBox="0 0 34 34" width="20" height="20" fill="none" aria-hidden="true" style="vertical-align:-4px;margin-right:6px"><circle cx="17" cy="17" r="15.6" stroke="var(--gold)" stroke-width="1.8"/><text x="17" y="23.6" text-anchor="middle" font-family="'Source Serif 4', Georgia, serif" font-size="18" font-weight="700" fill="var(--gold)">B</text></svg>Bhrugu&rsquo;s Stock Model</div><p>An educational research project. Nothing here is investment advice, and past results do not predict future returns.
  Picks are not recommendations to buy or sell any security.</p></div>
  <div><h4>Data</h4><p>Company financials: SEC EDGAR</p><p>Prices: Yahoo Finance</p><p>News: public RSS feeds</p></div>
  <div><h4>Updates</h4><p>Picks: every weekday morning</p><p>News: hourly, 7 AM–8 PM ET</p><p><a href="https://github.com/bhrugu1203/stock-model" target="_blank" rel="noopener">Source code on GitHub</a></p></div>
</div></footer>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const F = D.forecast;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct = (x, d=1) => x == null ? "–" : (x * 100).toFixed(d) + "%";
const signed = (x, d=1) => x == null ? "–" : (x >= 0 ? "+" : "") + (x * 100).toFixed(d) + "%";
const when = s => new Date(s).toLocaleString(undefined, {month:"short", day:"numeric", hour:"numeric", minute:"2-digit"});
const ago = s => { const m = (Date.now() - new Date(s)) / 60000;
  return m < 60 ? `${Math.max(1, Math.round(m))}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`; };
const safeUrl = u => /^https?:/.test(u) ? u : "#";
const NEWS_BY = {};
(D.stock_news || []).forEach(n => n.tk.forEach(t => (NEWS_BY[t] = NEWS_BY[t] || []).push(n)));
const HELD = new Set(F ? F.horizons[0].picks.map(p => p.ticker) : []);
function latestNews(t) {
  const n = NEWS_BY[t] || [];
  if (!n.length) return '<span class="nm">No recent headlines</span>';
  return `<div class="hl"><a href="${esc(safeUrl(n[0].link))}" target="_blank" rel="noopener" title="${esc(n[0].title)}">${esc(n[0].title)}</a>
    <div class="when">${ago(n[0].t)} · ${esc(n[0].source.replace(/^Google News: /, ""))}${n.length > 1 ? ` · <a class="more-chip" href="#lookup:${esc(t)}" onclick="openStock('${esc(t)}'); return false;" style="display:inline;font-weight:400">+${n.length - 1} more</a>` : ""}</div></div>`;
}

$("stamp").textContent = "Updated " + when(D.built);
$("theme").onclick = () => {
  const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("theme", document.documentElement.dataset.theme); } catch (e) {}
};
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

const SIMPLE = F && F.model === "simple", SIZED = F && F.weighting === "size";
let showAll = false;
if (F) $("score-note").textContent = SIMPLE
  ? "how strong the stock's financials are overall: the average of its rank on six measures (cheapness vs earnings and book value, gross profitability, return on assets, revenue growth, low debt) against the other ~500 stocks. 100 = best on everything."
  : "the model's estimated chance this stock beats the typical S&P 500 stock over the period.";

function renderPicks() {
  const h = F.horizons[H], s = h.summary, top = (h.calibration || []).find(c => c.bucket === "Top 20%");
  $("picks-lede").textContent = SIZED
    ? `Today's portfolio: the ${h.picks.length} S&P 500 stocks with the best scores (the top ${Math.round(F.top_fraction*100)}% of ${h.universe}), `
      + `each held in proportion to its company's value, biggest first. The same stocks for every holding period; the track record and risk numbers change with the period. Prices as of ${F.data_through}.`
    : SIMPLE
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
  const P = h.picks, top10 = P.slice(0, 10).reduce((a, p) => a + (p.weight || 0), 0), edge = s.periods ? s.avg_picks - s.avg_sp500 : null;
  $("pick-strip").innerHTML = [
    ["Holdings", `${P.length} stocks`],
    SIZED ? ["Largest holding", `${esc(P[0].ticker)} ${pct(P[0].weight)}`] : ["Top pick", esc(P[0].ticker)],
    SIZED ? ["Top 10 share", pct(top10, 0)] : null,
    ["Edge per period", edge == null ? "–" : `<span style="color:var(${edge >= 0 ? "--up" : "--down"})">${signed(edge)}</span>`],
    ["Prices as of", new Date(F.data_through + "T12:00:00").toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"})]
  ].filter(Boolean).map(([k, v]) => `<div><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  const n = F.n_show || 15, shown = showAll ? h.picks : h.picks.slice(0, n);
  $("pick-more").classList.toggle("hidden", h.picks.length <= n);
  $("pick-more").textContent = showAll ? `Show the top ${n} only` : `Show all ${h.picks.length} holdings`;
  $("pick-more").onclick = () => { showAll = !showAll; renderPicks(); };
  $("pick-table").innerHTML = `<thead><tr><th>#</th><th>Stock</th>${SIZED ? '<th class="num">Share</th>' : ""}<th>Model score</th><th>Likely range (80%)</th>
    <th class="num">Chance of loss</th><th>What stands out</th><th>Latest news</th><th class="num">Price</th></tr></thead><tbody>` +
    shown.map(p => `<tr><td>${p.rank}</td>
      <td><a class="tk" href="#lookup:${esc(p.ticker)}" onclick="openStock('${esc(p.ticker)}'); return false;">${esc(p.ticker)}</a><div class="nm" title="${esc(p.name)}">${esc(p.name)}</div></td>
      ${SIZED ? `<td class="num"><div class="share"><div class="track"><div class="fill" style="width:${Math.min(100, p.weight / h.picks[0].weight * 100).toFixed(0)}%"></div></div><b>${pct(p.weight, p.weight < .01 ? 2 : 1)}</b></div></td>` : ""}
      <td><div class="prob"><div class="track"><div class="fill" style="width:${(p.probability*100).toFixed(0)}%"></div></div><b>${SIMPLE ? Math.round(p.probability * 100) : pct(p.probability, 0)}</b></div>
        ${p.score_rank ? `<div class="range-txt">#${p.score_rank} of ${h.universe} by score</div>` : ""}</td>
      <td><div class="range"><div class="axis"></div><div class="span" style="left:${X(p.range_low)}%;width:${X(p.range_high)-X(p.range_low)}%"></div><div class="zero" style="left:${X(0)}%"></div></div>
          <div class="range-txt">${signed(p.range_low,0)} to ${signed(p.range_high,0)}</div></td>
      <td class="num">${pct(p.chance_of_loss,0)}<div class="range-txt">(${p.hist_chance_of_loss == null ? "–" : pct(p.hist_chance_of_loss,0)} in history)</div></td>
      <td>${p.traits.length ? p.traits.slice(0, 2).map(t => `<span class="chip">${esc(t)}</span>`).join("") + (p.traits.length > 2 ? `<span class="more-chip">+${p.traits.length - 2} more</span>` : "") : '<span class="nm">Balanced profile</span>'}</td>
      <td>${latestNews(p.ticker)}</td>
      <td class="num">$${p.price.toFixed(2)}</td></tr>`).join("") + "</tbody>";
}

function renderMix() {
  const M = F.industry_mix || [];
  $("mix-wrap").classList.toggle("hidden", !M.length);
  if (!M.length) return;
  const mx = Math.max(...M.map(r => Math.max(r.portfolio, r.sp500))), W = v => (v / mx * 100).toFixed(1) + "%";
  const pts = d => (d >= 0 ? "+" : "−") + Math.abs(d * 100).toFixed(1) + " pts";
  const top3 = M.filter(r => r.industry !== "Other").slice(0, 3), p3 = top3.reduce((a, r) => a + r.portfolio, 0), s3 = top3.reduce((a, r) => a + r.sp500, 0);
  const tilt = M.filter(r => r.industry !== "Other").map(r => ({...r, d: r.portfolio - r.sp500})).sort((a, b) => Math.abs(b.d) - Math.abs(a.d));
  const over = tilt.find(r => r.d > 0), under = tilt.find(r => r.d < 0);
  $("mix-lede").innerHTML = `The three biggest industries hold <b>${pct(p3, 0)}</b> of the portfolio, versus ${pct(s3, 0)} of the S&amp;P 500. `
    + (over ? `Biggest overweight: ${esc(over.industry)} (${pts(over.d)}). ` : "") + (under ? `Biggest underweight: ${esc(under.industry)} (${pts(under.d)}).` : "");
  $("mix").innerHTML = M.map((r, i) => { const d = r.portfolio - r.sp500;
    return `<div class="mixrow" role="row" tabindex="0" data-i="${i}">
      <div class="lab" role="rowheader">${esc(r.industry)}<small>${r.n_holdings} holding${r.n_holdings === 1 ? "" : "s"}</small></div>
      <div class="mixbars" aria-hidden="true"><i class="p" style="width:${W(r.portfolio)}"></i><i class="s" style="width:${W(r.sp500)}"></i></div>
      <div class="mixval" role="cell"><b>${pct(r.portfolio)}</b> <span>vs ${pct(r.sp500)}</span><em style="color:var(${Math.abs(d) < .005 ? "--muted" : d > 0 ? "--up" : "--down"})">${Math.abs(d) < .005 ? "about the same" : pts(d)}</em></div></div>`; }).join("");
  const tip = $("mix-tip"), box = tip.parentElement;
  const showTip = row => { const r = M[+row.dataset.i], d = r.portfolio - r.sp500;
    tip.innerHTML = `<b>${esc(r.industry)}</b>
      <div class="r"><span><i class="sw" style="background:var(--mix-port)"></i>Portfolio</span><b>${pct(r.portfolio)}</b></div>
      <div class="r"><span><i class="sw" style="background:var(--mix-sp)"></i>S&amp;P 500</span><b>${pct(r.sp500)}</b></div>
      <div class="r"><span>Difference</span><span>${pts(d)}</span></div>
      ${r.holdings.length ? `<div style="margin-top:6px;color:var(--muted)">Largest holdings: ${r.holdings.map(esc).join(", ")}${r.n_holdings > r.holdings.length ? ` +${r.n_holdings - r.holdings.length} more` : ""}</div>` : '<div style="margin-top:6px;color:var(--muted)">No holdings in this industry</div>'}`;
    tip.classList.remove("hidden");
    const b = box.getBoundingClientRect(), rr = row.getBoundingClientRect();
    tip.style.top = (rr.bottom - b.top + 4) + "px";
    tip.style.left = Math.max(8, Math.min(b.width - tip.offsetWidth - 8, rr.left - b.left + 180)) + "px"; };
  $("mix").querySelectorAll(".mixrow").forEach(row => {
    row.onmouseenter = row.onfocus = () => showTip(row);
    row.onmouseleave = row.onblur = () => tip.classList.add("hidden");
    row.onclick = () => showTip(row); });
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
    ? `If you had bought the model's top ${Math.round(F.top_fraction*100)}% of stocks${SIZED ? ", sized by company value," : ""} at the start of each quarter and held them for ${h.label}, `
      + `here is how you would have done against simply buying the S&P 500 on the same day. ` + (SIZED ? `Covers picks whose period ended before ${F.holdout_from}.` : `Periods ending in ${F.holdout_from} or later are held back for a final test.`)
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

function renderVersions() {
  const V = F.versions;
  $("versions-wrap").classList.toggle("hidden", !(V && V.versions.length));
  if (!V || !V.versions.length) return;
  const start = new Date(V.started + "T12:00:00").toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"});
  const names = {main: "Official model", capped: "Capped at 10%", equal: "Equal weight", momentum: "Plus momentum"};
  const days = Math.max(...V.versions.map(v => v.days));
  $("versions-lede").textContent = `Since ${start}, every morning also saves the portfolio of ${V.versions.length - 1} alternative versions. `
    + `They are never used for the official picks, and their saved picks can't be changed later, so this is an honest test of which design works. `
    + `Each day's portfolio is held for ${V.months} months. ` + (days < 60 ? `With only ${days} trading day${days === 1 ? "" : "s"} so far, differences are noise; give it 6 to 12 months.` : "");
  $("versions-table").innerHTML = `<thead><tr><th>Version</th><th>How it differs</th><th class="num">Days tracked</th><th class="num">Avg return since picked</th>
    <th class="num">S&amp;P 500</th><th class="num">Edge</th><th class="num">Days ahead</th><th class="num">Largest holding</th></tr></thead><tbody>`
    + V.versions.map(v => { const e = v.avg_ret - v.avg_sp_ret; return `<tr><td style="white-space:nowrap"><b>${esc(names[v.version] || v.version)}</b>${v.version === "main" ? '<span class="offical">Official</span>' : ""}</td>
      <td class="desc">${esc(v.description)}</td><td class="num">${v.days}</td><td class="num">${signed(v.avg_ret)}</td><td class="num">${signed(v.avg_sp_ret)}</td>
      <td class="num"><span class="pill ${e >= 0 ? "up" : "down"}">${signed(e)}</span></td><td class="num">${v.days_ahead} of ${v.days}</td>
      <td class="num">${esc(v.top)} ${pct(v.top_weight, 0)}<div class="range-txt">${v.holdings} holdings</div></td></tr>`; }).join("") + "</tbody>";
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
  $("live-lede").textContent = `Real picks, made before the results were known. Started ${fmt(start)}: every morning's `
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
  ["earnings_yield", "Cheap vs. earnings", "Yearly profit compared with the company's market value (the inverse of the P/E ratio). Higher = you pay less for each dollar of profit."],
  ["book_to_market", "Cheap vs. book value", "What the company owns minus what it owes, compared with its market value. Higher = cheaper."],
  ["gross_prof", "Gross profitability", "Gross profit for every dollar of assets: how much money the core business makes."],
  ["roa", "Return on assets", "Net income for every dollar of assets, after all costs and taxes."],
  ["rev_growth", "Revenue growth", "How fast sales grew compared with a year earlier."],
  ["leverage", "Low debt", "Total liabilities compared with total assets. Companies that owe less rank higher."]];
const PLAIN = {earnings_yield: "a low price compared with its profits", book_to_market: "a low price compared with its net worth",
  gross_prof: "a very profitable core business", roa: "a strong return on its assets", rev_growth: "fast-growing sales", leverage: "little debt"};
const WEAK = {earnings_yield: "a high price compared with its profits", book_to_market: "a high price compared with its net worth",
  gross_prof: "weak gross profitability", roa: "a weak return on its assets", rev_growth: "slow or shrinking sales", leverage: "a heavy debt load"};
const openRows = new Set();
let industry = "";
const hz = st => st.horizons.find(x => x.months === F.horizons[H].months) || st.horizons[0];
const scoreTxt = v => SIMPLE ? String(Math.round(v * 100)) : pct(v, 0);
const topTxt = p => p >= .5 ? `Top ${Math.max(1, Math.round((1 - p) * 100))}%` : `Bottom ${Math.max(1, Math.round(p * 100))}%`;
const list = a => a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1];

function openStock(t) {
  const st = S.find(s => s.ticker === t); if (!st) return;
  $("lq").value = ""; industry = "";
  $("lookup-filters").querySelectorAll(".fchip").forEach(x => x.classList.remove("on"));
  openRows.add(st.ticker); show("lookup", "lookup:" + st.ticker); renderLookup();
  const row = document.querySelector(`tr[data-t="${st.ticker}"]`); if (row) row.scrollIntoView({behavior: "smooth", block: "start"});
}
function toggleRow(t) { openRows.has(t) ? openRows.delete(t) : openRows.add(t); renderLookup(); }

function whyText(st, h) {
  const n = S.length, have = MEASURES.filter(([k]) => st.measures[k] != null);
  const strong = have.filter(([k]) => st.measures[k] >= .7).sort((a, b) => st.measures[b[0]] - st.measures[a[0]]);
  const weak = have.filter(([k]) => st.measures[k] <= .3).sort((a, b) => st.measures[a[0]] - st.measures[b[0]]);
  const missing = MEASURES.filter(([k]) => st.measures[k] == null).map(m => m[1].toLowerCase());
  const tone = h.percentile >= .9 ? "one of the model's favorites" : h.percentile >= .7 ? "rated well above average"
    : h.percentile >= .4 ? "rated about average" : h.percentile >= .15 ? "rated below average" : "near the bottom of the list";
  let out = `<b>${esc(st.ticker)} ranks #${h.rank} of ${n}: ${tone}.</b> `;
  out += SIMPLE ? `Its score of ${scoreTxt(h.score)} is the average of where it ranks on six measures of value, profitability, growth and debt. `
                : `The model gives it a ${pct(h.score, 0)} chance of beating the typical S&P 500 stock over ${F.horizons[H].label}. `;
  if (strong.length) out += `It is helped by ${list(strong.map(([k]) => `${PLAIN[k]} (${topTxt(st.measures[k]).toLowerCase()})`))}. `;
  if (weak.length) out += `${strong.length ? "Holding it back" : "It is held back by"}: ${list(weak.map(([k]) => `${WEAK[k]} (${topTxt(st.measures[k]).toLowerCase()})`))}. `;
  if (!strong.length && !weak.length) out += "It is close to the middle on every measure, with nothing that stands out either way. ";
  if (missing.length) out += `Not reported in its SEC filings, so counted as average: ${list(missing)}.`;
  return out;
}
function cautions(st, h) {
  const c = [], vols = S.map(s => hz(s).volatility).sort((a, b) => a - b), med = vols[Math.floor(vols.length / 2)];
  if (h.volatility > med * 1.5) c.push(`Its price swings about ${(h.volatility / med).toFixed(1)}× as much as the typical S&P 500 stock, so the range of outcomes is wide.`);
  if (st.traits.includes("Negative book value")) c.push("It owes more than it owns on paper (negative book value), often from large share buybacks, so the cheap-vs-book measure is left out.");
  if (st.ret_1y != null && st.ret_1y > .6) c.push(`The stock is up ${signed(st.ret_1y, 0)} in a year; the measures use the latest price, so some of the good news may already be priced in.`);
  if (st.ret_1y != null && st.ret_1y < -.3) c.push(`The stock is down ${signed(st.ret_1y, 0)} in a year. It can look cheap because the market expects trouble the financials don't show yet.`);
  if (st.industry === "Finance") c.push("Banks and insurers carry large liabilities by design, so they tend to rank poorly on debt and gross profitability.");
  c.push("The measures come from the company's last SEC filings, which can be a few months old.");
  return c;
}
function detailHtml(st) {
  const h = hz(st), n = S.length, inPicks = st.weight != null;
  return `<div class="detail">
    <div class="detail-head"><span class="big">${esc(st.ticker)}</span><span class="co">${esc(st.name)}</span>
      ${inPicks ? `<span class="badge">In the portfolio · ${pct(st.weight, st.weight < .01 ? 2 : 1)} share</span>` : ""}</div>
    <div class="nm" style="max-width:none;white-space:normal">${esc(st.industry)} · $${st.price.toFixed(2)}${st.ret_1y == null ? "" : " · " + signed(st.ret_1y) + " over the past year"}</div>
    <h3>Why the model rates it this way</h3>
    <p class="why">${whyText(st, h)}</p>
    <h3>Recent news</h3>${(NEWS_BY[st.ticker] || []).length ? `<ul class="newslist">${NEWS_BY[st.ticker].slice(0, 6).map(n =>
      `<li><a href="${esc(safeUrl(n.link))}" target="_blank" rel="noopener">${esc(n.title)}</a><div class="when nm" style="max-width:none">${when(n.t)} · ${esc(n.source.replace(/^Google News: /, ""))}</div></li>`).join("")}</ul>`
      : `<p class="note" style="margin-top:0">No headlines about ${esc(st.name || st.ticker)} in the last two weeks.</p>`}
    <div class="cards">
      ${card("Rank today", `#${h.rank} <span style="font-size:14px;color:var(--muted);font-weight:500">of ${n}</span>`, `${topTxt(h.percentile)} of current S&P 500 members`)}
      ${card("Model score", scoreTxt(h.score), SIMPLE ? "0–100, average rank on the six measures" : `chance of beating the typical stock over ${F.horizons[H].label}`)}
      ${card(`Likely range, ${F.horizons[H].label}`, `${signed(h.range_low, 0)} to ${signed(h.range_high, 0)}`, "8 in 10 outcomes, from its last 3 years of swings")}
      ${card("Chance of loss", pct(h.chance_of_loss, 0), h.hist_chance_of_loss == null ? "not enough history" : `${pct(h.hist_chance_of_loss, 0)} of past ${F.horizons[H].label} periods lost money`)}
    </div>
    <h3>The six measures behind the score</h3>
    <div class="grid2">${MEASURES.map(([k, label, desc]) => { const v = st.measures[k]; return `<div><div class="hbar big"><span><b>${label}</b></span>
      <div class="t">${v == null ? "" : `<div class="f" style="width:${(v*100).toFixed(0)}%"></div>`}<div class="mid"></div></div>
      <b class="num">${v == null ? "n/a" : topTxt(v)}</b></div><div class="mdesc">${desc}</div></div>`; }).join("")}</div>
    <p class="note" style="margin-top:0">Bars show where it ranks against the other S&P 500 stocks; the middle line is the typical stock. n/a = not reported.</p>
    <h3>Keep in mind</h3>
    <ul class="note" style="margin-top:0">${cautions(st, h).map(c => `<li>${esc(c)}</li>`).join("")}</ul>
  </div>`;
}
function renderLookup() {
  if (!S.length) { $("lookup-lede").textContent = "The stock list appears after the next morning update."; return; }
  $("lookup-lede").textContent = `Every current S&P 500 member, ranked by today's model score for the chosen holding period. `
    + `Click any stock to open it and see why the model rates it the way it does.`;
  const q = $("lq").value.trim().toLowerCase();
  const rows = S.filter(st => (!industry || st.industry === industry)
    && (!q || st.ticker.toLowerCase().startsWith(q) || st.name.toLowerCase().includes(q) || st.industry.toLowerCase().includes(q)))
    .map(st => [st, hz(st)]).sort((a, b) => a[1].rank - b[1].rank);
  $("stock-table").innerHTML = `<thead><tr><th></th><th class="num">Rank</th><th>Stock</th><th>Industry</th><th>Model score</th><th class="num">Chance of loss</th>
    <th class="num">Past year</th><th class="num">Price</th></tr></thead><tbody>` + rows.slice(0, 600).map(([st, h]) => {
    const open = openRows.has(st.ticker);
    return `<tr class="clickable${open ? " open" : ""}" data-t="${esc(st.ticker)}" onclick="toggleRow('${esc(st.ticker)}')" aria-expanded="${open}">
      <td><span class="chev">▶</span></td><td class="num">${h.rank}</td>
      <td><div class="tk">${esc(st.ticker)}</div><div class="nm" title="${esc(st.name)}">${esc(st.name)}</div></td>
      <td class="nm">${esc(st.industry)}</td>
      <td><div class="prob"><div class="track"><div class="fill" style="width:${(h.score*100).toFixed(0)}%"></div></div><b>${scoreTxt(h.score)}</b></div></td>
      <td class="num">${pct(h.chance_of_loss, 0)}</td><td class="num">${signed(st.ret_1y, 0)}</td><td class="num">$${st.price.toFixed(2)}</td></tr>`
      + (open ? `<tr class="drop"><td colspan="8">${detailHtml(st)}</td></tr>` : ""); }).join("") + "</tbody>";
  $("stock-count").textContent = rows.length ? `${rows.length} of ${S.length} stocks shown.` : "No stocks match.";
  fitDrops();
}
function fitDrops() {   // keep the open panel as wide as the visible table, even when the table scrolls sideways
  const w = $("stock-table").parentElement.clientWidth - 24;
  document.querySelectorAll("tr.drop .detail").forEach(d => d.style.width = w + "px");
}
window.addEventListener("resize", fitDrops);
if (S.length) {
  const inds = [...new Set(S.map(s => s.industry))].sort();
  $("lookup-filters").innerHTML = inds.map(i => `<button class="fchip" data-i="${esc(i)}">${esc(i)}</button>`).join("");
  $("lookup-filters").querySelectorAll(".fchip").forEach(c => c.onclick = () => {
    industry = industry === c.dataset.i ? "" : c.dataset.i;
    $("lookup-filters").querySelectorAll(".fchip").forEach(x => x.classList.toggle("on", x.dataset.i === industry)); renderLookup(); });
  $("lq").oninput = renderLookup;
  $("lq").onkeydown = e => { if (e.key === "Enter") { const q = $("lq").value.trim().toUpperCase(),
    hit = S.find(s => s.ticker === q) || S.find(s => s.ticker.startsWith(q) || s.name.toUpperCase().includes(q)); if (hit) openStock(hit.ticker); } };
  if (START[0] === "lookup" && START[1]) { const t = START[1].toUpperCase(); if (S.some(s => s.ticker === t)) { openRows.add(t);
    setTimeout(() => document.querySelector(`tr[data-t="${t}"]`)?.scrollIntoView({block: "start"}), 50); } }
}
window.addEventListener("hashchange", () => { const [tab, t] = location.hash.slice(1).split(":");
  if (tab === "lookup" && t) openStock(t.toUpperCase()); });

function renderAll() { markSegs(); renderPicks(); renderMix(); renderLive(); renderVersions(); renderRecord(); renderLookup(); }

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
let heldOnly = false;
$("news-chips").innerHTML = srcs.map(s => `<button class="fchip" data-s="${esc(s)}">${esc(s)}</button>`).join("");
function renderNews() {
  const q = $("q").value.toLowerCase(); let day = "", out = [];
  N.filter(r => (!on.size || on.has(r.source.split(":")[0])) && (!heldOnly || (r.tk || []).some(t => HELD.has(t)))
    && (r.title + " " + r.summary + " " + r.source + " " + (r.tk || []).join(" ")).toLowerCase().includes(q)).slice(0, 400).forEach(r => {
    const d = new Date(r.t), dl = d.toLocaleDateString(undefined, {weekday:"long", month:"long", day:"numeric"});
    if (dl !== day) { day = dl; out.push(`<div class="day">${dl}</div>`); }
    const safe = /^https?:/.test(r.link) ? r.link : "#";
    out.push(`<div class="story"><div class="meta">${d.toLocaleTimeString(undefined, {hour:"numeric", minute:"2-digit"})} · ${esc(r.source)}${r.seen === latest ? ' · <span class="new">New</span>' : ""}</div>
      <a href="${esc(safe)}" target="_blank" rel="noopener">${esc(r.title)}</a>${r.summary ? `<p>${esc(r.summary)}</p>` : ""}
      ${(r.tk || []).length ? `<div>${r.tk.map(t => `<span class="tkchip${HELD.has(t) ? " held" : ""}" onclick="openStock('${esc(t)}')" title="${HELD.has(t) ? "In the portfolio · " : ""}Open ${esc(t)} in Stock lookup">${esc(t)}</span>`).join("")}</div>` : ""}</div>`);
  });
  $("news-list").innerHTML = out.join("") || '<p class="note">No headlines match.</p>';
}
$("q").oninput = renderNews;
$("held-only").onclick = () => { heldOnly = !heldOnly; $("held-only").classList.toggle("on", heldOnly); renderNews(); };
document.querySelectorAll("#news-chips .fchip").forEach(c => c.onclick = () => { on.has(c.dataset.s) ? on.delete(c.dataset.s) : on.add(c.dataset.s); c.classList.toggle("on"); renderNews(); });
renderNews();
</script>
</body></html>
"""


if __name__ == "__main__":
    print("Saved", build())
