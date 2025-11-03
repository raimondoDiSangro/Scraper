# Simple GravinaLife "Most Read" rewriter with Ollama
# - Scrapes the homepage
# - Finds the "Most read this week" section
# - Opens the top 3 articles
# - Sends title/body to a local Ollama model for rewriting
# - Prints rewritten title + body to console

from bs4 import BeautifulSoup
import requests
import os
import json
import re
import sys
from typing import Optional  # <-- added for Optional[dict]

# -----------------------------
# Configuration
# -----------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

STYLE_INSTRUCTIONS = (
    "Rewrite in English with an ironic, confident tone. "
    "Keep all facts, but make it sound natural and human. "
    "Be clear, direct, short, and a bit sarcastic. "
    "If possible, mention how locals reacted or what they said. "
    "Vary sentence rhythm so it flows better and keeps readers hooked."
)

BASE_URL = "https://www.gravinalife.it"
MOST_READ_LABEL = "Più letti questa settimana"


# -----------------------------
# Helpers
# -----------------------------
def extract_json(text: str):
    """Extract a JSON object from model output (handles code fences and <think> blocks)."""
    if not text:
        return None
    t = text.strip()

    # Remove markdown code fences if present (```json ... ```)
    if t.startswith("```"):
        lines = t.splitlines()
        t = "\n".join(lines[1:])  # Skip first line with ```
        if t.endswith("```"):
            t = t[:-3]  # Remove closing ```
        t = t.strip()

    # Remove DeepSeek's <think>...</think> reasoning blocks
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()

    # Try parsing the entire text as JSON
    try:
        return json.loads(t)
    except Exception:
        pass

    # If that fails, try extracting just the JSON object between { and }
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            return None
    return None


def rewrite_with_ollama(title: str, body: str) -> Optional[dict]:
    """Send article to Ollama; return {'title','body'} on success, else None."""
    # Build the prompt with original article and rewriting instructions
    prompt = (
        f"Title: {title}\n"
        f"Body: {body}\n\n"
        f"{STYLE_INSTRUCTIONS}\n\n"
        "Return ONLY JSON with keys 'title' and 'body'."
    )

    try:
        # Try the primary /api/generate endpoint first
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # Request JSON response format
                "options": {
                    "num_predict": 2048,    # Max tokens to generate (conservative for 8B model)
                    "temperature": 0.7,      # Creativity level
                    "num_ctx": 8192          # Context window for long articles
                },
            },
            timeout=300,
        )

        # If /api/generate returns 404, fallback to /api/chat endpoint
        if r.status_code == 404:
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": "Rewrite news. Reply ONLY in JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"num_predict": 2048, "temperature": 0.7, "num_ctx": 8192},
                },
                timeout=300,
            )
            r.raise_for_status()
            # Chat endpoint returns content in message.content
            content = r.json().get("message", {}).get("content", "").strip()
        else:
            r.raise_for_status()
            # Generate endpoint returns content in response
            content = r.json().get("response", "").strip()

        # Parse the JSON from the model's response
        parsed = extract_json(content)
        if parsed:
            return {"title": parsed.get("title", "").strip(), "body": parsed.get("body", "").strip()}

        # If JSON parsing fails, return original title with raw content as body
        return {"title": title, "body": content.strip()}

    except Exception as e:
        print(f"[error] Ollama request failed: {e}", file=sys.stderr)
        return None


def rewrite_article(title: str, text: str) -> dict:
    """Rewrite article; on failure, return original."""
    res = rewrite_with_ollama(title or "", text or "")
    return res if res else {"title": title or "", "body": text or ""}


# -----------------------------
# Main Scrape + Rewrite
# -----------------------------
def main():
    # STEP 1: Fetch the homepage
    try:
        resp = requests.get(BASE_URL, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[error] Failed to fetch homepage: {e}", file=sys.stderr)
        sys.exit(1)

    # STEP 2: Parse HTML and find the "Most read this week" section
    soup = BeautifulSoup(resp.text, "html.parser")
    most_read_title = soup.find("div", class_="side-title", string=MOST_READ_LABEL)
    if not most_read_title:
        print("Could not find 'Most read this week' section", file=sys.stderr)
        sys.exit(1)

    # Navigate up to the wrapper div containing the article list
    wrapper = most_read_title.find_parent("div", class_="side-wrapper")
    if not wrapper:
        print("Could not find side-wrapper for most read list", file=sys.stderr)
        sys.exit(1)

    # Find the list container with the articles
    article_list = wrapper.find("div", class_="side-list")
    if not article_list:
        print("Could not find side-list container", file=sys.stderr)
        sys.exit(1)

    # Extract the top 3 article items from the list
    items = article_list.find_all("div", class_="side side-text", limit=3)
    if not items:
        print("No articles found in most read list", file=sys.stderr)
        sys.exit(1)

    # STEP 3: Extract title, URL, and full body text for each article
    articles = []
    for it in items:
        # Extract the article title
        title = ""
        # First try to get title from the sharing div's data-title attribute
        sharing = it.find("div", class_="sharing")
        if sharing and sharing.has_attr("data-title"):
            title = (sharing.get("data-title") or "").strip()
        # If not found, fallback to the link text
        if not title:
            tspan = it.find("span", class_="title")
            if tspan and tspan.find("a"):
                title = tspan.find("a").get_text(strip=True)

        # Extract the article URL
        article_url = ""
        tspan = it.find("span", class_="title")
        if tspan and tspan.find("a"):
            href = (tspan.find("a").get("href") or "").strip()
            if href:
                article_url = BASE_URL + href

        # Fetch and extract the full article body
        full_text = ""
        if article_url:
            try:
                ap = requests.get(article_url, timeout=20)
                ap.raise_for_status()
                asoup = BeautifulSoup(ap.text, "html.parser")
                
                # Try to find paragraphs with class .p first (site-specific)
                paras = asoup.select(".p")
                # If not found, try common paragraph selectors
                if not paras:
                    paras = asoup.select("div.content-wrapper p, article p, .article-content p, .content p")
                
                # Extract text from all paragraphs and join with double newlines
                parts = [p.get_text(" ", strip=True) for p in paras if p.get_text(strip=True)]
                full_text = "\n\n".join(parts) if parts else ""
            except Exception:
                full_text = ""

        articles.append({"title": title, "text": full_text})

    # STEP 4: Rewrite each article with Ollama and print the results
    for idx, art in enumerate(articles, 1):
        # Print separator between articles (not before the first one)
        if idx > 1:
            print("\n" + "=" * 80 + "\n")
        
        # Send article to Ollama for rewriting
        rewritten = rewrite_article(art.get("title", ""), art.get("text", ""))
        
        # Print the rewritten title and body
        print(rewritten.get("title", "").strip())
        print()
        print(rewritten.get("body", "").strip())


if __name__ == "__main__":
    main()
