from chunk_filing import parse_labeled_file, scan_rows, _split_cells
import glob, os

for path in sorted(glob.glob(os.path.join("./labeled_data", "*.tsv"))):
    rows = parse_labeled_file(path)
    scanned = scan_rows(rows)
    name = os.path.basename(path).replace(".tsv","")
    found = False
    for row in scanned:
        if row.label == "TABLE_ROW":
            cells = _split_cells(row.text)
            low = [c.lower().strip() for c in cells]
            # look for the actual Annex A-1 header row
            if any("property name" in c for c in low) and any("loan" in c for c in low[:3]):
                print(f"\n{name} — {len(cells)} columns")
                for i, c in enumerate(cells):
                    print(f"  [{i}] {c.strip()[:80]}")
                found = True
                break
    if not found:
        print(f"\n{name} — no Annex header row found")