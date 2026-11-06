import re
import sys


PAGE_MARKER = re.compile(r"^S-\d+$")

def clean_row(line):
    if ' | ' not in line:
        return line.strip()

    cells = [c.strip() for c in line.split('|')]
    cells = [c for c in cells if c not in('$', '%', '')]
    out = ' | '.join(cells)
    out = re.sub(r"\(\s*([\d,]+)\s*\|\s*\)", r"(\1)", out)
    out = re.sub(r"\(\s*([\d,]+)\s*\)", r"(\1)", out)
    out = re.sub(r"([\d.]+)\s*\|\s*%", r"\1%", out)
    return out

def main():
    input_path = 'extracted_data/file6.txt'
    output_path = 'cleaned_data/file6.txt'
    cleaned = []
    with open(input_path, encoding='utf-8') as f:
        for raw in f:
            s = raw.strip()
            if not s or PAGE_MARKER.match(s):
                continue
            cleaned.append(clean_row(raw.rstrip('\n')))

    with open(output_path, 'w', encoding='utf=8') as f:
        for ln in cleaned:
            f.write(ln + '\n')

if __name__ == '__main__':
    main()