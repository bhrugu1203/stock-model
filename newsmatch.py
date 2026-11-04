"""Find which S&P 500 companies each headline is about, for the news shown on each pick.

A headline is tagged with a company when its title names it: the company's cleaned-up name
("Nvidia", "Lam Research"), a well-known short name (ALIASES: "Google", "J&J"), or its ticker
written the way finance sites do ("(NVDA)", "$NVDA", "NVDA stock"). Names that are everyday words
("Target", "Progressive", "Visa") only count with a ticker or their full company name.
"""
import re

SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "companies", "ltd", "limited", "plc",
            "group", "holdings", "holding", "the", "nv", "n.v", "sa", "lp", "llc", "class", "new", "de", "md", "oh",
            "mi", "ma", "nj", "pa", "ny", "va", "tx", "us", "trust", "intl", "com", "cos"}
# first words that are ordinary English (or places), so a lone word would match unrelated news
COMMON = set("""advanced air alliant american analog applied arch arthur automatic avery baker ball bank best block booking
boston brown builders capital cardinal carrier charles charter church citizens comfort consolidated constellation cooper
crown delta digital dollar dominion dover dow duke edison edwards eli essex everest expand extra fair federal fidelity
fifth first flex fox franklin gen general genuine global globe hartford henry home host hunt huntington illinois
interactive intercontinental international invitation iron jack johnson kinder las live marathon marsh martin mid
monster morgan mosaic news northern old on packaging palo philip phillips pinnacle price principal progressive public
quest ralph raymond realty regency regions republic ross royal smith southern southwest stanley state steel super take
target texas trade travelers tyler union united universal us vertex visa vulcan walt waste waters west western
williams willis zebra cincinnati coca hewlett estee kimberly sherwin thermo bristol becton procter norfolk norwegian
simon square snap axon atmos oracle quanta veeva vistra coherent otis cummins emerson jacobs eaton lennox carnival
hubbell apollo workday monolithic intuitive align tapestry deere amazon apple nasdaq business energy health
market markets abbott bancorp bancshares financial bankshares""".split())
# tickers that are also everyday words or common abbreviations, so "ALL" or "NOW" in a headline means nothing
TICKER_WORDS = {"ALL", "NOW", "KEY", "LOW", "BALL", "TECH", "FAST", "POOL", "DAY", "HAS", "IT", "ON", "ARE", "CAT",
                "COST", "MAS", "CPT", "WELL", "PEAK", "HUM", "CARR", "DASH", "TT", "AI", "EV", "FIX", "BR", "GEN", "AMP",
                "COO", "DGX", "CFO", "CEO", "IPO", "ETF"}
ALIASES = {
    "GOOGL": ["Google", "Alphabet"], "GOOG": ["Google", "Alphabet"], "META": ["Meta", "Facebook", "Instagram"],
    "BRK-B": ["Berkshire"], "LLY": ["Eli Lilly", "Lilly"], "JPM": ["JPMorgan", "J.P. Morgan"], "XOM": ["Exxon"],
    "KO": ["Coca-Cola"], "PG": ["Procter & Gamble", "P&G"], "JNJ": ["Johnson & Johnson", "J&J"],
    "PEP": ["PepsiCo", "Pepsi"], "MCD": ["McDonald's", "McDonald’s", "McDonalds"], "DIS": ["Disney"],
    "C": ["Citigroup", "Citi"], "GS": ["Goldman"], "UNH": ["UnitedHealth"], "GM": ["General Motors", "GM"],
    "GE": ["GE Aerospace", "General Electric"], "GEV": ["GE Vernova"], "HD": ["Home Depot"], "LOW": ["Lowe's", "Lowe’s"],
    "TGT": ["Target Corp", "Target's", "Target’s"], "V": ["Visa Inc"], "AMD": ["AMD", "Advanced Micro"],
    "TROW": ["T. Rowe", "T Rowe"], "DHI": ["D.R. Horton", "DR Horton"], "HPE": ["Hewlett Packard Enterprise", "HPE"],
    "HPQ": ["HP Inc"], "IBM": ["IBM"], "TSLA": ["Tesla"], "WMT": ["Walmart"], "COST": ["Costco"],
    "BAC": ["Bank of America", "BofA"], "WFC": ["Wells Fargo"], "MS": ["Morgan Stanley"], "PM": ["Philip Morris"],
    "LMT": ["Lockheed"], "NOC": ["Northrop"], "LUV": ["Southwest Airlines"], "UAL": ["United Airlines"],
    "DAL": ["Delta Air"], "AAL": ["American Airlines"], "EL": ["Estee Lauder", "Estée Lauder"], "T": ["AT&T"],
    "TMUS": ["T-Mobile"], "CVS": ["CVS"], "UPS": ["UPS"], "FDX": ["FedEx"], "BKNG": ["Booking Holdings"],
    "ORCL": ["Oracle"], "NOW": ["ServiceNow"], "PANW": ["Palo Alto Networks"], "TXN": ["Texas Instruments"],
    "AMAT": ["Applied Materials"], "ADI": ["Analog Devices"], "SQ": ["Block Inc"], "XYZ": ["Block Inc"],
    "BX": ["Blackstone"], "BLK": ["BlackRock"], "KKR": ["KKR"], "SCHW": ["Schwab"], "CMCSA": ["Comcast"],
    "PGR": ["Progressive Corp"], "ALL": ["Allstate"], "DOW": ["Dow Inc"], "F": ["Ford"], "CAT": ["Caterpillar"],
    "MMM": ["3M"], "HON": ["Honeywell"], "RTX": ["RTX", "Raytheon"], "BA": ["Boeing"], "MU": ["Micron"],
    "SMCI": ["Super Micro", "Supermicro"], "STX": ["Seagate"], "WDC": ["Western Digital"], "SNDK": ["SanDisk"],
    "CRWD": ["CrowdStrike"], "ABNB": ["Airbnb"], "PYPL": ["PayPal"], "MRNA": ["Moderna"], "WBD": ["Warner Bros"],
    "FOXA": ["Fox Corp"], "FOX": ["Fox Corp"], "NWSA": ["News Corp"], "NWS": ["News Corp"], "TTWO": ["Take-Two"],
    "ORLY": ["O'Reilly", "O’Reilly"], "AMZN": ["Amazon"], "AAPL": ["Apple"], "NDAQ": ["Nasdaq Inc", "Nasdaq, Inc"], "ABT": ["Abbott Laboratories", "Abbott Labs"],
    "USB": ["U.S. Bancorp", "US Bancorp"], "BBY": [r"re:Best Buy(?! [Aa]nd [Hh]old)"], "DE": ["Deere"], "CCL": ["Carnival"],
    "APO": ["Apollo Global"], "WDAY": ["Workday"], "ISRG": ["Intuitive Surgical"], "TPR": ["Tapestry"],
    "OTIS": ["Otis Worldwide"], "CMI": ["Cummins"], "EMR": ["Emerson Electric"], "ETN": ["Eaton"], "MPWR": ["Monolithic Power"], "CMG": ["Chipotle"], "SBUX": ["Starbucks"], "NKE": ["Nike"], "ANET": ["Arista"],
}


def _clean(name):
    name = re.sub(r"/.*?/|/\w+$", " ", name)                  # "Newmont Corp /De/" -> "Newmont Corp"
    words = [w for w in re.split(r"[\s,.]+", name) if w and w.lower().strip("'") not in SUFFIXES]
    return " ".join(words)


def patterns(stocks):
    """ticker -> list of (regex, case_sensitive) built from the stock list in forecast.json."""
    out = {}
    for st in stocks:
        t, name = st["ticker"], _clean(st["name"])
        pats = [(r"\(" + re.escape(t) + r"\)", True), (r"\$" + re.escape(t) + r"\b", True),
                (r"\b" + re.escape(t) + r" (?:stock|shares)\b", True)]
        if len(t) >= 3 and t not in TICKER_WORDS and "-" not in t:
            pats.append((r"(?<![\w$])" + re.escape(t) + r"(?![\w-])", True))   # NVDA, AMZN written as a word
        words = name.split()
        if len(words) >= 2 and t not in ALIASES:
            pats.append((r"\b" + re.escape(name) + r"\b", False))
        first = words[0] if words else ""
        if len(first) >= 4 and first.lower() not in COMMON and first.isalpha():
            pats.append((r"\b" + re.escape(first) + r"(?:'s|’s)?\b", False))    # "Nvidia", "NVIDIA", "Lululemon's"
        for a in ALIASES.get(t, []):
            body = a[3:] if a.startswith("re:") else re.escape(a)
            pats.append((r"(?<![\w&.$])" + body + r"(?![\w&])", True))
        out[t] = [re.compile(p) if cs else re.compile(p, re.I) for p, cs in pats]
    return out


def tag(headlines, stocks):
    """List of tickers each headline is about, in the same order as headlines."""
    pats = patterns(stocks)
    tags = []
    for h in headlines:
        text = h["title"]
        hits = [t for t, ps in pats.items() if any(p.search(text) for p in ps)]
        tags.append(hits)
    return tags
