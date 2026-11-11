import { Link } from "react-router-dom";

const CAPABILITIES = [
  {
    tag: "Retrieval",
    title: "Loan-level search",
    desc: "Ask about a single loan, tranche, or risk factor across a 400-page prospectus and get the exact passage back.",
    tone: "tone-amber",
  },
  {
    tag: "Grounding",
    title: "Cited, not guessed",
    desc: "Every answer links back to the chunk it came from, so you can verify the source in one click.",
    tone: "tone-yellow",
  },
  {
    tag: "Structured data",
    title: "SQL + vector, together",
    desc: "Numeric fields route to SQL, narrative questions route to embeddings — automatically, per query.",
    tone: "tone-slate",
  },
  {
    tag: "Pipeline",
    title: "Clean ingestion",
    desc: "HTML filings are parsed, labeled, chunked, and embedded in one pass with live progress tracking.",
    tone: "tone-navy",
  },
  {
    tag: "Speed",
    title: "Answers in seconds",
    desc: "A purpose-built index keeps lookups fast even as the filing library grows into the thousands.",
    tone: "tone-charcoal",
  },
  {
    tag: "Coverage",
    title: "Built for CMBS",
    desc: "Tuned on commercial mortgage-backed securities language — servicer notes, DSCR, waterfalls, and more.",
    tone: "tone-ink",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Ingest a filing",
    desc: "Drop in a link to a prospectus. We clean, label, and extract it to SQL automatically.",
  },
  {
    n: "02",
    title: "Chunk & embed",
    desc: "Text is split into retrievable chunks and embedded for fast, precise semantic search.",
  },
  {
    n: "03",
    title: "Ask anything",
    desc: "Query in plain English — loan terms, risk factors, deal structure — and get a grounded answer.",
  },
];

const STATS = [
  { value: "10K+", label: "Pages indexed" },
  { value: "<2s", label: "Avg. response time" },
  { value: "100%", label: "Answers with citations" },
  { value: "0", label: "Hallucinated figures" },
];

function Home() {
  return (
    <div className="home-page">
      <nav className="nx-nav">
        <span className="nx-logo">GreenLight</span>
        <div className="nx-nav-links">
          <Link to="/ingest-file">Ingest</Link>
          <Link to="/cmbs-qa">Q&amp;A</Link>
        </div>
        <Link to="/cmbs-qa" className="nx-btn nx-btn-dark">Launch CMBS-QA</Link>
      </nav>

      <header className="nx-hero">
        <div className="nx-hero-text">
          <h1>GreenLight</h1>
          <p>
            Why we're different &nbsp;·&nbsp; A grounded AI analyst &nbsp;·&nbsp; Powered by GPT-4
          </p>
        </div>
        <p className="nx-hero-sub">
          <strong>CMBS filings, answered instantly.</strong> Ask a question, get a
          grounded answer pulled straight from the document — no guessing, no
          hallucinated figures.
        </p>
      </header>

      <section className="nx-badges">
        <span>SQL + Vector Search</span>
        <span>GPT-4 grounded</span>
        <span>Sub-second retrieval</span>
        <span>Loan-level detail</span>
        <span>Source-cited answers</span>
        <span>Built for CMBS</span>
      </section>

      <section className="nx-capabilities">
        <div className="nx-section-head">
          <span className="nx-eyebrow">What we offer</span>
          <h2>Built to answer the hard questions</h2>
        </div>
        <div className="nx-capability-grid">
          {CAPABILITIES.map((c) => (
            <div className="nx-capability-card" key={c.title}>
              <div className={`nx-capability-art ${c.tone}`}>
                <span>{c.tag}</span>
              </div>
              <h3>{c.title}</h3>
              <p>{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="nx-results">
        <div className="nx-results-copy">
          <span className="nx-eyebrow">Why GreenLight</span>
          <h2>We get you answers — <strong>grounded, fast, and verifiable.</strong></h2>
          <p>
            Every response is retrieved directly from filing text. Clean
            interfaces, fast ingestion, and transparent sourcing keep analysts
            coming back.
          </p>
          <div className="nx-results-actions">
            <Link to="/ingest-file" className="nx-btn nx-btn-dark">Ingest a file</Link>
            <Link to="/cmbs-qa" className="nx-btn nx-btn-outline">See it in action</Link>
          </div>
        </div>
        <div className="nx-stats-grid">
          {STATS.map((s) => (
            <div className="nx-stat" key={s.label}>
              <span className="nx-stat-value">{s.value}</span>
              <span className="nx-stat-label">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="nx-services">
        <div className="nx-section-head nx-section-head-dark">
          <span className="nx-eyebrow">How it works</span>
          <h2>From raw filing to grounded answer</h2>
        </div>
        <div className="nx-steps">
          {STEPS.map((s) => (
            <div className="nx-step" key={s.n}>
              <span className="nx-step-n">{s.n}</span>
              <div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <Link to="/ingest-file" className="nx-btn nx-btn-light">Get started</Link>
      </section>

      <footer className="nx-footer">
        <h2>Ready to ask your filings a question?</h2>
        <div className="nx-footer-actions">
          <Link to="/ingest-file" className="nx-btn nx-btn-light">Ingest File</Link>
          <Link to="/cmbs-qa" className="nx-btn nx-btn-outline-light">Launch CMBS-QA</Link>
        </div>
        <div className="nx-footer-base">
          <span>GreenLight</span>
          <span>CMBS-QA · 2026</span>
        </div>
      </footer>
    </div>
  );
}

export default Home;
