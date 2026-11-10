from bs4 import BeautifulSoup

BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}


class ExtractLinesFromMemory:
    """Same extraction logic as extract_lines.py, but operates on an HTML string
    already in memory instead of reading it from a file on disk."""

    def __init__(self, html: str):
        self.html = html

    @staticmethod
    def clean(text):
        return " ".join(text.replace('\xa0', ' ').split()).strip()

    def extract(self):
        soup = BeautifulSoup(self.html, 'html.parser')
        for t in soup(['script', 'style']):
            t.decompose()

        lines = []
        seen = set()

        for el in soup.find_all(['table'] + list(BLOCK_TAGS)):
            if el.name == 'table':
                for tr in el.find_all('tr'):
                    cells = [self.clean(td.get_text(' ', strip=True)) for td in tr.find_all(['td', 'th'])]
                    cells = [c for c in cells if c]

                    row = ' | '.join(cells)
                    if row and row not in seen:
                        lines.append(row)
                        seen.add(row)
            else:
                if el.find('table'):
                    continue
                txt = self.clean(el.get_text(" ", strip=True))
                if txt and txt not in seen:
                    lines.append(txt)
                    seen.add(txt)

        return lines
