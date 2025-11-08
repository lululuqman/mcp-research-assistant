from fastapi import FastAPI, Query
from duckduckgo_search import DDGS
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# 🔑 Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="MCP Research Assistant")

# 🧭 DuckDuckGo Search Endpoint
@app.get("/tools/search_web")
def search_web(query: str = Query(...)):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body")
                })

        # 🧾 Save query to Supabase
        if results:
            supabase.table("search_history").insert({
                "query": query,
                "source": "duckduckgo",
                "result_summary": results[0]["title"] if results else "No result"
            }).execute()

        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

# 📚 Arxiv Search Endpoint
@app.get("/tools/search_arxiv")
def search_arxiv(query: str = Query(...)):
    try:
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
        response = requests.get(url)
        response.raise_for_status()
        supabase.table("search_history").insert({
            "query": query,
            "source": "arxiv",
            "result_summary": "Fetched results"
        }).execute()
        return {"results": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"message": "🚀 MCP Research Assistant with Supabase connected!"}
