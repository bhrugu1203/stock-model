"""Collect market headlines from many free feeds into one place:  python news.py

Every run adds new headlines to data/news/headlines.csv (kept forever, so it slowly
builds the news history a future model feature can be tested on) and rebuilds
outputs/news.html, one page with the latest headlines from every source.
Feeds and the ticker watchlist are set in config.py.
"""
import csv
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import config

NEWS_DIR = os.path.join(config.CACHE_DIR, "news")
ARCHIVE = os.path.join(NEWS_DIR, "headlines.csv")
PAGE = os.path.join(config.OUTPUT_DIR, "news.html")
COLUMNS = ["first_seen", "published", "source", "title", "link", "summary"]
USER_AGENT = "Mozilla/5.0 (Macintosh; stock-model news collector)"


def _text(el, tag):
    found = el.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def _clean(s, limit=300):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def _parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)                                   # RSS: "Mon, 02 Nov 2026 14:05:00 GMT"
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))  # Atom: "2026-11-02T14:05:00Z"
        except ValueError:
            return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def fetch(source, url):
    """Return a list of headline dicts from one RSS or Atom feed."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        root = ET.fromstring(resp.read())
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for it in root.iter("item"):                                      # RSS 2.0
        title = _clean(_text(it, "title"), 500)
        src = it.find("source")                                       # Google News names the real publisher here
        if source == "Google News" and src is not None and src.text:
            title = re.sub(r"\s+-\s+" + re.escape(src.text.strip()) + r"$", "", title)
            name = f"Google News: {src.text.strip()}"
        else:
            name = source
        items.append({"source": name, "title": title, "link": _text(it, "link"),
                      "published": _parse_date(_text(it, "pubDate")),
                      "summary": _clean(_text(it, "description"))})
    for it in root.iter(atom + "entry"):                              # Atom
        link = it.find(atom + "link")
        items.append({"source": source, "title": _clean(_text(it, atom + "title"), 500),
                      "link": link.get("href", "") if link is not None else "",
                      "published": _parse_date(_text(it, atom + "updated") or _text(it, atom + "published")),
                      "summary": _clean(_text(it, atom + "summary"))})
    return [i for i in items if i["title"] and i["link"].startswith("http")]


def load_archive():
    if not os.path.exists(ARCHIVE):
        return []
    with open(ARCHIVE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _key(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def collect():
    feeds = dict(config.NEWS_FEEDS)
    if config.WATCHLIST:
        feeds["Yahoo watchlist"] = ("https://feeds.finance.yahoo.com/rss/2.0/headline?s="
                                    + ",".join(config.WATCHLIST) + "&region=US&lang=en-US")
    archive = load_archive()
    seen_links = {r["link"] for r in archive}
    seen_titles = {_key(r["title"]) for r in archive}
    now = datetime.now(timezone.utc)

    new, failed = [], []
    for source, url in feeds.items():
        try:
            items = fetch(source, url)
        except Exception as e:
            failed.append(f"{source} ({type(e).__name__}: {e})")
            continue
        added = 0
        for it in items:
            k = _key(it["title"])
            if it["link"] in seen_links or k in seen_titles:          # same story from a second feed
                continue
            seen_links.add(it["link"])
            seen_titles.add(k)
            pub = it["published"] or now
            new.append({"first_seen": now.isoformat(timespec="seconds"),
                        "published": pub.isoformat(timespec="seconds"),
                        "source": it["source"], "title": it["title"],
                        "link": it["link"], "summary": it["summary"]})
            added += 1
        print(f"  {source:<20} {len(items):>4} headlines, {added:>4} new")

    os.makedirs(NEWS_DIR, exist_ok=True)
    write_header = not os.path.exists(ARCHIVE)
    with open(ARCHIVE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if write_header:
            w.writeheader()
        w.writerows(new)
    return archive + new, new, failed


def build_page(rows, new, failed):
    """Write outputs/news.html: recent headlines from every source, newest first."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=config.NEWS_PAGE_DAYS)
    new_links = {r["link"] for r in new}
    recent = []
    for r in rows:
        pub = _parse_date(r["published"])
        if pub and pub >= cutoff:
            recent.append((pub, r))
    recent.sort(key=lambda x: x[0], reverse=True)
    sources = sorted({r["source"].split(":")[0] for _, r in recent})

    cards, day = [], None
    for pub, r in recent:
        local = pub.astimezone()
        if local.date() != day:
            day = local.date()
            cards.append(f'<h2 class="day">{local:%A, %B} {local.day}</h2>')
        fresh = ' <span class="new">new</span>' if r["link"] in new_links else ""
        cards.append(
            f'<article data-source="{html.escape(r["source"].split(":")[0])}">'
            f'<div class="meta">{local:%H:%M} · {html.escape(r["source"])}{fresh}</div>'
            f'<a href="{html.escape(r["link"])}" target="_blank" rel="noopener">{html.escape(r["title"])}</a>'
            + (f'<p>{html.escape(r["summary"])}</p>' if r["summary"] else "") + "</article>")

    chips = "".join(f'<button class="chip" data-s="{html.escape(s)}">{html.escape(s)}</button>' for s in sources)
    warn = (f'<p class="warn">Could not reach: {html.escape("; ".join(failed))}</p>' if failed else "")
    page = PAGE_TEMPLATE.format(
        updated=f"{now.astimezone():%B} {now.astimezone().day}, {now.astimezone():%H:%M}",
        count=len(recent), days=config.NEWS_PAGE_DAYS, n_new=len(new), total=len(rows),
        chips=chips, warn=warn, cards="\n".join(cards) or "<p>No headlines yet.</p>")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Market News</title>
<style>
:root {{ --bg:#f7f7f5; --card:#fff; --text:#1d1d1f; --muted:#6e6e73; --line:#e3e3e0; --accent:#0a6cdf; --new:#1a7f37; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#141415; --card:#1e1e20; --text:#ececee; --muted:#9a9aa0; --line:#2e2e31; --accent:#5aa2ff; --new:#4ac26b; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width:820px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }}
.sub {{ color:var(--muted); margin:0 0 16px; font-size:13px; }}
.warn {{ color:#b35900; font-size:13px; }}
.controls {{ position:sticky; top:0; background:var(--bg); padding:8px 0 10px; z-index:1; }}
input {{ width:100%; padding:9px 12px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--text); font-size:15px; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }}
.chip {{ border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:999px; padding:3px 10px; font-size:12px; cursor:pointer; }}
.chip.on {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
h2.day {{ font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:22px 0 6px; }}
article {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; margin:6px 0; }}
article a {{ color:var(--text); text-decoration:none; font-weight:600; }}
article a:hover {{ color:var(--accent); }}
article p {{ margin:4px 0 0; color:var(--muted); font-size:13px; }}
.meta {{ font-size:12px; color:var(--muted); margin-bottom:2px; }}
.new {{ color:var(--new); font-weight:600; }}
.hidden {{ display:none; }}
</style></head><body><main>
<h1>Market News</h1>
<p class="sub">Updated {updated} · {count} headlines from the last {days} days · {n_new} new this run · {total} saved in total</p>
{warn}
<div class="controls">
<input id="q" type="search" placeholder="Search headlines (e.g. Nvidia, Fed, earnings)">
<div class="chips">{chips}</div>
</div>
{cards}
</main>
<script>
const q = document.getElementById("q"), on = new Set();
function apply() {{
  const term = q.value.toLowerCase();
  document.querySelectorAll("article").forEach(a => {{
    const okS = !on.size || on.has(a.dataset.source);
    a.classList.toggle("hidden", !(okS && a.textContent.toLowerCase().includes(term)));
  }});
  document.querySelectorAll("h2.day").forEach(h => {{
    let n = h.nextElementSibling, any = false;
    while (n && n.tagName === "ARTICLE") {{ if (!n.classList.contains("hidden")) any = true; n = n.nextElementSibling; }}
    h.classList.toggle("hidden", !any);
  }});
}}
q.addEventListener("input", apply);
document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => {{
  on.has(c.dataset.s) ? on.delete(c.dataset.s) : on.add(c.dataset.s);
  c.classList.toggle("on"); apply();
}}));
</script></body></html>
"""


def main():
    print("Collecting headlines...")
    rows, new, failed = collect()
    build_page(rows, new, failed)
    print(f"{len(new)} new headlines, {len(rows)} saved in {ARCHIVE}")
    if failed:
        print("Could not reach:", "; ".join(failed))
    print("Open", os.path.abspath(PAGE))
    if "--open" in sys.argv:
        import webbrowser
        webbrowser.open("file://" + os.path.abspath(PAGE))


if __name__ == "__main__":
    main()
