import glob
import os
import re

from backend.ai_module.app.file_ingestion.chunk_filing_from_memory import ChunkFilingFromMemory


class DataLoader:
    def __init__(self, labeled_dir: str):
        self.labeled_dir = labeled_dir

    @staticmethod
    def _deal_id_from_filename(path: str) -> str:
        """"WFRBS-2013-C13.tsv" -> "WFRBS-2013-C13"."""
        stem = os.path.splitext(os.path.basename(path))[0]
        return re.sub(r"[\s_]+", "-", stem.strip())

    @staticmethod
    def _read_labeled_lines(path: str):
        """Read <text>\t<label> lines into (text, label) pairs."""
        labeled_lines = []
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.rstrip("\n")
                if not raw.strip() or "\t" not in raw:
                    continue
                # Label is the final field; the text may itself contain tabs.
                text, label = raw.rsplit("\t", 1)
                labeled_lines.append((text, label.strip()))
        return labeled_lines

    def load(self):
        chunks_by_file = {}
        all_loans = {}

        paths = sorted(
            glob.glob(os.path.join(self.labeled_dir, "*.tsv"))
        )

        for path in paths:
            deal_id = self._deal_id_from_filename(path)
            labeled_lines = self._read_labeled_lines(path)

            loans, chunks = ChunkFilingFromMemory(labeled_lines, deal_id).process()

            chunks_by_file[deal_id] = chunks
            all_loans.update(loans)

        return chunks_by_file, all_loans
