#!/usr/bin/env python3
"""
News scraper with AI rewriting via Ollama.

Supports multiple sites via SiteConfig. Uses trafilatura for article body
extraction (works on most news sites without custom selectors).

Usage:
    python scraper.py [--site gravinalife] [--count 3]

Environment variables:
    OLLAMA_URL    Ollama server URL  (default: http://localhost:11434)
    OLLAMA_MODEL  Model name         (default: deepseek-r1:8b)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Optional
from urllib.parse import urljoin

import requests
import trafilatura
from bs4 import BeautifulSoup


# ── Configuration ─────────────────────────────────────────────────────────────

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

STYLE_INSTRUCTIONS = (
    "Rewrite in English with an ironic, confident tone. "
    "Keep all facts, but make it sound natural and human. "
    "Be clear, direct, short, and a bit sarcastic. "
    "If possible, mention how locals reacted or what they said. "
    "Vary sentence rhythm so it flows better and keeps readers hooked."
)

MAX_RETRIES    = 3
RETRY_DELAY    = 2    # seconds between retries
FETCH_TIMEOUT  = 20   # seconds
OLLAMA_TIMEOUT = 300  # seconds

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; news-scraper/2.0)"}


# ── Site Configs ───────────────────────────────────────────────────────────────

@dataclass
class SiteConfig:
    name: str
    base_url: str
    # CSS selector that returns <a> elements linking to articles.
    # Applied within the section found by section_label, if set.
    link_selector: str
    # If the target articles live on a separate page (e.g. /most-read),
    # set this; otherwise the base_url homepage is fetched.
    feed_url: str = ""
    # Narrow the search to a labelled section on the page.
    # section_selector: CSS selector for the heading/label element.
    # section_label:    text that element must contain.
    section_selector: str = ""
    section_label: str = ""
    max_articles: int = 3


SITES: dict[str, SiteConfig] = {
    "gravinalife": SiteConfig(
        name="gravinalife",
        base_url="https://www.gravinalife.it",
        link_selector="span.title a",
        section_selector="div.side-title",
        section_label="Più letti questa settimana",
        max_articles=3,
    ),
    # ── Add more sites here ────────────────────────────────────────────────
    #
    # "example": SiteConfig(
    #     name="example",
    #     base_url="https://example-news.com",
    #     feed_url="https://example-news.com/most-read",   # optional
    #     link_selector="h2.article-title a",
    #     max_articles=5,
    # ),
}


# ── Network helpers ────────────────────────────────────────────────────────────

def fetch_with_retry(url: str, timeout: int = FETCH_TIMEOUT) -> Optional[requests.Response]:
    """GET a URL, retrying up to MAX_RETRIES times on transient failures."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=HEADERS)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"[error] Failed to fetch {url} after {MAX_RETRIES} attempts: {e}",
                      file=sys.stderr)
                return None
            time.sleep(RETRY_DELAY)
    return None


# ── JSON extraction ────────────────────────────────────────────────────────────

def extract_json(text: str) -> Optional[dict]:
    """Extract a JSON object from model output.

    Handles:
    - Markdown code fences (```json ... ```)
    - DeepSeek <think>...</think> reasoning blocks
    - JSON embedded inside surrounding prose
    """
    if not text:
        return None
    t = text.strip()

    # Remove markdown code fences
    if t.startswith("```"):
        lines = t.splitlines()
        inner = lines[1:]  # drop opening ``` or ```json line
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]  # drop closing ``` line
        t = "\n".join(inner).strip()

    # Remove DeepSeek's <think>...</think> reasoning blocks
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()

    # Try the whole string first
    try:
        return json.loads(t)
    except Exception:
        pass

    # Fallback: extract the first {...} block
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except Exception:
            pass

    return None


# ── Scraping ───────────────────────────────────────────────────────────────────

def get_article_urls(config: SiteConfig) -> list[str]:
    """Fetch the site's listing page and return article URLs per the site config."""
    url = config.feed_url or config.base_url
    resp = fetch_with_retry(url)
    if resp is None:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Narrow to a labelled section when configured
    search_root = soup
    if config.section_label and config.section_selector:
        for el in soup.select(config.section_selector):
            if config.section_label in el.get_text():
                parent = el.find_parent()
                if parent:
                    search_root = parent
                break

    links: list[str] = []
    for a in search_root.select(config.link_selector)[: config.max_articles]:
        href = (a.get("href") or "").strip()
        if href:
            links.append(urljoin(config.base_url, href))

    return links


def fetch_article(url: str, config: SiteConfig) -> dict:
    """Fetch one article URL; return title + body text."""
    resp = fetch_with_retry(url)
    if resp is None:
        return {"title": "", "text": "", "url": url}

    html = resp.text

    # trafilatura handles body extraction on most news sites
    body = trafilatura.extract(html, include_comments=False, include_tables=False) or ""

    # Get title from trafilatura metadata
    meta = trafilatura.extract_metadata(html)
    title = (meta.title or "") if meta else ""

    # Fallback: if trafilatura found nothing, use basic BeautifulSoup extraction
    if not body:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        title = title or (h1.get_text(strip=True) if h1 else "")
        paras = soup.select(
            "article p, .article-content p, .content p, .entry-content p, p"
        )
        body = "\n\n".join(
            p.get_text(" ", strip=True) for p in paras if p.get_text(strip=True)
        )

    return {"title": title, "text": body, "url": url}


# ── Rewriting ──────────────────────────────────────────────────────────────────

def rewrite_with_ollama(title: str, body: str) -> Optional[dict]:
    """Send an article to Ollama; return {'title', 'body'} on success, else None."""
    prompt = (
        f"Title: {title}\n"
        f"Body: {body}\n\n"
        f"{STYLE_INSTRUCTIONS}\n\n"
        "Return ONLY JSON with keys 'title' and 'body'."
    )
    payload_base = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "options": {"num_predict": 2048, "temperature": 0.7, "num_ctx": 8192},
    }

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={**payload_base, "prompt": prompt},
            timeout=OLLAMA_TIMEOUT,
        )

        if r.status_code == 404:
            # Older Ollama builds only expose /api/chat
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    **payload_base,
                    "messages": [
                        {"role": "system", "content": "Rewrite news. Reply ONLY in JSON."},
                        {"role": "user",   "content": prompt},
                    ],
                },
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            # Chat endpoint returns content in message.content
            content = r.json().get("message", {}).get("content", "").strip()
        else:
            r.raise_for_status()
            content = r.json().get("response", "").strip()

        parsed = extract_json(content)
        if parsed:
            return {
                "title": parsed.get("title", "").strip(),
                "body":  parsed.get("body",  "").strip(),
            }

        # JSON parsing failed — return raw content as body
        return {"title": title, "body": content.strip()}

    except Exception as e:
        print(f"[error] Ollama request failed: {e}", file=sys.stderr)
        return None


def rewrite_article(article: dict) -> dict:
    """Rewrite an article dict; fall back to original text on failure."""
    result = rewrite_with_ollama(article.get("title", ""), article.get("text", ""))
    if result:
        return result
    return {"title": article.get("title", ""), "body": article.get("text", "")}


# ── Output ─────────────────────────────────────────────────────────────────────

def print_results(results: list[dict]) -> None:
    for idx, res in enumerate(results, 1):
        if idx > 1:
            print("\n" + "=" * 80 + "\n")
        print(res.get("title", "").strip())
        print()
        print(res.get("body", "").strip())


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape and rewrite news articles with Ollama.",
    )
    parser.add_argument(
        "--site",
        choices=list(SITES.keys()),
        default=list(SITES.keys())[0],
        help=f"Site to scrape. Available: {', '.join(SITES.keys())} (default: %(default)s)",
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Number of articles to fetch (overrides the site config default).",
    )
    args = parser.parse_args()

    config = SITES[args.site]
    max_articles = args.count if args.count else config.max_articles

    # Step 1 — collect article URLs
    print(f"[info] Fetching article list from {config.feed_url or config.base_url} ...",
          file=sys.stderr)
    urls = get_article_urls(config)
    if not urls:
        print("[error] No article URLs found.", file=sys.stderr)
        sys.exit(1)
    urls = urls[:max_articles]
    print(f"[info] Found {len(urls)} article(s).", file=sys.stderr)

    # Step 2 — fetch all articles in parallel
    _fetch = partial(fetch_article, config=config)
    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        articles = list(pool.map(_fetch, urls))

    # Step 3 — rewrite sequentially (Ollama is typically single-GPU)
    results = []
    for art in articles:
        print(f"[info] Rewriting: {art.get('title') or art.get('url', '')}",
              file=sys.stderr)
        results.append(rewrite_article(art))

    # Step 4 — print
    print_results(results)


if __name__ == "__main__":
    main()
