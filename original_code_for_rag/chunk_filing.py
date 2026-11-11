"""
Chunking + loan-tagging processor for labeled CMBS filing files.

Input: a folder of .tsv files, one labeled filing each, tab-separated:
    <text>\t<label>
Line numbers come from position in the file (1-indexed).

Labels seen in the data: COVER, BODY, SECTION, SUBSECTION, TERM,
TABLE_TITLE, TABLE_ROW, FOOTNOTE, NOISE

Pipeline per file:
    scan_rows             mark which lines are rows of the big loan table
    extract_loan_metadata loan number -> property name / seller / address
    chunk_rows            group lines into chunks (loan table: one per row)
    tag_chunks_with_loans attach "<deal>:<loan_no>" keys to each chunk

The deal prefix on each key is what makes it unique: loan numbers restart
at 1 in every filing, so "2" alone is ambiguous across deals.

Each chunk also keeps its own file + position (deal_id, index), so at
grounding time you can pull back a window of neighboring chunks from the
same file instead of passing a single chunk -- or the whole file -- to
the LLM. See get_local_context().
"""

import os
import re
import glob
from dataclasses import dataclass, field

LOAN_NO_CELL_RE = re.compile(r"^\d+(?:\.\d+)?$")   # "1", "23", "15.09"
GENERIC_NAMES = {"various", "n/a", "", "-"}        # unsafe to match in prose

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class Row:
    """One source line, plus what scan_rows worked out about it."""
    line_num: int
    text: str
    label: str
    cells: list = None       # pipe-split cells, for table lines
    cols: dict = None        # loan-table column layout, while inside one
    header: str = ""         # that table's header line
    loan_no: str = ""        # set when this line is one loan's data row
    is_header: bool = False  # set when this line IS a loan-table header

@dataclass
class Chunk:
    label: str
    lines: list = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    loan_keys: list = field(default_factory=list)         # ["WFRBS-2013-C13:1.01"]
    parent_loan_keys: list = field(default_factory=list)  # parent of a sub-loan
    header: str = ""          # column headers, for a single loan-table row
    row_loan_no: str = ""     # that row's own loan number
    deal_id: str = ""         # which file this chunk came from
    index: int = 0            # this chunk's position in that file's chunk list

    def text(self) -> str:
        return "\n".join(self.lines)

    def embedding_text(self) -> str:
        """
        What goes to the embedding model: loan tag first (so chunks about the
        same loan land near each other), then column headers for a lifted
        table row (without them the row is bare numbers), then the text.
        """
        parts = []
        if self.loan_keys:
            parts.append(f"[Loans: {', '.join(self.loan_keys)}]")
        if self.header:
            parts.append(f"Columns: {self.header}")
        parts.append(self.text())
        return "\n".join(parts)

# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def parse_labeled_file(path: str):
    """Read <text>\t<label> lines into (line_num, text, label) tuples."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, start=1):
            raw = raw.rstrip("\n")
            if not raw.strip() or "\t" not in raw:
                continue
            # Label is the final field; the text may itself contain tabs.
            text, label = raw.rsplit("\t", 1)
            rows.append((line_num, text, label.strip()))
    return rows

def deal_id_from_filename(path: str) -> str:
    """"WFRBS-2013-C13.tsv" -> "WFRBS-2013-C13"."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[\s_]+", "-", stem.strip())

# ---------------------------------------------------------------------------
# scan_rows: find the big loan table
# ---------------------------------------------------------------------------

def _split_cells(text: str):
    return [c.strip() for c in text.split("|")]

def _find_loan_tape_columns(cells):
    """
    Locate the loan-number / property-name / seller / address columns in a
    candidate header row, or return None if this isn't a loan-table header.

    Matched loosely because column names differ per filing:
    "LOAN # | SELLER | PROPERTY NAME | STREET ADDRESS" in one,
    "Mortgage Loan Number | Property Name | Mortgage Loan Seller" in another.
    """
    idx = {"loan": None, "name": None, "seller": None, "addr": None}
    for i, cell in enumerate((c.lower() for c in cells)):
        if idx["loan"] is None and ("loan number" in cell or "loan #" in cell):
            idx["loan"] = i
        elif idx["name"] is None and "property name" in cell:
            idx["name"] = i
        elif idx["seller"] is None and "seller" in cell:
            idx["seller"] = i
        elif idx["addr"] is None and ("street address" in cell or cell == "address"):
            idx["addr"] = i
    # Loan number + property name are the identifying pair, and they repeat
    # in every slice of the table. Without both, this isn't the loan table.
    return idx if idx["loan"] is not None and idx["name"] is not None else None

def _is_bare_loan_row(cells):
    """
    Some filings' loan table has no header row at all. Every row instead
    starts with the literal word "Loan", then the loan number, then the
    property name, by fixed position -- not by column name:
        Loan | 2 | 32 Avenue of the Americas (33)(36) | 7.3% | ...
    """
    return (len(cells) >= 3
            and cells[0].strip().lower() == "loan"
            and LOAN_NO_CELL_RE.match(cells[1].strip()))

def scan_rows(rows):
    """
    Walk the lines once and mark the loan table.

    Two row styles, checked in this order:
      - a bare loan row: starts with the word "Loan", no header needed --
        recognized on its own, every time it appears.
      - the header-based style: a slice header names its "loan number"/
        "property name" columns, and rows after it are identified by
        content (loan-number cell holds a number) because the same row can
        be labeled TABLE_ROW, TABLE_TITLE, BODY or TERM.
    """
    out, cols, header = [], None, ""

    for line_num, text, label in rows:
        row = Row(line_num, text, label)

        if label == "NOISE":
            out.append(row)       # page footers interrupt the table; ignore
            continue

        if "|" not in text:
            cols, header = None, ""    # prose: we've left the table
            out.append(row)
            continue

        row.cells = _split_cells(text)

        if _is_bare_loan_row(row.cells):
            # Self-describing row -- doesn't need or touch header tracking.
            row.loan_no = row.cells[1].strip()
            row.cols = {"loan": 1, "name": 2, "seller": None, "addr": None}
            out.append(row)
            continue

        found = _find_loan_tape_columns(row.cells)

        if found is not None:                      # a slice header
            cols, header = found, text
            row.cols, row.header, row.is_header = cols, header, True
        elif cols is not None and cols["loan"] < len(row.cells) \
                and LOAN_NO_CELL_RE.match(row.cells[cols["loan"]]):
            row.loan_no = row.cells[cols["loan"]]  # one loan's data row
            row.cols, row.header = cols, header
        else:
            cols, header = None, ""                # totals/footnote: slice ends

        out.append(row)

    return out

# ---------------------------------------------------------------------------
# extract_loan_metadata
# ---------------------------------------------------------------------------

def _new_loan_record(deal_id: str, loan_no: str) -> dict:
    return {
        "loan_key": f"{deal_id}:{loan_no}",
        "deal_id": deal_id,
        "loan_no": loan_no,
        "property_name": None,
        "seller": None,
        "street_address": None,
        # "15.09" is a sub-property of loan "15"; keep the link so a query
        # about the parent can optionally pull its children.
        "parent_loan_key": f"{deal_id}:{loan_no.split('.')[0]}" if "." in loan_no else None,
    }

def _cell(cells, cols, which):
    """Cell value for a named column, or None if absent/generic."""
    i = cols.get(which)
    if i is None or i >= len(cells):
        return None
    value = cells[i]
    return None if value.lower() in GENERIC_NAMES else value

def extract_loan_metadata(scanned, deal_id: str):
    """Build {loan_key: record} from the loan table's rows."""
    loans = {}
    for row in scanned:
        if not row.loan_no:
            continue
        record = loans.setdefault(f"{deal_id}:{row.loan_no}",
                                 _new_loan_record(deal_id, row.loan_no))
        # Each slice carries different columns, so fill from whichever
        # slice first provides a given field.
        for field_name, column in (("property_name", "name"),
                                   ("seller", "seller"),
                                   ("street_address", "addr")):
            if record[field_name] is None:
                record[field_name] = _cell(row.cells, row.cols, column)
    return loans

# ---------------------------------------------------------------------------
# chunk_rows
# ---------------------------------------------------------------------------

def chunk_rows(scanned):
    """
    Group lines into chunks:
      - NOISE and loan-table headers are not chunks of their own (the header
        rides along on each row chunk instead).
      - Each loan-table row becomes its OWN chunk. Kept whole, one slice
        covers every loan in the deal: too big for context, and retrieved
        for any loan question.
      - TABLE_TITLE opens a table chunk; TABLE_ROW joins the open one.
      - Otherwise consecutive same-label lines merge; a label change splits.
    """
    chunks, current = [], None

    for row in scanned:
        if row.label == "NOISE" or row.is_header:
            current = None
            continue

        if row.loan_no:
            chunks.append(Chunk("LOAN_ROW", [row.text], row.line_num, row.line_num,
                                header=row.header, row_loan_no=row.loan_no))
            current = None
            continue

        joins_open_table = row.label == "TABLE_ROW" and current is not None \
            and current.label == "TABLE_TITLE"
        continues_run = current is not None and current.label == row.label \
            and row.label != "TABLE_TITLE"

        if joins_open_table or continues_run:
            current.lines.append(row.text)
            current.end_line = row.line_num
        else:
            # A stray TABLE_ROW with no title still gets its own table chunk.
            label = "TABLE_TITLE" if row.label == "TABLE_ROW" else row.label
            current = Chunk(label, [row.text], row.line_num, row.line_num)
            chunks.append(current)

    return chunks

# ---------------------------------------------------------------------------
# tag_chunks_with_loans
# ---------------------------------------------------------------------------

# "Loan No. 23", "Loan Nos. 1, 3 and 24", "Loan #264" all appear.
LOAN_REF_RE = re.compile(
    r"Loan\s*(?:Nos?\.|#)\s*"
    r"(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*(?:\s*and\s*\d+(?:\.\d+)?)?)"
)

def _build_alias_table(loans):
    """
    Property name -> loan key, longest names first so a specific name wins
    over a shorter one contained inside it. Short names are skipped: they
    collide with ordinary prose.
    """
    aliases = [(rec["property_name"], key) for key, rec in loans.items()
               if rec["property_name"] and len(rec["property_name"]) >= 12]
    return sorted(aliases, key=lambda pair: -len(pair[0]))

def _keys_from_numbers(text, deal_id, known):
    """
    Loan keys from numeric references, checked against this deal's own loans.
    Filings cite other securitizations' loan numbers in their repurchase
    footnotes -- "Loan #264 GM&O Building" belongs to a different trust --
    so an unknown number is dropped. With no loan table to check against,
    nothing is dropped.
    """
    keys = []
    for match in LOAN_REF_RE.finditer(text):
        numbers = match.group(1).replace(" and ", ", ").split(",")
        for number in (n.strip() for n in numbers if n.strip()):
            key = f"{deal_id}:{number}"
            if not known or key in known:
                keys.append(key)
    return keys

def _keys_from_names(text, aliases):
    """Loan keys from property names mentioned without their number."""
    return [key for name, key in aliases
            if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE)]

def _dedupe(items):
    seen = set()
    return [x for x in items if not (x in seen or seen.add(x))]

def tag_chunks_with_loans(chunks, loans, deal_id: str, match_names: bool = True):
    """Attach loan keys (and any parent keys) to every chunk."""
    known = set(loans)
    aliases = _build_alias_table(loans) if match_names else []

    for chunk in chunks:
        if chunk.row_loan_no:
            # A loan-table row states its own loan in column one -- no
            # scanning, and its other cells may name unrelated things.
            chunk.loan_keys = [f"{deal_id}:{chunk.row_loan_no}"]
        else:
            text = chunk.text()
            chunk.loan_keys = _dedupe(_keys_from_numbers(text, deal_id, known)
                                      + _keys_from_names(text, aliases))

        chunk.parent_loan_keys = sorted({
            parent for key in chunk.loan_keys
            if (parent := loans.get(key, {}).get("parent_loan_key"))
        })

    return chunks

# ---------------------------------------------------------------------------
# get_local_context: grounding window around a retrieved chunk
# ---------------------------------------------------------------------------

def get_local_context(chunks, index, before=1, after=1):
    """
    Text of the chunks around `index` in the same file -- expanded by whole
    chunks, not raw lines, so the window never cuts a sentence or a row in
    half. This is what should go to the LLM for grounding, instead of a
    single chunk or the whole file.
    """
    lo = max(0, index - before)
    hi = min(len(chunks), index + after + 1)
    return "\n\n".join(chunks[i].text() for i in range(lo, hi))

# ---------------------------------------------------------------------------
# Folder processor
# ---------------------------------------------------------------------------

def process_file(path: str):
    """Run the pipeline on one file; return (deal_id, rows, loans, chunks)."""
    deal_id = deal_id_from_filename(path)
    rows = parse_labeled_file(path)
    scanned = scan_rows(rows)
    loans = extract_loan_metadata(scanned, deal_id)
    chunks = chunk_rows(scanned)
    tag_chunks_with_loans(chunks, loans, deal_id)

    for i, chunk in enumerate(chunks):
        chunk.deal_id = deal_id
        chunk.index = i

    return deal_id, rows, loans, chunks

def _print_summary(path, deal_id, rows, loans, chunks):
    tagged = [c for c in chunks if c.loan_keys]
    print("=" * 70)
    print(f"{os.path.basename(path)}   deal_id={deal_id}")
    print(f"  {len(rows)} lines -> {len(chunks)} chunks "
          f"({sum(1 for c in chunks if c.label == 'LOAN_ROW')} loan rows)")
    print(f"  loans found: {len(loans)}   chunks tagged: {len(tagged)}")

    if not loans:
        # Expected when a filing's extraction dropped the Annex A-1 table.
        print("  [warning] no loan table found -- numeric refs unvalidated")

    for rec in list(loans.values())[:4]:
        print(f"    {rec['loan_key']:<26} {str(rec['property_name'])[:32]:<34}"
              f" seller={rec['seller']}")
    for chunk in tagged[:3]:
        print(f"    [{chunk.label}] L{chunk.start_line} {chunk.loan_keys} :: "
              f"{chunk.text()[:60]}...")
    print()

def process_folder(folder: str):
    """Process every .tsv in the folder, printing a summary per file."""
    paths = sorted(glob.glob(os.path.join(folder, "*.tsv")))
    if not paths:
        print(f"No .tsv files found in {folder}")
        return
    for path in paths:
        _print_summary(path, *process_file(path))

# Folder of labeled .tsv files to process.
INPUT_DIR = "./labeled_data"

if __name__ == "__main__":
    process_folder(INPUT_DIR)