"""All the settings you will want to tweak live here."""

START_DATE = "2010-01-01"      # how far back to download prices
FIRST_TEST_YEAR = 2016         # first year the backtest is scored on
UNIVERSE = "historical"        # "historical" = S&P 500 members as they were on each date (less survivorship bias)
                               # "today" = random sample of today's S&P 500 (the old, biased setup)
N_STOCKS = 150                 # "today" only: how many of today's S&P 500 to sample
SAMPLE_SEED = 42               # "today" only: change to test a different random sample of stocks
HOLDOUT_FROM_YEAR = 2023       # years from here on are kept for one final check (python holdout.py)
# The 2023+ years were scored once (Nov 3, 2026) and size weighting was then adopted after studying them,
# so they are no longer an untouched test. The live record (data/live/picks.csv) is the real test now.
HORIZON_MONTHS = 12            # how far ahead the model predicts
REBALANCE_MONTH = 1            # 1 = rebalance each January
TOP_FRACTION = 0.20            # hold the top 20% of stocks the model likes
COST_PER_REBALANCE = 0.002     # 0.2% yearly trading-cost assumption
PICK_HORIZONS = [6, 12, 24]    # forecast.py / website: holding periods (months) to make picks for
N_PICKS = 15                   # how many holdings the website lists before "show all"
WEIGHTING = "size"             # "size" = hold the top 20% in proportion to company value, like the S&P 500;
                               # "equal" = same amount in each. Size won in both 2016-22 and 2023-26 (Nov 2026 review)

MODEL_TYPE = "simple"          # "simple" = average of the ranked inputs; "forest" = random forest (machine learning)
                               # simple won the Nov 2026 comparison (python experiments.py --simple)
MODEL_PARAMS = dict(
    n_estimators=300,
    max_depth=5,
    min_samples_leaf=100,
    n_jobs=-1,
    random_state=0,
)

USE_FUNDAMENTALS = True        # add company financials from SEC filings to the model's inputs
USE_PRICE_FEATURES = False     # also feed the model price patterns (momentum, volatility); they hurt in 2016-2022
SEC_USER_AGENT = "stock-model bhrugu1203@icloud.com"   # the SEC asks scripts to include a contact email

CACHE_DIR = "data"
OUTPUT_DIR = "outputs"

# --- News collector (python news.py) ---
NEWS_FEEDS = {
    "MarketWatch":       "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "MarketWatch Pulse": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "WSJ Markets":       "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "CNBC Markets":      "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "CNBC Top News":     "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC Earnings":     "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135",
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "FT Markets":        "https://www.ft.com/markets?format=rss",
    "Seeking Alpha":     "https://seekingalpha.com/market_currents.xml",
    "Investing.com":     "https://www.investing.com/rss/news.rss",
    "Google News":       "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en",
    "Federal Reserve":   "https://www.federalreserve.gov/feeds/press_all.xml",
    "SEC":               "https://www.sec.gov/news/pressreleases.rss",
}
WATCHLIST = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]  # extra Yahoo headlines for these tickers
NEWS_PAGE_DAYS = 3             # how many days of headlines the news page shows (all are kept on disk)
STOCK_NEWS_DAYS = 14           # how far back the headlines shown on each stock go
