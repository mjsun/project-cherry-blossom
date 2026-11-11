import re

PAGE_MARKER = re.compile(r"^S-\d+$")


class CleanPassFromMemory:
    """Same cleaning logic as clean_pass.py, but operates on an in-memory list
    of lines instead of reading from a file on disk."""

    def __init__(self, lines):
        self.lines = lines

    @staticmethod
    def clean_row(line):
        if ' | ' not in line:
            return line.strip()

        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c not in ('$', '%', '')]
        out = ' | '.join(cells)
        out = re.sub(r"\(\s*([\d,]+)\s*\|\s*\)", r"(\1)", out)
        out = re.sub(r"\(\s*([\d,]+)\s*\)", r"(\1)", out)
        out = re.sub(r"([\d.]+)\s*\|\s*%", r"\1%", out)
        return out

    def clean(self):
        cleaned = []
        for raw in self.lines:
            s = raw.strip()
            if not s or PAGE_MARKER.match(s):
                continue
            cleaned.append(self.clean_row(raw.rstrip('\n')))
        return cleaned
