import glob
import os

from chunk_filing import process_file


class DataLoader:
    def __init__(self, labeled_dir: str):
        self.labeled_dir = labeled_dir

    def load(self):
        chunks_by_file = {}
        all_loans = {}

        paths = sorted(
            glob.glob(os.path.join(self.labeled_dir, "*.tsv"))
        )

        for path in paths:
            deal_id, rows, loans, chunks = process_file(path)

            chunks_by_file[deal_id] = chunks
            all_loans.update(loans)

        return chunks_by_file, all_loans