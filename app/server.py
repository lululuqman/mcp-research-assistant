from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from duckduckgo_search import DDGS
import arxiv
import requests

app = FastAPI(title="MCP Research Assistant")

# --- Allow React frontend requests ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, set to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root route ---
@app.get("/")
def read_root():
    return {"message": "MCP Research Assistant is running 🚀"}


# --- DuckDuckGo Search Tool ---
@app.get("/tools/search_web")
def search_web(query: str = Query(..., description="Search query")):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append({
                    "title": r.get("title"),
                    "link": r.get("href"),
                    "snippet": r.get("body")
                })
        return {"results": results}
    except Exception as e:
        return {"error": f"DuckDuckGo request failed: {str(e)}"}


# --- ArXiv Search Tool ---
@app.get("/tools/search_arxiv")
def search_arxiv(query: str = Query(..., description="ArXiv search query")):
    try:
        search = arxiv.Search(query=query, max_results=5, sort_by=arxiv.SortCriterion.Relevance)
        results = []
        for result in search.results():
            results.append({
                "title": result.title,
                "summary": result.summary,
                "authors": [a.name for a in result.authors],
                "pdf_url": result.pdf_url,
                "published": result.published.strftime("%Y-%m-%d")
            })
        return {"results": results}
    except Exception as e:
        return {"error": f"ArXiv request failed: {str(e)}"}


# --- Simple health check route ---
@app.get("/health")
def health():
    return {"status": "ok"}