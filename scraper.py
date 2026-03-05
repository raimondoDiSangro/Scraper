# Generic Web Scraper + Article Rewriter with Claude API
# - Loads configuration from config.json
# - Scrapes any website homepage
# - Finds a configurable section
# - Extracts articles with configurable CSS selectors
# - Sends title/body to Claude for rewriting
# - Prints rewritten title + body to console

from bs4 import BeautifulSoup
import requests
import os
import json
import re
import sys
from typing import Optional
from anthropic import Anthropic

# -----------------------------
# Load Configuration
# -----------------------------
def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[error] Config file '{config_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[error] Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)

CONFIG = load_config()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("[error] ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
    sys.exit(1)

# Extract settings from config
BASE_URL = CONFIG["website"]["base_url"]
MOST_READ_LABEL = CONFIG["website"]["most_read_section_label"]
SELECTORS = CONFIG["website"]["selectors"]
ARTICLES_LIMIT = CONFIG["website"]["articles_limit"]
STYLE_INSTRUCTIONS = CONFIG["rewriting"]["style_instructions"]
CLAUDE_MODEL = CONFIG["claude"]["model"]
CLAUDE_MAX_TOKENS = CONFIG["claude"]["max_tokens"]
CLAUDE_TEMPERATURE = CONFIG["claude"]["temperature"]

# Initialize Anthropic client
client = Anthropic()


# -----------------------------
# Helpers
# -----------------------------
def extract_json(text: str) -> Optional[dict]:
    """Extract a JSON object from text."""
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


def rewrite_with_claude(title: str, body: str) -> Optional[dict]:
    """Send article to Claude; return {'title','body'} on success, else None."""
    # Build the prompt with original article and rewriting instructions
    prompt = (
        f"Title: {title}\n"
        f"Body: {body}\n\n"
        f"{STYLE_INSTRUCTIONS}\n\n"
        "Return ONLY valid JSON with keys 'title' and 'body'. No markdown, no code fences, just JSON."
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from Claude's response
        content = message.content[0].text.strip()
        
        # Parse JSON from the response
        parsed = extract_json(content)
        if parsed:
            return {
                "title": parsed.get("title", "").strip(),
                "body": parsed.get("body", "").strip()
            }

        # If JSON parsing fails, return original title with raw content as body
        return {"title": title, "body": content.strip()}

    except Exception as e:
        print(f"[error] Claude request failed: {e}", file=sys.stderr)
        return None


def rewrite_article(title: str, text: str) -> dict:
    """Rewrite article with Claude; on failure, return original."""
    res = rewrite_with_claude(title or "", text or "")
    return res if res else {"title": title or "", "body": text or ""}


# -----------------------------
# Main Scrape + Rewrite
# -----
def main():
    # STEP 1: Fetch the homepage
    try:
        resp = requests.get(BASE_URL, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[error] Failed to fetch homepage: {e}", file=sys.stderr)
        sys.exit(1)

    # STEP 2: Parse HTML and find the "Most read" section
    soup = BeautifulSoup(resp.text, "html.parser")
    most_read_title = soup.find("div", class_="side-title", string=MOST_READ_LABEL)
    if not most_read_title:
        print(f"[error] Could not find '{MOST_READ_LABEL}' section", file=sys.stderr)
        sys.exit(1)

    # Navigate up to the wrapper div containing the article list
    wrapper = most_read_title.find_parent("div", class_=SELECTORS["section_class"])
    if not wrapper:
        print(f"[error] Could not find wrapper with class '{SELECTORS['section_class']}'", file=sys.stderr)
        sys.exit(1)

    # Find the list container with the articles
    article_list = wrapper.find("div", class_=SELECTORS["list_class"])
    if not article_list:
        print(f"[error] Could not find list with class '{SELECTORS['list_class']}'", file=sys.stderr)
        sys.exit(1)

    # Extract article items up to the configured limit
    items = article_list.find_all("div", class_=SELECTORS["article_item_class"], limit=ARTICLES_LIMIT)
    if not items:
        print(f"[error] No articles found with class '{SELECTORS['article_item_class']}'", file=sys.stderr)
        sys.exit(1)

    # STEP 3: Extract title, URL, and full body text for each article
    articles = []
    for it in items:
        # Extract the article title
        title = ""
        # First try to get title from the sharing div's data-title attribute
        sharing = it.find("div", class_=SELECTORS["sharing_div_class"])
        if sharing and sharing.has_attr("data-title"):
            title = (sharing.get("data-title") or "").strip()
        # If not found, fallback to the link text
        if not title:
            tspan = it.find("span", class_=SELECTORS["article_title_class"])
            if tspan and tspan.find("a"):
                title = tspan.find("a").get_text(strip=True)

        # Extract the article URL
        article_url = ""
        tspan = it.find("span", class_=SELECTORS["article_title_class"])
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
                
                # Try each configured paragraph selector in order
                paras = []
                for selector in SELECTORS["article_paragraphs"]:
                    paras = asoup.select(selector)
                    if paras:
                        break
                
                # Extract text from all paragraphs and join with double newlines
                parts = [p.get_text(" ", strip=True) for p in paras if p.get_text(strip=True)]
                full_text = "\n\n".join(parts) if parts else ""
            except Exception:
                full_text = ""

        articles.append({"title": title, "text": full_text})

    # STEP 4: Rewrite each article with Claude and print the results
    for idx, art in enumerate(articles, 1):
        # Print separator between articles (not before the first one)
        if idx > 1:
            print("\n" + "=" * 80 + "\n")
        
        # Send article to Claude for rewriting
        rewritten = rewrite_article(art.get("title", ""), art.get("text", ""))
        
        # Print the rewritten title and body
        print(rewritten.get("title", "").strip())
        print()
        print(rewritten.get("body", "").strip())


if __name__ == "__main__":
    main()
