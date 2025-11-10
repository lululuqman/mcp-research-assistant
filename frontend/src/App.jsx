import React, { useState } from "react";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("Tavily");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const suggestions = [
    "AI Ethics",
    "Quantum Computing",
    "Climate Change",
    "React Performance",
    "GPT Models",
    "Blockchain Security",
    "Robotics",
  ];

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setResults([]);

    try {
      const endpoint =
        source === "Tavily"
          ? `http://localhost:8000/tools/search_web?query=${encodeURIComponent(query)}`
          : `http://localhost:8000/tools/search_arxiv?query=${encodeURIComponent(query)}`;

      const response = await fetch(endpoint);
      if (!response.ok) throw new Error("Network error");

      const data = await response.json();
      if (!data || data.error) throw new Error(data.error || "Error fetching data");

      setResults(data.results || []);
    } catch (err) {
      console.error(err);
      setError("Error fetching data. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="app">
      {/* Header always visible */}
      <header className="header">
        <h1>MCP Research Assistant 🔍</h1>
        <p className="subtitle">Search academic papers or the web intelligently</p>
      </header>

      {/* Search Bar */}
      <div className="search-container">
        <input
          type="text"
          value={query}
          placeholder="Search for topics (AI, Quantum, GPT...)"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          list="suggestions"
        />
        <datalist id="suggestions">
          {suggestions.map((s, i) => (
            <option key={i} value={s} />
          ))}
        </datalist>

        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="Tavily">Tavily (Web)</option>
          <option value="arXiv">arXiv (Papers)</option>
        </select>

        <button onClick={handleSearch} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {/* Results */}
      <main className="results-section">
        {error && <p className="error">{error}</p>}

        {!loading && results.length === 0 && !error && (
          <p className="no-results">No results yet. Try searching something!</p>
        )}

        {results.map((item, index) => (
          <div className="result-card" key={index}>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="result-title"
            >
              {item.title}
            </a>

            {/* Show citation for arXiv results */}
            {item.citation ? (
              <p className="citation">📚 {item.citation}</p>
            ) : (
              <p className="source">
                🌐 Source: {item.source || "Unknown"}
              </p>
            )}

            {item.summary && <p className="summary">{item.summary}</p>}
          </div>
        ))}
      </main>
    </div>
  );
}

export default App;