# Generic Web Scraper + Claude Rewriter

A configurable web scraper that automatically rewrites articles using Claude's API.

## Setup

### 1. Set your Anthropic API key

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "your-api-key-here"

# CMD
set ANTHROPIC_API_KEY=your-api-key-here

# Linux/Mac
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. Install dependencies

```bash
pip install anthropic beautifulsoup4 requests
```

## Configuration

Edit `config.json` to customize for any website:

```json
{
  "website": {
    "base_url": "https://www.example.com",
    "most_read_section_label": "Section Title",
    "selectors": {
      "section_class": "class-name",      // Wrapper div class
      "list_class": "class-name",         // List container class
      "article_item_class": "class-name", // Individual article class
      "article_title_class": "class-name", // Title span class
      "sharing_div_class": "class-name",  // Sharing div class (optional)
      "article_paragraphs": [".p", "p"]   // CSS selectors to try in order
    },
    "articles_limit": 3                     // Number of articles to process
  },
  "rewriting": {
    "style_instructions": "Your custom rewriting instructions here..."
  },
  "claude": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2048,
    "temperature": 0.7
  }
}
```

## Usage

```bash
python scraper.py
```

The script will:
1. Fetch the homepage
2. Find the configured section
3. Extract the top N articles
4. Rewrite each with Claude
5. Print rewritten articles to console

## How to find CSS selectors

1. Open the website in your browser
2. Right-click → "Inspect" to open developer tools
3. Use the element inspector to find class names for:
   - The wrapper div holding the "most read" list
   - The list container
   - Individual article items
   - Title elements
   - Body paragraphs

## Example: Setting up for a new website

1. Open `config.json`
2. Change `base_url` to your target website
3. Update `most_read_section_label` to match the section header
4. Inspect the HTML and update all the selector class names
5. Run `python scraper.py` and test
