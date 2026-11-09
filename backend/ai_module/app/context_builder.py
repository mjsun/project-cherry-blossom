from chunk_filing import get_local_context


class ContextBuilder:
    def __init__(self, chunks_by_file):
        self.chunks_by_file = chunks_by_file

    def build(
        self,
        positions,
        before: int = 1,
        after: int = 1,
    ):
        blocks = []

        for deal_id, index in positions:
            chunks = self.chunks_by_file.get(deal_id, [])

            if index >= len(chunks):
                continue

            chunk = chunks[index]

            window = get_local_context(
                chunks,
                index,
                before=before,
                after=after,
            )

            blocks.append(
                f"[{deal_id} lines "
                f"{chunk.start_line}-{chunk.end_line}]\n"
                f"{window}"
            )

        return "\n\n---\n\n".join(blocks)