from chunk_filing import get_local_context


class ContextBuilder:
    def __init__(self, chunks_by_file):
        self.chunks_by_file = chunks_by_file

    def build(
        self,
        positions,
        before: int = 1,
        after: int = 1,
        fallback_docs=None,
    ):
        fallback_docs = fallback_docs or {}
        blocks = []

        for deal_id, index in positions:
            chunks = self.chunks_by_file.get(deal_id, [])

            if index < len(chunks):
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
                continue

            # Not loaded from a local labeled .tsv (e.g. ingested straight
            # into the vector DB) -- fall back to Chroma's own stored text.
            document = fallback_docs.get((deal_id, index))
            if document is not None:
                blocks.append(f"[{deal_id}]\n{document}")

        return "\n\n---\n\n".join(blocks)