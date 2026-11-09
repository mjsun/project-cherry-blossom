import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function CmbsQa() {
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/home/")
      .then((res) => res.json())
      .then((data) => setMessage(data));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setResult("");
    setLoading(true);

    fetch("http://localhost:8000/api/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
      .then((res) => res.json())
      .then((data) => setResult(data.answer))
      .finally(() => setLoading(false));
  };

  return (
    <div className="qa-page">
      <header className="qa-header">
        <Link to="/" className="qa-brand">GreenLight</Link>
        <span className="qa-divider" />
        <span className="qa-title">CMBS-QA</span>
      </header>

      <main className="qa-main">
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
            className="btn btn-primary"
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

        {!loading && result && <p className="qa-result">{result}</p>}
      </main>
    </div>
  );
}

export default CmbsQa;
