
import sys
from bs4 import BeautifulSoup

BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}

def clean(text):
    return " ".join(text.replace('\xa0', ' ').split()).strip()

def extract_lines(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style']):
        t.decompose()
    lines = []
    seen = set()

    for el in soup.find_all(['table'] + list(BLOCK_TAGS)):
        if el.name == 'table':
            for tr in el.find_all('tr'):
                cells = [clean(td.get_text(' ', strip=True)) for td in tr.find_all(['td', 'th'])]
                cells = [c for c in cells if c]

                row = ' | '.join(cells)
                if(row and row not in seen):
                    lines.append(row)
                    seen.add(row)
        else:
            if el.find('table'):
                continue
            txt = clean(el.get_text(" ", strip=True))
            if txt and txt not in seen:
                lines.append(txt)
                seen.add(txt)

    return lines


def main():
    input_path = 'sample_data/file6/file6.html'
    output_path = 'extracted_data/file6.txt'
    with open(input_path, encoding="cp1252") as f:
        html = f.read()
    lines = extract_lines(html)
    with open(output_path, 'w', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + '\n')

if __name__ == '__main__':
    main()

