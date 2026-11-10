from urllib.parse import urlparse
import httpx
from fastapi import HTTPException
from backend.ai_module.app.file_ingestion.extract_lines_from_memory import ExtractLinesFromMemory
from backend.ai_module.app.file_ingestion.clean_pass_from_memory import CleanPassFromMemory
from backend.ai_module.app.file_ingestion.label_lines_from_memory import LabelLinesFromMemory
from backend.ai_module.app.file_ingestion.chunk_filing_from_memory import ChunkFilingFromMemory
from backend.ai_module.app.file_ingestion.embed_and_store_from_memory import EmbedAndStoreFromMemory

class FileIngestionService:
    def _loadHTMLByUrl(self, url):
        try:
            headers = {"User-Agent": "CMBS-QA bot (contact: mingjiesun1984@gmail.com)"}
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Failed to fetch link: {exc}") 

        return response
    
    def loadFileByUrl(self, url):
        response = self._loadHTMLByUrl(url)
        html = response.text
        lines = ExtractLinesFromMemory(html).extract()
        cleaned = CleanPassFromMemory(lines).clean()
        labeled = LabelLinesFromMemory(cleaned[0:100]).label()
        deal_id = urlparse(url).path.rsplit("/", 1)[-1] or urlparse(url).netloc
        loans, chunks = ChunkFilingFromMemory(labeled, deal_id).process()
        collection, loan_index = EmbedAndStoreFromMemory(chunks).store()
        print('...collection is : ', collection)
        return "\n\n".join(f"[Chunk {chunk.index}]\n{chunk.text()}" for chunk in chunks)