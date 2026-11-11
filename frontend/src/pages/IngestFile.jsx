import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE } from "../apiBase";

const STEP_LABELS = [
  "Reading HTML and cleaning lines",
  "Labeling and extracting to SQL",
  "Chunking and embedding",
];

function IngestFile() {
  const [url, setLink] = useState("");
  const [filename, setFilename] = useState("");
  const [jobId, setJobId] = useState(null);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [status, setStatus] = useState(null); // null | "running" | "done" | "error"
  const [error, setError] = useState("");
  const [batchProgress, setBatchProgress] = useState({ total: 0, done: 0 });
  const [chunkProgress, setChunkProgress] = useState({ total: 0, done: 0 });
  const pollRef = useRef(null);

  const SECONDS_PER_BATCH = 2;
  const SECONDS_PER_CHUNK = 3;

  const formatEta = (seconds) => {
    if (seconds <= 0) return null;
    if (seconds < 60) return `~${seconds}s remaining`;
    const minutes = Math.ceil(seconds / 60);
    return `~${minutes} min remaining`;
  };

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  const pollStatus = (id) => {
    pollRef.current = setInterval(() => {
      fetch(`${API_BASE}/api/file_ingestion/status/${id}`)
        .then((res) => res.json())
        .then((data) => {
          setCompletedSteps(data.completed_steps || []);
          setStatus(data.status);
          setBatchProgress({
            total: data.total_batches || 0,
            done: data.completed_batches || 0,
          });
          setChunkProgress({
            total: data.total_chunks || 0,
            done: data.completed_chunks || 0,
          });
          if (data.status === "done" || data.status === "error") {
            clearInterval(pollRef.current);
            if (data.status === "error") setError(data.error || "Ingestion failed.");
          }
        })
        .catch(() => {
          clearInterval(pollRef.current);
          setStatus("error");
          setError("Lost connection while checking ingestion status.");
        });
    }, 1000);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    setCompletedSteps([]);
    setBatchProgress({ total: 0, done: 0 });
    setChunkProgress({ total: 0, done: 0 });
    setStatus("running");

    fetch(`${API_BASE}/api/file_ingestion/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, filename }),
    })
      .then((res) => res.json())
      .then((data) => {
        setJobId(data.job_id);
        pollStatus(data.job_id);
      })
      .catch(() => {
        setStatus("error");
        setError("Failed to start ingestion.");
      });
  };

  const reset = () => {
    clearInterval(pollRef.current);
    setLink("");
    setFilename("");
    setJobId(null);
    setCompletedSteps([]);
    setBatchProgress({ total: 0, done: 0 });
    setChunkProgress({ total: 0, done: 0 });
    setStatus(null);
    setError("");
  };

  return (
    <div className="nx-page">
      <nav className="nx-nav">
        <Link to="/" className="nx-logo">GreenLight</Link>
        <div className="nx-nav-links">
          <Link to="/ingest-file">Ingest</Link>
          <Link to="/cmbs-qa">Q&amp;A</Link>
        </div>
        <Link to="/" className="nx-btn nx-btn-outline">Back home</Link>
      </nav>

      <header className="qa-header">
        <span className="qa-title">Ingest File</span>
      </header>

      <main className="nx-page-content">
        {status === null && (
          <>
            <p className="qa-subtitle">Paste a link to a prospectus document to ingest it.</p>

            <form className="qa-form" onSubmit={handleSubmit}>
              <input
                className="qa-input"
                type="text"
                placeholder="File name"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                required
              />
              <input
                className="qa-input"
                type="text"
                placeholder="https://example.com/prospectus.pdf"
                value={url}
                onChange={(e) => setLink(e.target.value)}
                required
              />
              <button className="nx-btn nx-btn-dark" type="submit">Submit</button>
            </form>
          </>
        )}

        {(status === "running" || status === "error") && (
          <div className="ingest-steps">
            {STEP_LABELS.map((label, i) => {
              const isDone = completedSteps.includes(i);
              const isActive = !isDone && status === "running" &&
                (i === 0 || completedSteps.includes(i - 1));

              let eta = null;
              let progressLabel = null;
              if (isActive && i === 1 && batchProgress.total > 0) {
                const remaining = batchProgress.total - batchProgress.done;
                const current = Math.min(batchProgress.done + 1, batchProgress.total);
                eta = formatEta(remaining * SECONDS_PER_BATCH);
                progressLabel = `Batch ${current} / ${batchProgress.total} · ${remaining} remaining`;
              } else if (isActive && i === 2 && chunkProgress.total > 0) {
                const remaining = chunkProgress.total - chunkProgress.done;
                const current = Math.min(chunkProgress.done + 1, chunkProgress.total);
                eta = formatEta(remaining * SECONDS_PER_CHUNK);
                progressLabel = `Chunk ${current} / ${chunkProgress.total} · ${remaining} remaining`;
              }

              return (
                <div className="ingest-step" key={i}>
                  <div className="ingest-step-icon">
                    {isDone ? (
                      <span className="ingest-check">✓</span>
                    ) : (
                      <span className="ingest-step-number">{i + 1}</span>
                    )}
                  </div>
                  <div className="ingest-step-body">
                    <span className="ingest-step-label">{label}</span>
                    {!isDone && (
                      <div className="ingest-progress-track">
                        <div
                          className={`ingest-progress-bar ${isActive ? "ingest-progress-bar--active" : ""}`}
                        />
                      </div>
                    )}
                    {progressLabel && <span className="ingest-step-eta">{progressLabel}</span>}
                    {eta && <span className="ingest-step-eta">{eta}</span>}
                  </div>
                </div>
              );
            })}

            {status === "error" && (
              <p className="qa-result">{error}</p>
            )}
          </div>
        )}

        {status === "done" && (
          <div className="ingest-done">
            <p className="qa-subtitle">Ingestion complete.</p>
            <div className="ingest-done-actions">
              <Link to="/cmbs-qa" className="nx-btn nx-btn-dark">Go to Q&A</Link>
              <button className="nx-btn nx-btn-outline" onClick={reset}>Ingest another file</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default IngestFile;
