import json
import sys
import ollama
import os
import re

MODEL = 'qwen2.5:14b'
BATCH = 10

LABELS = ["COVER", "SECTION", "SUBSECTION", "TERM", "BODY", "TABLE_TITLE", "TABLE_ROW", "FOOTNOTE", "NOISE"]

TOC = re.compile(r"\|\s*S-\d+\s*$")     
PAGE = re.compile(r"^S-\d+$")           
FOOTNOTE = re.compile(r"^\(\s*(?:\d+|Footnotes?)\b")
NAV = {"table of contents"}
LIST_ITEM = re.compile(r"^\(\s*[a-zxiv]{1,4}\s*\)\s", re.I)
TABLE_INTRO = re.compile(r"(following tables?|as set forth in the following|set forth below)", re.I)
BULLET = re.compile(r"^[\u2022\u25cf\*\-]\s*\|")  
SENT_END = (".", ";", ":", "’", "”", "’’", "‘‘")
NUMERIC_CELL = re.compile(
    r"^[\(\)\$]?\s*(?:"
    r"[\d,]+(?:\.\d+)?%?"                               
    r"|[A-Z][a-z]+ \d{1,2}, \d{4}"               
    r"|\d{4}"                           
    r"|[—–-]"               
    r")\s*[\)\%]?\s*(?:\(\d+\))?$"
)


def find_cover_end(lines):
    for i, ln in enumerate(lines):
        if ln.strip().lower() in NAV:     # "table of contents"
            return i
    return 0  

def _numeric_fraction(cells):
    if not cells:
        return 0.0
    n = sum(1 for c in cells if NUMERIC_CELL.match(c.strip()))
    return n/len(cells)

def _cells(line):
    return [c.strip() for c in line.split("|") if c.strip()]


def _is_term(line):
    """'Label | long explanatory text' -> a definition block."""
    cells = _cells(line)
    if len(cells) != 2:
        return False
    return len(cells[0]) <= 70 and len(cells[1]) >= 60

def _is_table_header(line):
    cells = _cells(line)
    if len(cells) < 4: return False
    if any(len(c) > 80 for c in cells): return False
    return _numeric_fraction(cells) <= 0.25

def _is_table_row(line):
    """A data row: >= 2 cells where the cells after the first are mostly numeric."""
    if "|" not in line:
        return False
    cells = [c.strip() for c in line.split("|") if c.strip()]

    if len(cells) < 2 :
        return False
    rest = cells[1:] 

    if any(len(c) > 60 for c in rest):
        return False

    fraction = _numeric_fraction(rest)
    return fraction >= 0.5 if len(cells) >= 4 else fraction >= 0.99     

def rule_label(line, idx=None, cover_end=0):
    s = line.strip()
    if not s:
        return "NOISE"
    if s.lower() in NAV:
        return "NOISE"
    if PAGE.match(s):
        return "NOISE"
    if TOC.search(s):
        return "NOISE"
    if BULLET.match(s):
        return "BODY"
    if FOOTNOTE.match(s):
        return "FOOTNOTE"
    if _is_table_header(s):
        return "TABLE_TITLE"
    if _is_table_row(s):
        return "TABLE_ROW"
    if _is_term(s):
        return "TERM"
    if LIST_ITEM.match(s):
        return "BODY"
    if TABLE_INTRO.search(s) and s.rstrip().endswith(":"):
        return "BODY"
    if _is_prose(s):
        return "BODY"
    if idx is not None and idx < cover_end:
        return "COVER"
    return None


def _is_prose(line):
    """Long, no table pipes, ends like a sentence -> running prose."""
    return "|" not in line and len(line) >= 150 and line.rstrip().endswith(SENT_END)
 

DEFINITIONS = """\
COVER       - front/title-page content: deal name, dollar amount, "PROSPECTUS SUPPLEMENT", sponsor/underwriter/depositor names, offering date, filing info.
SECTION     - a major section heading, e.g. "RISK FACTORS", "Description of the Mortgage Pool".
SUBSECTION  - a sub-heading under a section, e.g. "Hotel Properties Have Special Risks".
TERM        - a key->value definition block: a label plus its explanation, e.g. "Depositor | J.P. Morgan Chase Commercial Mortgage Securities Corp., a Delaware corporation...".
BODY        - a normal paragraph of running prose (usually a full sentence or more).
TABLE_TITLE - a table's caption OR its column-header row, e.g. "Overview of Grace Periods".
TABLE_ROW   - one row of table data.
FOOTNOTE    - a footnote line.
NOISE       - junk with no standalone meaning: nav links, stray fragments."""

PROMPT = """You label lines from a CMBS prospectus. Choose EXACTLY one label per line.
 
{defs}
 
Guidance:
- A short line that is a title with no verb is a heading (SECTION/SUBSECTION), not BODY.
- BODY must read as prose, normally a complete sentence.
- Identical-looking lines must get identical labels.
 
Return ONLY a JSON array of label strings, one per input line, in order.
Example: ["SECTION","BODY","TABLE_ROW"]
 
Lines:
{lines}"""


def label_batch(lines):
    numbered = "\n".join(f"{i+1}. {ln}" for i, ln in enumerate(lines))

    prompt = PROMPT.format(defs=DEFINITIONS, lines=numbered)

    res = ollama.chat(
        model=MODEL,
        messages=[{'role': 'user', 'content': prompt}],
        options = {'temperature': 0},
    )

    text = res['message']['content'].strip()

    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("no JSON array in reply")
    
    labels = [str(x).strip().upper() for x in json.loads(text[start:end + 1])]
    return [x if x in LABELS else "BODY" for x in labels]


def main():

    input_path = sys.argv[1] if len(sys.argv) > 1 else 'cleaned_data/file6.txt'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'labeled_data/file6.tsv'
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(input_path, encoding='utf-8') as f:
        lines = [ln.rstrip('\n') for ln in f if ln.strip()]

    cover_end = find_cover_end(lines)
    labels = [rule_label(ln, i, cover_end) for i, ln in enumerate(lines)]
    todo = [i for i, l in enumerate(labels) if l is None]

    print(f"rules labeled {len(lines)-len(todo)} / {len(lines)} "
          f"({100*(len(lines)-len(todo))/len(lines):.0f}%) "
          f"-> {len(todo)} lines to the model")

    for i in range(0, len(todo), BATCH):
        idxs = todo[i:i + BATCH]
        batch = [lines[i] for i in idxs]
        try:
            todo_labels= label_batch(batch)
        except Exception as e:
            print(f"batch at {i} failed ({e}) -> defaulting to BODY")
            todo_labels = ["BODY"] * len(batch)
        if len(todo_labels) < len(batch):
            todo_labels += ["BODY"] * (len(batch) - len(todo_labels))
        elif len(todo_labels) > len(batch):
            todo_labels = todo_labels[:len(batch)]
        for m, l in zip(idxs, todo_labels):
            labels[m] = l
        print(f"model-labeled {min(i+BATCH, len(todo))} / {len(todo)}")

    with open(output_path, 'w', encoding='utf-8') as f:
        for ln, l in zip(lines, labels):
            f.write(f"{ln}\t{l}\n")

    counts = {}
    for lab in labels:
        counts[lab] = counts.get(lab, 0) + 1
    print(f"\nwrote {len(lines)} rows -> {output_path}")
    for lab in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {lab:<12} {counts[lab]}")

if __name__ == '__main__':
    main()