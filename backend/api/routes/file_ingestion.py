from fastapi import APIRouter, BackgroundTasks, HTTPException
from urllib.parse import urlparse

from backend.schema.file_ingestion_model import (
    FileIngestionRequest,
    FileIngestionStartResponse,
    FileIngestionStatusResponse,
)
from backend.services.file_ingestion import FileIngestionService
from backend.services import ingestion_jobs

router = APIRouter()


def _run_ingestion(job_id: str, url: str):
    fi = FileIngestionService()
    try:
        fi.loadFileByUrl(
            url,
            on_step=lambda step_index: ingestion_jobs.mark_step_done(job_id, step_index),
            on_total_batches=lambda total: ingestion_jobs.set_total_batches(job_id, total),
            on_batch_done=lambda: ingestion_jobs.mark_batch_done(job_id),
            on_total_chunks=lambda total: ingestion_jobs.set_total_chunks(job_id, total),
            on_chunk_done=lambda: ingestion_jobs.mark_chunk_done(job_id),
        )
        ingestion_jobs.mark_done(job_id)
    except Exception as exc:
        ingestion_jobs.mark_error(job_id, str(exc))


@router.post("/", response_model=FileIngestionStartResponse)
def start_ingestion(request: FileIngestionRequest, background_tasks: BackgroundTasks):
    parsed = urlparse(request.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Not a valid link")

    job_id = ingestion_jobs.create_job()
    background_tasks.add_task(_run_ingestion, job_id, request.url)

    return {"job_id": job_id}


@router.get("/status/{job_id}", response_model=FileIngestionStatusResponse)
def get_ingestion_status(job_id: str):
    job = ingestion_jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
