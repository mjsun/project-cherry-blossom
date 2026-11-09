import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function CmbsQa() {
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/home/")
      .then((res) => res.json())
      .then((data) => setMessage(data));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    fetch("http://localhost:8000/api/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
      .then((res) => res.json())
      .then((data) => setResult(data.answer));
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
          <button className="btn btn-primary" type="submit">Ask</button>
        </form>

        {result && <p className="qa-result">{result}</p>}
      </main>
    </div>
  );
}

export default CmbsQa;
