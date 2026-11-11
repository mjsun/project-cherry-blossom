import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE } from "../apiBase";

function renderWithHighlight(text, highlight) {
  if (!highlight) return text;

  const start = text.indexOf(highlight);
  if (start === -1) return text;

  const end = start + highlight.length;
  return (
    <>
      {text.slice(0, start)}
      <mark className="qa-highlight">{text.slice(start, end)}</mark>
      {text.slice(end)}
    </>
  );
}

function CmbsQa() {
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("");
  const [route, setRoute] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/home/`)
      .then((res) => res.json())
      .then((data) => setMessage(data));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setResult("");
    setRoute("");
    setSources([]);
    setLoading(true);

    fetch(`${API_BASE}/api/query/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
      .then((res) => res.json())
      .then((data) => {
        setResult(data.answer);
        setRoute(data.route);
        setSources(data.sources || []);
      })
      .finally(() => setLoading(false));
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
        <span className="qa-title">CMBS-QA</span>
      </header>

      <main className="nx-page-content">
        <p className="qa-subtitle">{message}</p>

        <form className="qa-form" onSubmit={handleSubmit}>
          <input
            className="qa-input"
            type="text"
            placeholder="Ask a question about CMBS filings..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            className="nx-btn nx-btn-dark"
            type="submit"
            disabled={!query.trim() || loading}
          >
            Ask
          </button>
        </form>

        {loading && (
          <div className="qa-loading" role="status" aria-label="Loading answer">
            <span className="qa-spinner" />
            <span>Thinking...</span>
          </div>
        )}

        {!loading && result && (
          <div className="qa-result">
            <p>{result}</p>

            {route === "structured" && (
              <p className="qa-source">Data from database</p>
            )}

            {route !== "structured" && sources.length > 0 && (
              <div className="qa-source">
                <span>Referenced chunk{sources.length > 1 ? "s" : ""}:</span>
                <div className="qa-source-list">
                  {sources.map((s, i) => (
                    <details className="qa-chunk" key={i}>
                      <summary>Chunk {s.chunk_index}</summary>
                      <p className="qa-chunk-text">
                        {renderWithHighlight(s.text, s.highlight)}
                      </p>
                      <footer className="qa-chunk-footnote">{s.deal_id}</footer>
                    </details>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default CmbsQa;
