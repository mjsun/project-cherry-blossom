import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

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
  const pollRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  const pollStatus = (id) => {
    pollRef.current = setInterval(() => {
      fetch(`http://localhost:8000/api/file_ingestion/status/${id}`)
        .then((res) => res.json())
        .then((data) => {
          setCompletedSteps(data.completed_steps || []);
          setStatus(data.status);
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
    setStatus("running");

    fetch("http://localhost:8000/api/file_ingestion/", {
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
