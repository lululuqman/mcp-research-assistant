from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import feedparser
import os
from dotenv import load_dotenv

# ✅ Load .env variables
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# 🔍 Tavily Search Endpoint
# ================================
@app.get("/tools/search_web")
async def search_web(query: str):
    """
    Tavily Web Search (replaces DuckDuckGo)
    """
    try:
        if not TAVILY_API_KEY:
            return {"error": "TAVILY_API_KEY is missing in .env"}

        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 10,
                "include_answer": False,
                "include_domains": [],
                "search_depth": "basic",
                "include_images": False,
            },
            timeout=10,
        )

        if response.status_code != 200:
            return {"error": f"Tavily API error ({response.status_code})"}

        data = response.json()
        results = []

        for item in data.get("results", []):
            results.append({
                "title": item.get("title", "Untitled"),
                "summary": item.get("content", "No summary available."),
                "url": item.get("url", "#"),
                "source": item.get("url", "Tavily").split("/")[2],
            })

        return {"results": results}

    except Exception as e:
        return {"error": str(e)}


# ================================
# 📚 arXiv Research Search
# ================================
@app.get("/tools/search_arxiv")
async def search_arxiv(query: str):
    """
    arXiv Research Paper Search
    """
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=10"
        feed = feedparser.parse(url)

        results = []
        for entry in feed.entries:
            title = entry.title
            summary = entry.summary
            paper_url = entry.link
            published = getattr(entry, "published", "Unknown Date")
            authors = [a.name for a in getattr(entry, "authors", [])]

            citation = f"{', '.join(authors) if authors else 'Unknown Author'} ({published.split('T')[0]})."
            results.append({
                "title": title,
                "summary": summary,
                "url": paper_url,
                "citation": citation,
                "source": "arXiv",
                "date": published,
                "authors": authors,
            })

        return {"results": results}

    except Exception as e:
        return {"error": str(e)}