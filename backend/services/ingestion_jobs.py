import threading
import uuid

STEPS = [
    "Reading HTML and cleaning lines",
    "Labeling and extracting to SQL",
    "Chunking and embedding",
]

_jobs = {}
_lock = threading.Lock()


def create_job():
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "completed_steps": [],
            "error": None,
            "total_batches": 0,
            "completed_batches": 0,
            "total_chunks": 0,
            "completed_chunks": 0,
        }
    return job_id


def mark_step_done(job_id, step_index):
    with _lock:
        _jobs[job_id]["completed_steps"].append(step_index)


def set_total_batches(job_id, total):
    with _lock:
        _jobs[job_id]["total_batches"] = total
        _jobs[job_id]["completed_batches"] = 0


def mark_batch_done(job_id):
    with _lock:
        _jobs[job_id]["completed_batches"] += 1


def set_total_chunks(job_id, total):
    with _lock:
        _jobs[job_id]["total_chunks"] = total
        _jobs[job_id]["completed_chunks"] = 0


def mark_chunk_done(job_id):
    with _lock:
        _jobs[job_id]["completed_chunks"] += 1


def mark_done(job_id):
    with _lock:
        _jobs[job_id]["status"] = "done"


def mark_error(job_id, message):
    with _lock:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = message


def get_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None
