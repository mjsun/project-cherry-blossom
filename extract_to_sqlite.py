"""
extract_to_sqlite.py

Walk each labeled .tsv, find every Annex A sub-table, merge columns
by loan number, and load the result into a local SQLite database.

Run once:
    python extract_to_sqlite.py

Produces:  ./loans.db  (table: loans)
"""

import os, re, glob, sqlite3
from dataclasses import dataclass, field
from typing import Optional

# ── helpers ──────────────────────────────────────────────────────

PIPE_RE = re.compile(r"\s*\|\s*")

def _split(text: str) -> list[str]:
    return PIPE_RE.split(text.strip())

def _clean_num(val: str) -> Optional[float]:
    """Parse a number that may have commas, $, %, or 'x'."""
    if not val or val.strip().upper() in ("", "NAV", "NAP", "N/A", "VARIOUS"):
        return None
    s = val.strip().replace("$", "").replace(",", "").replace("%", "").replace("x", "")
    try:
        return float(s)
    except ValueError:
        return None

def _clean_str(val: str) -> Optional[str]:
    s = val.strip()
    if not s or s.upper() in ("NAV", "NAP", "N/A"):
        return None
    # strip trailing footnote refs like (33)(36)
    s = re.sub(r"\s*\(\d+\)\s*", " ", s).strip()
    return s or None

# ── column maps: header keyword → canonical field name ───────────

# Each sub-table has a header row.  We match header cells (lowered)
# to canonical field names.  Order of checks matters — first match
# wins for ambiguous words like "balance".

HEADER_RULES: list[tuple[str, list[str]]] = [
    # table 1 – identity
    ("property_name",        ["property name"]),
    ("seller",               ["mortgage loan seller", "seller"]),
    ("address",              ["address"]),
    ("city",                 ["city"]),
    ("state",                ["state"]),
    ("zip_code",             ["zip code", "zip"]),
    ("general_property_type",["general property type", "property type (4)", "property type"]),
    ("specific_property_type",["specific property type", "detailed"]),
    ("year_built",           ["year built", "built"]),
    ("year_renovated",       ["year renovated", "renovated"]),

    # table 2 – balance / dates
    ("original_balance",     ["original balance"]),
    ("cutoff_balance",       ["cut-off date balance", "cut-off date bal", "cutoff date balance",
                              "date balance($)"]),
    ("pct_of_pool",          ["% of aggregate", "% of cut-off", "% of initial pool",
                              "initial pool"]),
    ("maturity_balance",     ["maturity date or ard balloon", "maturity or ard balance",
                              "maturity balance"]),
    ("origination_date",     ["origination date"]),
    ("maturity_date",        ["maturity date or anticipated", "maturity or ard date",
                              "maturity date"]),

    # table 3 – rate
    ("gross_rate",           ["gross mortgage rate", "interest rate"]),
    ("net_rate",             ["net mortgage rate"]),
    ("amort_type",           ["amortization type"]),

    # table 4 – valuation / leverage
    ("appraised_value",      ["appraised value"]),
    ("cutoff_ltv",           ["cut-off date ltv", "cut off date ltv", "date ltv ratio",
                              "cutoff date ltv"]),
    ("maturity_ltv",         ["ltv ratio at maturity", "ltv ratio at mat"]),
    ("uw_noi_dscr",          ["uw noi dscr"]),
    ("uw_ncf_dscr",          ["uw ncf dscr", "underwritten ncf dscr",
                              "underwritten noi dscr"]),  # file5 uses "underwritten"
    ("uw_noi",               ["uw net operating income", "uw noi ($)", "noi($)"]),
    ("uw_ncf",               ["uw net cash flow", "uw ncf ($)", "ncf($)"]),
    ("occupancy",            ["occupancy rate", "occupancy"]),

    # table – location (file5 has city/state in a separate sub-table)
    ("county",               ["county"]),
    ("num_units",            ["number of units", "rentable area", "sf/units",
                              "rooms/pads"]),
    ("unit_measure",         ["unit of measure", "measure"]),
]

def _match_header(cell: str) -> Optional[str]:
    low = cell.lower()
    for field_name, keywords in HEADER_RULES:
        for kw in keywords:
            if kw in low:
                return field_name
    return None


# ── parse one file ───────────────────────────────────────────────

LOAN_NO_RE = re.compile(r"^(\d+)(\.\d+)?$")

@dataclass
class LoanRecord:
    deal_id: str = ""
    loan_no: str = ""
    is_sub: bool = False   # True for sub-properties like 1.01
    data: dict = field(default_factory=dict)


def _deal_id_from_path(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def parse_file(path: str) -> list[LoanRecord]:
    """Return one LoanRecord per loan row found across all sub-tables."""

    lines = open(path, encoding="utf-8").readlines()

    # pass 1: find every header row (has "Property Name" and recognizable
    #         financial/location fields)
    headers: list[tuple[int, dict[int, str]]] = []   # (line_idx, {col_idx: field_name})

    for li, line in enumerate(lines):
        cells = _split(line)
        if len(cells) < 4:
            continue
        col_map: dict[int, str] = {}
        has_name = False
        for ci, cell in enumerate(cells):
            matched = _match_header(cell)
            if matched:
                col_map[ci] = matched
                if matched == "property_name":
                    has_name = True
        # require property_name + at least 2 other mapped columns
        if has_name and len(col_map) >= 3:
            headers.append((li, col_map))

    if not headers:
        return []

    # pass 2: for each header, read data rows until next header or gap
    deal_id = _deal_id_from_path(path)
    merged: dict[str, LoanRecord] = {}   # keyed by loan_no string

    for h_idx, (h_line, col_map) in enumerate(headers):
        # determine end boundary
        if h_idx + 1 < len(headers):
            end_line = headers[h_idx + 1][0]
        else:
            end_line = len(lines)

        for li in range(h_line + 1, end_line):
            cells = _split(lines[li])
            if len(cells) < 3:
                continue

            # figure out which cell holds the loan number
            # file2/file4: cell[0] is loan_no  ("1", "1.01")
            # file5: cell[0] is flag ("Loan"/"Property"), cell[1] is loan_no
            loan_no = None
            col_offset = 0

            if cells[0].strip().lower() in ("loan", "property"):
                # file5 style
                raw = cells[1].strip()
                if LOAN_NO_RE.match(raw):
                    loan_no = raw
                    col_offset = 1   # all column indices shift by 1
            else:
                raw = cells[0].strip()
                if LOAN_NO_RE.match(raw):
                    loan_no = raw

            if loan_no is None:
                continue

            is_sub = "." in loan_no

            if loan_no not in merged:
                merged[loan_no] = LoanRecord(
                    deal_id=deal_id, loan_no=loan_no, is_sub=is_sub
                )
            rec = merged[loan_no]

            for ci, field_name in col_map.items():
                if field_name == "property_name":
                    pass  # handled separately below
                actual_ci = ci + col_offset
                if actual_ci < len(cells):
                    val = cells[actual_ci].strip()
                    if val and val.upper() not in ("", "NAV", "NAP"):
                        # only set if not already set (first sub-table wins
                        # for a field, others are typically blank for sub-rows)
                        if field_name not in rec.data or not rec.data[field_name]:
                            rec.data[field_name] = val

            # always grab property name from the known position
            name_ci = col_map.get("property_name")
            if name_ci is not None:
                name_ci_actual = name_ci if col_offset == 0 else name_ci + col_offset
            else:
                # fallback: cell index 1 (file2/4) or 2 (file5)
                name_ci_actual = 1 + col_offset
            if name_ci_actual < len(cells):
                name_val = _clean_str(cells[name_ci_actual])
                if name_val and "property_name" not in rec.data:
                    rec.data["property_name"] = name_val

    return list(merged.values())


# ── SQLite ───────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS loans (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id               TEXT NOT NULL,
    loan_no               TEXT NOT NULL,
    is_sub_property       INTEGER NOT NULL DEFAULT 0,
    property_name         TEXT,
    seller                TEXT,
    address               TEXT,
    city                  TEXT,
    state                 TEXT,
    zip_code              TEXT,
    county                TEXT,
    general_property_type TEXT,
    specific_property_type TEXT,
    year_built            TEXT,
    original_balance      REAL,
    cutoff_balance        REAL,
    pct_of_pool           REAL,
    maturity_balance      REAL,
    gross_rate            REAL,
    net_rate              REAL,
    amort_type            TEXT,
    origination_date      TEXT,
    maturity_date         TEXT,
    appraised_value       REAL,
    cutoff_ltv            REAL,
    maturity_ltv          REAL,
    uw_noi_dscr           REAL,
    uw_ncf_dscr           REAL,
    uw_noi                REAL,
    uw_ncf                REAL,
    occupancy             REAL,
    num_units             REAL,
    unit_measure          TEXT,
    UNIQUE(deal_id, loan_no)
);
"""

NUM_FIELDS = {
    "original_balance", "cutoff_balance", "pct_of_pool", "maturity_balance",
    "gross_rate", "net_rate", "appraised_value", "cutoff_ltv", "maturity_ltv",
    "uw_noi_dscr", "uw_ncf_dscr", "uw_noi", "uw_ncf", "occupancy", "num_units",
}

STR_FIELDS = {
    "property_name", "seller", "address", "city", "state", "zip_code",
    "county", "general_property_type", "specific_property_type",
    "year_built", "amort_type", "origination_date", "maturity_date",
    "unit_measure",
}

ALL_FIELDS = sorted(NUM_FIELDS | STR_FIELDS)

def load_to_sqlite(records: list[LoanRecord], db_path: str = "./loans.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)

    for rec in records:
        row = {
            "deal_id": rec.deal_id,
            "loan_no": rec.loan_no,
            "is_sub_property": 1 if rec.is_sub else 0,
        }
        for f in ALL_FIELDS:
            raw = rec.data.get(f)
            if f in NUM_FIELDS:
                row[f] = _clean_num(raw) if raw else None
            else:
                row[f] = _clean_str(raw) if raw else None

        cols = list(row.keys())
        placeholders = ", ".join(":" + c for c in cols)
        col_str = ", ".join(cols)
        conn.execute(
            f"INSERT OR REPLACE INTO loans ({col_str}) VALUES ({placeholders})",
            row,
        )

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    conn.close()
    return total


# ── main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    all_records: list[LoanRecord] = []

    for path in sorted(glob.glob(os.path.join("./labeled_data", "*.tsv"))):
        recs = parse_file(path)
        deal = _deal_id_from_path(path)
        loans_only = [r for r in recs if not r.is_sub]
        subs = [r for r in recs if r.is_sub]
        print(f"{deal}: {len(loans_only)} loans, {len(subs)} sub-properties")
        all_records.extend(recs)

    total = load_to_sqlite(all_records)
    print(f"\nLoaded {total} rows into ./loans.db")
    print("Done. Quick check:")

    conn = sqlite3.connect("./loans.db")
    conn.row_factory = sqlite3.Row
    sample = conn.execute(
        "SELECT deal_id, loan_no, property_name, city, state, "
        "cutoff_balance, gross_rate, cutoff_ltv, uw_noi_dscr "
        "FROM loans WHERE is_sub_property = 0 LIMIT 5"
    ).fetchall()
    for r in sample:
        print(f"  {r['deal_id']}:{r['loan_no']} | {r['property_name']} | "
              f"{r['city']}, {r['state']} | bal={r['cutoff_balance']} | "
              f"rate={r['gross_rate']} | LTV={r['cutoff_ltv']} | "
              f"DSCR={r['uw_noi_dscr']}")
    conn.close()