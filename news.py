"""Collect market headlines from many free feeds into one place:  python news.py

Every run adds new headlines to data/news/headlines.csv (kept forever, so it slowly
builds the news history a future model feature can be tested on) and rebuilds
the website (dashboard.py), whose Market news tab shows the latest headlines from every source.
Feeds and the ticker watchlist are set in config.py.
"""
import csv
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import config

NEWS_DIR = os.path.join(config.CACHE_DIR, "news")
ARCHIVE = os.path.join(NEWS_DIR, "headlines.csv")
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


def main():
    print("Collecting headlines...")
    rows, new, failed = collect()
    print(f"{len(new)} new headlines, {len(rows)} saved in {ARCHIVE}")
    if failed:
        print("Could not reach:", "; ".join(failed))
    import dashboard
    page = os.path.abspath(dashboard.build())
    print("Open", page)
    if "--open" in sys.argv:
        import webbrowser
        webbrowser.open("file://" + page + "#news")


if __name__ == "__main__":
    main()
