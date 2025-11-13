import React, { useState, useRef } from "react";
import "./App.css";

function ResultCard({ item, index, onAsk }) {
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]); // {role:'user'|'ai', text}
  const [aiLoading, setAiLoading] = useState(false);

  const summary = item.summary || item.abstract || "";
  const shortSummary = summary.length > 420 && !expanded ? summary.slice(0, 420) + "…" : summary;

  const ask = async (text) => {
    if (!text.trim()) return;
    setAiLoading(true);
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    try {
      const res = await fetch("http://localhost:8000/tools/ask_ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, context: summary || item.title }),
      });
      const data = await res.json();
      if (data.answer) {
        setMessages((m) => [...m, { role: "ai", text: data.answer }]);
      } else if (data.error) {
        setMessages((m) => [...m, { role: "ai", text: `⚠️ ${data.error}` }]);
      } else {
        setMessages((m) => [...m, { role: "ai", text: "No answer returned." }]);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "ai", text: "Network error. Try again." }]);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="result-card">
      <div className="result-header">
        <a href={item.url} target="_blank" rel="noopener noreferrer" className="result-title">
          {item.title}
        </a>
        <div className="result-meta">
          <span className="source">🌐 {item.source || item.citation || "Unknown"}</span>
          {item.date && <span className="date">{item.date.split("T")[0]}</span>}
        </div>
      </div>

      <div className="result-body">
        <p className="summary">{shortSummary}</p>
        {summary.length > 420 && (
          <button className="read-more" onClick={() => setExpanded((s) => !s)}>
            {expanded ? "Show less" : "Read more"}
          </button>
        )}

        {/* Chat area */}
        <div className="card-chat">
          <div className="chat-input-row">
            <input
              aria-label={`Ask about result ${index}`}
              placeholder="Ask AI about this result..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  ask(input);
                }
              }}
            />
            <button onClick={() => ask(input)} disabled={aiLoading}>
              {aiLoading ? "Thinking…" : "Ask"}
            </button>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role === "ai" ? "ai" : "user"}`}>
                <div className="bubble">
                  {m.role === "ai" ? "🤖 " : "You: "}
                  <span>{m.text}</span>
                </div>
              </div>
            ))}
            {aiLoading && (
              <div className="chat-message ai">
                <div className="bubble">🤖 Thinking…</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("Tavily");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");

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
    setLoadingMsg("Searching...");

    const longTimeout = setTimeout(() => {
      setLoadingMsg("Still searching… some sources (arXiv) can be slow. Please wait or try a different term.");
    }, 5000);

    try {
      const endpoint =
        source === "Tavily"
          ? `http://localhost:8000/tools/search_web?query=${encodeURIComponent(query)}`
          : `http://localhost:8000/tools/search_arxiv?query=${encodeURIComponent(query)}`;

      const res = await fetch(endpoint);
      clearTimeout(longTimeout);
      if (!res.ok) throw new Error("Network error");
      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }
      setResults(data.results || []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Error fetching data. Try again.");
    } finally {
      clearTimeout(longTimeout);
      setLoading(false);
      setLoadingMsg("");
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>MCP Research Assistant 🔎</h1>
        <p className="subtitle">Search academic papers or the web — then ask AI about any result</p>
      </header>

      <div className="search-container">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search (e.g. AI Ethics)"
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
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
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {loading && <div className="loading">{loadingMsg || "Searching…"}</div>}
      {error && <div className="error">{error}</div>}

      <main className="results">
        {results.length === 0 && !loading && !error && (
          <p className="no-results">No results yet. Try searching something!</p>
        )}

        {results.map((r, i) => (
          <ResultCard key={i} item={r} index={i} />
        ))}
      </main>
    </div>
  );
}