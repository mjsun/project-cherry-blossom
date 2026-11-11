class LoanIndex:
    def __init__(self, chunks_by_file):
        self.chunks_by_file = chunks_by_file
        self.index = self._build_index()

    def _build_index(self):
        index = {}

        for deal_id, chunks in self.chunks_by_file.items():
            for chunk in chunks:
                for loan_key in chunk.loan_keys:
                    index.setdefault(loan_key, []).append(
                        (chunk.deal_id, chunk.index)
                    )

        return index

    def resolve(self, loan_keys):
        positions = []

        for key in loan_keys:
            positions.extend(self.index.get(key, []))

        seen = set()
        result = []

        for position in positions:
            if position not in seen:
                seen.add(position)
                result.append(position)

        return result