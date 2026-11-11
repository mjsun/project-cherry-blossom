"""
Extract CMBS Annex A-1 loan tables from lines already in memory into SQLite.

Same parsing logic as extract_to_sqlite.py, but takes a filing's lines
directly (e.g. from ExtractLinesFromMemory/CleanPassFromMemory) instead of
reading a .tsv file from disk, and writes to the DB under
backend/ai_module/app/data/loans.db instead of the project root.
"""

import os
import re
import sqlite3

# Relative to this file's own location, not the process cwd, so it keeps
# working no matter where the app is launched from (local or cloud deploy).
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "loans.db")

LOAN_NO_RE = re.compile(r"^\d{1,3}(\.\d{1,2})?$")

# field name -> substring to look for in the header label (first match wins)
HEADER_RULES = [
    ("property_name",           "property name"),
    ("seller",                  "mortgage loan seller"),
    ("address",                 "address"),
    ("city",                    "city"),
    ("state",                   "state"),
    ("zip_code",                "zip code"),
    ("general_property_type",   "general property type"),
    ("specific_property_type",  "specific property type"),
    ("year_built",              "year built"),
    ("year_renovated",          "year renovated"),
    ("num_units",               "number of units"),
    ("unit_measure",            "unit of measure"),
    ("original_balance",        "original balance ($)"),
    ("cutoff_balance",          "cut-off date balance ($)"),
    ("pct_of_pool",             "% of aggregate cut-off"),
    ("maturity_balance",        "ard balloon payment"),
    ("gross_rate",              "gross mortgage rate"),
    ("net_rate",                "net mortgage rate"),
    ("amort_type",              "amortization type"),
    ("origination_date",        "origination date"),
    ("maturity_date",           "maturity date or anticip"),
    ("appraised_value",         "appraised value"),
    ("cutoff_ltv",              "cut-off date ltv ratio"),
    ("maturity_ltv",            "ltv ratio at maturity"),
    ("uw_noi_dscr",             "uw noi dscr"),
    ("uw_ncf_dscr",             "uw ncf dscr"),
    ("uw_noi",                  "uw net operating income"),
    ("uw_ncf",                  "uw net cash flow"),
    ("occupancy",               "occupancy rate"),
]

FIELDS = [f for f, _ in HEADER_RULES]

NUMERIC = {
    "year_built", "year_renovated", "num_units", "original_balance",
    "cutoff_balance", "pct_of_pool", "maturity_balance", "gross_rate",
    "net_rate", "appraised_value", "cutoff_ltv", "maturity_ltv",
    "uw_noi_dscr", "uw_ncf_dscr", "uw_noi", "uw_ncf", "occupancy",
}

# Header columns that individual data rows may leave out entirely.
# Coop loans carry the Coop columns, non-coop loans don't; portfolio
# loans carry the cross-collateral flag, single-property loans don't.
OPTIONAL_COLS = (
    "cross collateralized", "coop - coop units", "coop - sponsor/investor",
    "coop- rental value", "coop - ltv as rental", "coop - unsold percent",
    "coop - sponsor units", "coop - investor units",
)

# Loan-level fields. Sub-property rows omit columns mid-row in the
# financial tables, so these are only trusted from parent loan rows.
PARENT_ONLY = {
    "original_balance", "cutoff_balance", "pct_of_pool", "maturity_balance",
    "gross_rate", "net_rate", "amort_type", "origination_date",
    "maturity_date", "appraised_value", "cutoff_ltv", "maturity_ltv",
    "uw_noi_dscr", "uw_ncf_dscr", "uw_noi", "uw_ncf", "occupancy",
}

STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
}


class ExtractToSqliteFromMemory:
    """Extract loan-table records from a filing's lines already in memory
    and upsert them into the shared loans.db SQLite database."""

    def __init__(self, lines, deal_id: str, db_path: str = DB_PATH):
        self.lines = lines
        self.deal_id = deal_id
        self.db_path = db_path

    @staticmethod
    def _split_cells(line):
        line = re.sub(r"\s*TABLE_(ROW|TITLE)\s*$", "", line)
        return [c.strip() for c in line.split("|")]

    @staticmethod
    def _is_header(line):
        return "Mortgage Loan Number" in line and line.count("|") >= 3

    @staticmethod
    def _build_col_map(header_cells):
        """position -> field name, first match wins per field."""
        col_map = {}
        taken = set()
        for i, label in enumerate(header_cells):
            low = label.lower()
            if "whole loan" in low:       # whole-loan variants are separate metrics
                continue
            for field, keyword in HEADER_RULES:
                if field in taken:
                    continue
                if keyword in low:
                    col_map[i] = field
                    taken.add(field)
                    break
        return col_map

    @staticmethod
    def _drop_optional(fields, labels, count):
        """Remove the first `count` optional header columns."""
        kept_f, kept_l, dropped = [], [], 0
        for f, l in zip(fields, labels):
            low = l.lower()
            if (dropped < count
                    and any(o in low for o in OPTIONAL_COLS)
                    and "maturity date" not in low):
                dropped += 1
                continue
            kept_f.append(f)
            kept_l.append(l)
        return kept_f, kept_l

    def _align_fields(self, header_cells, col_map, cells, offset):
        """Map each data position to a field name for one row."""
        n_data = len(cells) - offset
        fields = [col_map.get(i) for i in range(len(header_cells))]
        labels = list(header_cells)
        n_optional = sum(
            1 for l in labels
            if any(o in l.lower() for o in OPTIONAL_COLS)
            and "maturity date" not in l.lower()
        )

        # A row may carry an optional column or leave it out, independently of
        # how many trailing columns it has. If the table has a state column,
        # it pins the alignment: only one candidate puts a real state code there.
        if any(f == "state" for f in fields):
            for count in range(n_optional + 1):
                cand_f, _ = self._drop_optional(fields, labels, count)
                if "state" not in cand_f:
                    continue
                pos = cand_f.index("state") + offset
                if pos < len(cells) and cells[pos].upper() in STATES:
                    return cand_f

        # Otherwise assume the row left out as many optional columns as it is
        # short by.
        gap = len(header_cells) - n_data
        if gap > 0:
            fields, labels = self._drop_optional(fields, labels, gap)

        return fields

    def _parse_lines(self):
        lines = self.lines
        header_lines = [i for i, l in enumerate(lines) if self._is_header(l)]
        merged = {}
        known_loans = None   # real loan numbers, locked in from the first sub-table

        for idx, h in enumerate(header_lines):
            header_cells = self._split_cells(lines[h])
            col_map = self._build_col_map(header_cells)
            end = header_lines[idx + 1] if idx + 1 < len(header_lines) else len(lines)

            for k in range(h + 1, end):
                cells = self._split_cells(lines[k])
                if len(cells) < 3:
                    continue

                # loan number is in cell 0, or cell 1 behind a Loan/Property flag
                offset = 0
                if cells[0].lower() in ("loan", "property") and len(cells) > 1:
                    offset = 1
                loan_no = cells[offset]
                if not LOAN_NO_RE.match(loan_no):
                    continue

                # Later in the filing, unrelated statistical tables (loan term
                # buckets, etc.) can also look like loan rows. Only the first
                # sub-table is trusted to define which loan numbers are real.
                if known_loans is not None and loan_no not in known_loans:
                    continue

                is_sub = "." in loan_no
                rec = merged.setdefault(loan_no, {})
                rec["loan_no"] = loan_no
                rec["is_sub_property"] = 1 if is_sub else 0

                fields = self._align_fields(header_cells, col_map, cells, offset)
                for pos, field in enumerate(fields):
                    if not field:
                        continue
                    if is_sub and field in PARENT_ONLY:
                        continue
                    ci = pos + offset
                    if ci >= len(cells):
                        break
                    val = cells[ci]
                    if not val or val.upper() in ("NAV", "NAP", "N/A"):
                        continue
                    if not rec.get(field):          # first sub-table wins
                        rec[field] = val

            if known_loans is None:
                known_loans = set(merged.keys())

        return list(merged.values())

    @staticmethod
    def _to_number(val):
        try:
            return float(val.replace(",", "").replace("%", "").replace("$", ""))
        except (ValueError, AttributeError):
            return None

    def extract(self):
        """Parse this filing's lines into loan-table records."""
        return self._parse_lines()

    def store(self):
        """Parse, then upsert records into loans.db. Returns the records parsed."""
        records = self.extract()

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)

        cols = ", ".join(
            f"{f} {'REAL' if f in NUMERIC else 'TEXT'}" for f in FIELDS
        )
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS loans (
                deal_id TEXT,
                loan_no TEXT,
                is_sub_property INTEGER,
                {cols},
                PRIMARY KEY (deal_id, loan_no)
            )
        """)

        insert_cols = ["deal_id", "loan_no", "is_sub_property"] + FIELDS
        sql = (f"INSERT OR REPLACE INTO loans ({','.join(insert_cols)}) "
               f"VALUES ({','.join('?' * len(insert_cols))})")

        rows = []
        for rec in records:
            row = [self.deal_id, rec["loan_no"], rec["is_sub_property"]]
            for f in FIELDS:
                val = rec.get(f)
                row.append(self._to_number(val) if f in NUMERIC and val else val)
            rows.append(row)

        conn.executemany(sql, rows)
        conn.commit()

        for col in ("state", "general_property_type", "cutoff_balance"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON loans({col})")
        conn.commit()
        conn.close()

        loans = sum(1 for r in records if not r["is_sub_property"])
        print(f"{self.deal_id}: {len(records)} rows ({loans} loans, "
              f"{len(records) - loans} sub-properties)")

        return records
