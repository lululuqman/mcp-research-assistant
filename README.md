# mcp-research-assistant
A Model Context Protocol (MCP) server powered by FastAPI that integrates DuckDuckGo and arXiv search tools. Built with Docker for easy deployment and designed to connect with GPT for real-time research assistance.

# 🧠 MCP Research Assistant

A Model Context Protocol (MCP) server that lets AI models fetch info from:
- 🦆 DuckDuckGo (general web search)
- 🧠 arXiv (academic research papers)

---

## 🚀 Run Locally (Docker)

```bash
docker build -t mcp-research-assistant .
docker run -p 8000:8000 mcp-research-assistant