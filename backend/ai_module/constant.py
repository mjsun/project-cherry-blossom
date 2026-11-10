# patterns that signal a structured/aggregate question
STRUCTURED_PATTERNS = [
    r"\bhow many\b",
    r"\bcount\b",
    r"\btotal\b",
    r"\baverage\b",
    r"\bmean\b",
    r"\bsum\b",
    r"\blargest\b",
    r"\bsmallest\b",
    r"\bhighest\b",
    r"\blowest\b",
    r"\bmax\b",
    r"\bmin\b",
    r"\bgreater than\b",
    r"\bless than\b",
    r"\babove\b",
    r"\bbelow\b",
    r"\brange\b",
    r"\bbetween\b",
    r"\bgroup by\b",
    r"\bby state\b",
    r"\bby city\b",
    r"\bby property type\b",
    r"\bin california\b",
    r"\bin new york\b",
    r"\bin texas\b",
    r"\bin florida\b",
    r"\boffice loans\b",
    r"\bretail loans\b",
    r"\bmultifamily\b",
    r"\bhospitality\b",
    r"\bdscr\b",
    r"\bltv\b",
    r"\bbalance\b",
    r"\brate\b",
    r"\boccupancy\b",
]

# state name → abbreviation for filter extraction
STATE_MAP = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


PROPERTY_TYPES = [
    "office", "retail", "multifamily", "hospitality", "industrial",
    "mixed use", "self storage", "manufactured housing", "mobile home",
]

AGG_KEYWORDS = {
    "average dscr": "avg_dscr",
    "average ltv": "avg_ltv",
    "average rate": "avg_rate",
    "average balance": "avg_balance",
    "average": "avg_balance",
    "mean": "avg_balance",
    "how many": "count",
    "count": "count",
    "total": "sum_balance",
    "sum": "sum_balance",
}

GROUP_KEYWORDS = {
    "by state": "state", "by city": "city",
    "by property type": "general_property_type", "by seller": "seller",
    "by deal": "deal_id",
}


BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}
