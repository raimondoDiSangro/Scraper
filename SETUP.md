# Generic Web Scraper + Claude Rewriter

A configurable web scraper that automatically rewrites articles using Claude's API. Works with any website.

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

Get your key from: https://console.anthropic.com/account/keys

### 2. Install dependencies

```bash
pip install anthropic beautifulsoup4 requests
```

## Configuration

Edit `config.json` to set up for your target website. Here's what each field means:

```json
{
  "website": {
    "base_url": "https://example.com",          // Homepage URL
    "most_read_section_label": "Most Popular",  // Section header text to find
    "selectors": {
      "section_class": "class-name",      // CSS class of wrapper div
      "list_class": "class-name",         // CSS class of article list
      "article_item_class": "class-name", // CSS class of each article item
      "article_title_class": "class-name", // CSS class of title element
      "sharing_div_class": "class-name",  // CSS class of sharing div (optional)
      "article_paragraphs": ["p"]         // CSS selectors for body text (tries in order)
    },
    "articles_limit": 3                   // Number of articles to process
  },
  "rewriting": {
    "style_instructions": "Your rewriting instructions..."
  },
  "claude": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2048,
    "temperature": 0.7
  }
}
```

## How to find CSS selectors for your website

1. **Visit the website** you want to scrape in your browser
2. **Right-click** on the section/element → **"Inspect"**
3. **Find the class name** in the HTML (e.g., `class="article-item"`)
4. **Update `config.json`** with the class names you found

### Example: Finding selectors for CNN

1. Go to https://www.cnn.com
2. Right-click on the "Most Popular" section → Inspect
3. Look at the HTML structure:
   - Find the wrapper div class
   - Find the list container class
   - Find each article item class
   - Find the title/heading class inside each item

Then update config.json with those values.

## Running the scraper

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set API key
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Run scraper
python scraper.py
```

## Example configs

- `config.example.gravinalife.json` - GravinaLife (Italian news site)

Just copy one to `config.json` and adjust selectors if needed.
