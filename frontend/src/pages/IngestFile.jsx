import { useState } from "react";
import { Link } from "react-router-dom";

function IngestFile() {
  const [link, setLink] = useState("");
  const [filename, setFilename] = useState("");
  const [result, setResult] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    fetch("http://localhost:8000/file/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link, filename }),
    })
      .then((res) => res.json())
      .then((data) => setResult(data.success ? data.content : "Failed to ingest prospectus."))
      .catch(() => setResult("Failed to ingest prospectus."));
  };

  return (
    <div className="qa-page">
      <header className="qa-header">
        <Link to="/" className="qa-brand">GreenLight</Link>
        <span className="qa-divider" />
        <span className="qa-title">Ingest File</span>
      </header>

      <main className="qa-main">
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
            value={link}
            onChange={(e) => setLink(e.target.value)}
            required
          />
          <button className="btn btn-primary" type="submit">Submit</button>
        </form>

        {result && <p className="qa-result">{result}</p>}
      </main>
    </div>
  );
}

export default IngestFile;
