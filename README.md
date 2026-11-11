# Project Cherry Blossom

## Backend (Docker)

By default the backend uses **Ollama** as the LLM provider. This is set in
`backend/.env`:

```
LLM_PROVIDER=ollama
```

To switch to OpenAI instead, change it to `LLM_PROVIDER=openai` and make sure
`OPENAI_API_KEY` is also set in that same file. Each provider reads/writes
its own Chroma collection (`cmbs_filing_ollama` / `cmbs_filing_openai`), so
switching providers won't wipe out the other's vector data.

If using Ollama, make sure it's running on your Mac first:

```bash
ollama serve
```
(skip if it's already running as a background app)

### Start

```bash
./run_docker.sh
```

This builds the image and starts a container named `cherry-blossom-backend`,
reachable at `http://localhost:8000` (docs at `http://localhost:8000/docs`).

### Stop

```bash
docker stop cherry-blossom-backend
```

## Frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

This starts the Vite dev server (default `http://localhost:5173`), which
talks to the backend at `http://localhost:8000` by default.

### Stop

Press `Ctrl+C` in the terminal running `npm run dev`.

## Data: Chroma DB + SQLite

The backend stores data in two local stores, neither of which is seeded by
default:

- **Chroma DB** (`backend/ai_module/app/data/chroma_db`) — vector embeddings
  of filing text, used for retrieval/Q&A. Split per provider into
  `cmbs_filing_ollama` / `cmbs_filing_openai` collections (see above).
- **SQLite** (`loans.db`) — structured loan data extracted from filings.

On a fresh checkout/clone, both are empty. You need to ingest at least one
filing before querying will return anything useful. Ingestion is triggered
via the API:

```bash
curl -X POST http://localhost:8000/api/file_ingestion/ \
  -H "Content-Type: application/json" \
  -d '{"url": "<link to the filing document>"}'
```

This kicks off a background job and returns a `job_id`. Check progress with:

```bash
curl http://localhost:8000/api/file_ingestion/status/<job_id>
```

Ingestion runs several steps (extraction, chunking, labeling, embedding) and
calls the LLM provider repeatedly, so **it can take a while**, especially
with Ollama running locally on CPU. Let it finish before querying.

In the frontend, go to the **ingestion page** first, type in the file name
and URL, and ingest before asking questions on the query page.

## Demo Filings & Test Questions

Ingest a filing by passing its URL to the `/file/` endpoint, then ask its questions.
Include the series code in each question so retrieval stays within that deal.

> HRR = Horizontal Risk Retention: the lowest-rated certificate classes, which the
> sponsor's designee keeps to meet the risk retention rule.

---

### 1. MSBAM 2025-5C1 (term sheet)
**File:** `n4886_x3-ts.htm`
**URL:** https://www.sec.gov/Archives/edgar/data/2056713/000153949725000819/n4886_x3-ts.htm

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who is the depositor for MSBAM 2025-5C1? | Morgan Stanley Capital I Inc. |
| 2 | Who is the special servicer for MSBAM 2025-5C1? | Argentic Services Company LP |
| 3 | What is the initial pool balance of MSBAM 2025-5C1? | ~$934,609,352 |
| 4 | When is the expected closing date for MSBAM 2025-5C1? | March 20, 2025 |
| 5 | Who is the retaining sponsor for MSBAM 2025-5C1? | Argentic Real Estate Finance 2 LLC |

---

### 2. BMO 2024-5C7 (424B2 prospectus)
**File:** `n4562_x13-424b2.htm`
**URL:** https://www.sec.gov/Archives/edgar/data/0002038433/000153949724002197/n4562_x13-424b2.htm

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who is the depositor for BMO 2024-5C7? | BMO Commercial Mortgage Securities LLC |
| 2 | Who is the special servicer for BMO 2024-5C7? | Greystone Servicing Company LLC |
| 3 | What is the initial pool balance of BMO 2024-5C7? | $959,562,630 |
| 4 | Who is the HRR holder for BMO 2024-5C7? | 660 RR Holdings LLC |
| 5 | Who is the initial directing holder for BMO 2024-5C7? | 400 Capital Management, LLC |

---

### 3. BMO 2024-5C6 (424B2 prospectus)
**File:** `n4476_x13-424b2.htm`
**URL:** https://www.sec.gov/Archives/edgar/data/0002034419/000153949724001916/n4476_x13-424b2.htm

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who is the special servicer for BMO 2024-5C6? | LNR Partners, LLC |
| 2 | Who is the operating advisor for BMO 2024-5C6? | Pentalpha Surveillance LLC |
| 3 | What is the initial pool balance of BMO 2024-5C6? | $675,204,631 (32 mortgage loans) |
| 4 | When are the certificates for BMO 2024-5C6 expected to be delivered? | On or about September 26, 2024 |
| 5 | Who is expected to purchase the HRR certificates for BMO 2024-5C6? | CMBS 4 Sub 4, LLC |

---

### 4. BBCMS 2024-C28 (424B2 prospectus)
**File:** `n4385_x12-424b2.htm`
**URL:** https://www.sec.gov/Archives/edgar/data/0002030072/000153949724001624/n4385_x12-424b2.htm

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who is the depositor for BBCMS 2024-C28? | Barclays Commercial Mortgage Securities LLC |
| 2 | Who is the master servicer for BBCMS 2024-C28? | Wells Fargo Bank, National Association |
| 3 | What is the initial pool balance of BBCMS 2024-C28? | $804,920,408 |
| 4 | When is the first distribution date for BBCMS 2024-C28? | September 2024 |
| 5 | Who is the expected initial directing certificateholder for BBCMS 2024-C28? | CMBS 4 Sub 2, LLC |

---

### 5. BBCMS 2024-5C27 (424B2 prospectus)
**File:** `n4259_x13-424b2.htm`
**URL:** https://www.sec.gov/Archives/edgar/data/0002022685/000153949724001318/n4259_x13-424b2.htm

| # | Question | Expected Answer |
|---|----------|-----------------|
| 1 | Who is the special servicer for BBCMS 2024-5C27? | LNR Partners, LLC |
| 2 | What is the initial pool balance of BBCMS 2024-5C27? | $800,844,845 |
| 3 | Who is the retaining sponsor for BBCMS 2024-5C27? | Starwood Mortgage Capital LLC |
| 4 | Who is the expected initial directing certificateholder for BBCMS 2024-5C27? | LNR Securities Holdings, LLC |
| 5 | When are the certificates for BBCMS 2024-5C27 expected to be delivered? | On or about July 11, 2024 |

---

### Negative test (filing not ingested)
| Question | Expected Answer |
|----------|-----------------|
| Who is the special servicer for BANK5 2099-ZZ9? | "I don't have that filing. It hasn't been ingested yet." |
