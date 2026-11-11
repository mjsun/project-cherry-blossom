import re
from dataclasses import dataclass, field

LOAN_NO_CELL_RE = re.compile(r"^\d+(?:\.\d+)?$")   # "1", "23", "15.09"
GENERIC_NAMES = {"various", "n/a", "", "-"}        # unsafe to match in prose

# "Loan No. 23", "Loan Nos. 1, 3 and 24", "Loan #264" all appear.
LOAN_REF_RE = re.compile(
    r"Loan\s*(?:Nos?\.|#)\s*"
    r"(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*(?:\s*and\s*\d+(?:\.\d+)?)?)"
)


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
        parts = []
        if self.loan_keys:
            parts.append(f"[Loans: {', '.join(self.loan_keys)}]")
        if self.header:
            parts.append(f"Columns: {self.header}")
        parts.append(self.text())
        return "\n".join(parts)


class ChunkFilingFromMemory:

    def __init__(self, labeled_lines, deal_id: str):
        self.labeled_lines = labeled_lines
        self.deal_id = deal_id

    def _rows(self):
        return [
            (line_num, text, label)
            for line_num, (text, label) in enumerate(self.labeled_lines, start=1)
        ]

    @staticmethod
    def _split_cells(text: str):
        return [c.strip() for c in text.split("|")]

    @staticmethod
    def _find_loan_tape_columns(cells):
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
        return idx if idx["loan"] is not None and idx["name"] is not None else None

    @staticmethod
    def _is_bare_loan_row(cells):
        return (len(cells) >= 3
                and cells[0].strip().lower() == "loan"
                and LOAN_NO_CELL_RE.match(cells[1].strip()))

    def _scan_rows(self, rows):
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

            row.cells = self._split_cells(text)

            if self._is_bare_loan_row(row.cells):
                row.loan_no = row.cells[1].strip()
                row.cols = {"loan": 1, "name": 2, "seller": None, "addr": None}
                out.append(row)
                continue

            found = self._find_loan_tape_columns(row.cells)

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

    @staticmethod
    def _new_loan_record(deal_id: str, loan_no: str) -> dict:
        return {
            "loan_key": f"{deal_id}:{loan_no}",
            "deal_id": deal_id,
            "loan_no": loan_no,
            "property_name": None,
            "seller": None,
            "street_address": None,
            "parent_loan_key": f"{deal_id}:{loan_no.split('.')[0]}" if "." in loan_no else None,
        }

    @staticmethod
    def _cell(cells, cols, which):
        i = cols.get(which)
        if i is None or i >= len(cells):
            return None
        value = cells[i]
        return None if value.lower() in GENERIC_NAMES else value

    def _extract_loan_metadata(self, scanned, deal_id: str):
        loans = {}
        for row in scanned:
            if not row.loan_no:
                continue
            record = loans.setdefault(f"{deal_id}:{row.loan_no}",
                                       self._new_loan_record(deal_id, row.loan_no))
            for field_name, column in (("property_name", "name"),
                                        ("seller", "seller"),
                                        ("street_address", "addr")):
                if record[field_name] is None:
                    record[field_name] = self._cell(row.cells, row.cols, column)
        return loans

    @staticmethod
    def _chunk_rows(scanned):
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
                label = "TABLE_TITLE" if row.label == "TABLE_ROW" else row.label
                current = Chunk(label, [row.text], row.line_num, row.line_num)
                chunks.append(current)

        return chunks

    @staticmethod
    def _build_alias_table(loans):
        aliases = [(rec["property_name"], key) for key, rec in loans.items()
                   if rec["property_name"] and len(rec["property_name"]) >= 12]
        return sorted(aliases, key=lambda pair: -len(pair[0]))

    @staticmethod
    def _keys_from_numbers(text, deal_id, known):
        keys = []
        for match in LOAN_REF_RE.finditer(text):
            numbers = match.group(1).replace(" and ", ", ").split(",")
            for number in (n.strip() for n in numbers if n.strip()):
                key = f"{deal_id}:{number}"
                if not known or key in known:
                    keys.append(key)
        return keys

    @staticmethod
    def _keys_from_names(text, aliases):
        return [key for name, key in aliases
                if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE)]

    @staticmethod
    def _dedupe(items):
        seen = set()
        return [x for x in items if not (x in seen or seen.add(x))]

    def _tag_chunks_with_loans(self, chunks, loans, deal_id: str, match_names: bool = True):
        known = set(loans)
        aliases = self._build_alias_table(loans) if match_names else []

        for chunk in chunks:
            if chunk.row_loan_no:
                chunk.loan_keys = [f"{deal_id}:{chunk.row_loan_no}"]
            else:
                text = chunk.text()
                chunk.loan_keys = self._dedupe(
                    self._keys_from_numbers(text, deal_id, known)
                    + self._keys_from_names(text, aliases)
                )

            chunk.parent_loan_keys = sorted({
                parent for key in chunk.loan_keys
                if (parent := loans.get(key, {}).get("parent_loan_key"))
            })

        return chunks

    def process(self):
        """Run the pipeline; return (loans, chunks)."""
        rows = self._rows()
        scanned = self._scan_rows(rows)
        loans = self._extract_loan_metadata(scanned, self.deal_id)
        chunks = self._chunk_rows(scanned)
        self._tag_chunks_with_loans(chunks, loans, self.deal_id)

        for i, chunk in enumerate(chunks):
            chunk.deal_id = self.deal_id
            chunk.index = i

        return loans, chunks
