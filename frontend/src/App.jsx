import { useEffect, useState } from "react";

function App() {
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
    fetch("http://localhost:8000/query/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
      .then((res) => res.json())
      .then((data) => setResult(data.answer));
  };

  return (
    <div>
      <h1>Hello World!</h1>
      <p>{message}</p>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit">Submit</button>
      </form>
      <p>{result}</p>
    </div>
  );
}

export default App;
