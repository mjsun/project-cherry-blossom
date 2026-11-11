from chunk_filing import parse_labeled_file, scan_rows, _split_cells, _find_loan_tape_columns
import glob, os

for path in sorted(glob.glob(os.path.join("./labeled_data", "*.tsv"))):
    rows = parse_labeled_file(path)
    name = os.path.basename(path).replace(".tsv","")
    
    # scan raw rows for the header row _find_loan_tape_columns would match
    for i, row in enumerate(rows):
        cells = _split_cells(row.text)
        cols = _find_loan_tape_columns(cells)
        if cols is not None:
            print(f"\n{name} — header at line {row.line_no}, {len(cells)} columns")
            print(f"  col map: {cols}")
            # print the next data row
            if i + 1 < len(rows):
                data_cells = _split_cells(rows[i+1].text)
                for j, c in enumerate(data_cells):
                    print(f"  [{j}] {c.strip()[:80]}")
            break
    else:
        print(f"\n{name} — no header found by _find_loan_tape_columns")