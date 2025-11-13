from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import feedparser
from urllib.parse import quote
import os
from dotenv import load_dotenv
import httpx
import asyncio
import time
import google.generativeai as genai
import urllib.parse
import traceback
from typing import Dict
import socket

# ✅ Load .env
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Missing GEMINI_API_KEY in .env file.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# ✅ Initialize app
app = FastAPI(title="MCP Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# 💾 Cache system
# ================================
cache = {}
CACHE_TTL = 300  # 5 minutes

def get_cache(key: str):
    data = cache.get(key)
    if data and (time.time() - data["timestamp"]) < CACHE_TTL:
        return data["results"]
    return None

def set_cache(key: str, results):
    cache[key] = {"timestamp": time.time(), "results": results}

# ================================
# 🌐 Tavily Web Search
# ================================
@app.get("/tools/search_web")
async def search_web(query: str):
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY missing in .env"}

    cache_key = f"tavily:{query}"
    cached = get_cache(cache_key)
    if cached:
        return {"results": cached, "cached": True}

    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": 8,
                    "include_answer": False,
                    "search_depth": "basic",
                    "include_images": False,
                },
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return {"error": f"Tavily error: {str(e)}"}

    results = [
        {
            "title": item.get("title", "Untitled"),
            "summary": item.get("content", "No summary available."),
            "url": item.get("url", "#"),
            "source": item.get("url", "Tavily").split("/")[2],
            "type": "web",
        }
        for item in data.get("results", [])
    ]

    set_cache(cache_key, results)
    return {"results": results, "cached": False}

# ================================
# 📚 arXiv Paper Search (fast, cached)
# ================================

@app.get("/tools/search_arxiv")
async def search_arxiv(query: str):
    """
    arXiv Research Paper Search with automatic fallback and timeout.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        base_urls = [
            f"https://export2.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=10",
            f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=10"
        ]

        headers = {"User-Agent": "FastAPI-ArxivFetcher/1.0"}

        async with httpx.AsyncClient(timeout=10) as client:
            response = None
            for url in base_urls:
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        break
                except (httpx.RequestError, httpx.TimeoutException):
                    continue

            if not response or response.status_code != 200:
                return {"error": f"arXiv error: {response.status_code if response else 'No response'}"}

            import feedparser
            feed = feedparser.parse(response.text)
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
        return {"error": f"arXiv error: {str(e)}"}

# ================================
# 💬 Gemini AI Chat
# ================================
@app.post("/tools/ask_ai")
async def ask_ai(payload: Dict):
    """
    Ask Gemini AI about a result. Robust extraction + friendly fallback.
    Payload should be: { "question": "...", "context": "..." }
    """
    question = payload.get("question", "").strip()
    context = payload.get("context", "").strip()

    if not question:
        return {"error": "Missing question."}
    if not context:
        return {"error": "Missing context."}

    # If key missing, return friendly error (and print server log)
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is missing. Set GEMINI_API_KEY in .env and restart.")
        return {"error": "AI assistant is not configured. Please add GEMINI_API_KEY."}

    # Compose a short prompt that provides context + question
    prompt = (
        "You are a concise research assistant. Use the context to answer the user's question. "
        "Be factual and short (1-3 paragraphs). If the context doesn't contain the answer, say so and give a next-step suggestion.\n\n"
        f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"
    )

    # We'll try a couple of times on transient errors
    max_attempts = 2
    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Use a thread to avoid blocking the event loop
            def call_gemini():
                model = genai.GenerativeModel("gemini-2.0-flash")
                # model.generate_content(prompt) is what worked for our earlier examples
                # some SDK responses may be objects with .text / .output / .candidates - we handle both
                return model.generate_content(prompt)

            response = await asyncio.to_thread(call_gemini)

            # Extract textual content robustly
            answer = None

            # Common place: response.text
            if hasattr(response, "text") and response.text:
                answer = response.text.strip()

            # Another possible shape (SDK may vary): response.output or response.candidates
            elif getattr(response, "output", None):
                # output may contain a list of 'content' blocks; join any text nodes
                try:
                    parts = []
                    for item in getattr(response, "output", []):
                        if isinstance(item, dict) and "content" in item:
                            # item["content"] might be list of dicts
                            content = item["content"]
                            if isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "output_text":
                                        parts.append(c.get("text", ""))
                        elif isinstance(item, str):
                            parts.append(item)
                    answer = "\n".join([p for p in parts if p]).strip() or None
                except Exception:
                    answer = None

            # Sometimes it's response.candidates[0].content
            elif getattr(response, "candidates", None):
                try:
                    cand = response.candidates[0]
                    # candidate may have 'content' or 'message' fields
                    answer = getattr(cand, "content", None) or getattr(cand, "message", None)
                    if isinstance(answer, dict):
                        # may be nested structure; try to get text field
                        answer = answer.get("text") or str(answer)
                    if isinstance(answer, list):
                        answer = " ".join([str(x) for x in answer])
                    if answer:
                        answer = str(answer).strip()
                except Exception:
                    answer = None

            # Final fallback: if response has .to_dict, try that and stringify
            if not answer:
                try:
                    d = getattr(response, "to_dict", None)
                    if callable(d):
                        s = d()
                        answer = str(s)[:2000]  # limit length
                except Exception:
                    answer = None

            if not answer:
                # If we couldn't extract, raise so that fallback path runs
                raise RuntimeError("Could not parse Gemini response format.")

            # Success
            return {"answer": answer}

        except (httpx.RequestError, socket.gaierror) as net_err:
            # transient network/DNS error - try again if possible
            last_exc = net_err
            print(f"⚠️ Gemini network error (attempt {attempt}): {repr(net_err)}")
            if attempt < max_attempts:
                await asyncio.sleep(1)
                continue
            else:
                print("❌ Gemini network failure:", traceback.format_exc())
                # Friendly message to user
                return {"error": "AI assistant temporarily unavailable (network). Please try again."}

        except Exception as e:
            # Log full traceback to server console for debugging
            print("❌ Gemini AI error (full traceback):")
            traceback.print_exc()
            last_exc = e
            # Friendly fallback for the frontend so UI doesn't display cryptic errors
            return {"error": "AI assistant is temporarily unavailable. Please try again later."}

    # Ultimately if we fell out of the loop without returning:
    return {"error": f"AI error: {str(last_exc)}"}