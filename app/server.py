from fastapi import FastAPI
from openai_mcp import MCPServer
import requests
from bs4 import BeautifulSoup

app = FastAPI()
mcp = MCPServer(app, name="research_mcp")

# 🦆 DuckDuckGo Search Tool
@mcp.tool()
def search_web(query: str):
    """Search the web using DuckDuckGo and return top 5 results."""
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1"
    res = requests.get(url)
    if res.status_code != 200:
        return {"error": f"DuckDuckGo request failed ({res.status_code})"}
    data = res.json()
    related = data.get("RelatedTopics", [])
    results = []
    for r in related:
        if "Text" in r and "FirstURL" in r:
            results.append({
                "title": r["Text"],
                "link": r["FirstURL"]
            })
    return results[:5] or {"message": "No results found."}


# 🧠 arXiv Research Tool
@mcp.tool()
def search_arxiv(query: str):
    """Search arXiv for research papers."""
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
    res = requests.get(url)
    if res.status_code != 200:
        return {"error": f"arXiv request failed ({res.status_code})"}

    soup = BeautifulSoup(res.text, "xml")
    entries = soup.find_all("entry")

    results = []
    for e in entries:
        results.append({
            "title": e.title.text.strip(),
            "summary": e.summary.text.strip()[:300] + "...",
            "link": e.id.text.strip(),
            "published": e.published.text.strip()
        })
    return results or {"message": "No papers found."}


@app.get("/")
def root():
    return {"message": "MCP Research Assistant (DuckDuckGo + arXiv) is running!"}