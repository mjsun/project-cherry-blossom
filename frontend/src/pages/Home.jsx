import { Link } from "react-router-dom";

function Home() {
  return (
    <div className="home-page">
      <header className="home-header">
        <span className="qa-brand">GreenLight</span>
        <nav>
          <Link to="/cmbs-qa" className="btn btn-ghost">Launch CMBS-QA</Link>
        </nav>
      </header>

      <section className="hero">
        <h1 className="hero-title">
          CMBS filings,<br />answered instantly.
        </h1>
        <p className="hero-sub">
          GreenLight is an AI analyst for Commercial Mortgage-Backed Securities
          documents — ask a question, get a grounded answer pulled straight
          from the filing.
        </p>
        <div className="hero-actions">
          <Link to="/ingest-file" className="btn btn-primary">Ingest File</Link>
          <Link to="/cmbs-qa" className="btn btn-outline">See it in action</Link>
        </div>
      </section>

      <section className="features">
        <div className="feature-card">
          <h2>Grounded answers</h2>
          <p>Every response is retrieved directly from filing text — no guessing, no hallucinated figures.</p>
        </div>
        <div className="feature-card">
          <h2>Built for loan-level detail</h2>
          <p>Ask about specific loans, risk factors, or sections across thousands of pages.</p>
        </div>
        <div className="feature-card">
          <h2>Fast, structured retrieval</h2>
          <p>A purpose-built pipeline chunks, labels, and indexes filings for precise lookup.</p>
        </div>
      </section>

      <footer className="home-footer">
        <span>GreenLight</span>
        <span>CMBS-QA</span>
      </footer>
    </div>
  );
}

export default Home;
