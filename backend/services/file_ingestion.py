from urllib.parse import urlparse
import httpx
from fastapi import HTTPException


class FileIngestionService:
    def loadFileByUrl(self, url):
        try:
            headers = {"User-Agent": "CMBS-QA bot (contact: mingjiesun1984@gmail.com)"}
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=400, detail=f"Failed to fetch link: {exc}") 

        return response