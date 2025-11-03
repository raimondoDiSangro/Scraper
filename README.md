# Web Scraper with AI Rewriter & WordPress Publisher

This tool scrapes articles from gravinalife.it, rewrites them using a local AI model (Ollama), and optionally publishes them to your WordPress site.

## Setup

### 1. Install Dependencies
```powershell
pip install beautifulsoup4 requests
```

### 2. Install & Start Ollama
```powershell
# Download from: https://ollama.ai
ollama serve

# Pull the model
ollama pull deepseek-r1:8b
```

### 3. Configure WordPress (Optional)

To publish to WordPress, you need to create an **Application Password**:

1. Go to your WordPress site → Users → Profile
2. Scroll down to "Application Passwords"
3. Enter a name (e.g., "Scraper Bot") and click "Add New Application Password"
4. Copy the generated password (you won't see it again!)

### 4. Set Environment Variables

**For Publishing to WordPress:**
```powershell
# Required for WordPress publishing
$env:WP_SITE_URL = "https://yoursite.com"
$env:WP_USERNAME = "your_username"
$env:WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx xxxx xxxx"

# Optional: Auto-publish (default saves as draft)
$env:WP_PUBLISH = "true"
```

**Optional Ollama Configuration:**
```powershell
$env:OLLAMA_URL = "http://localhost:11434"
$env:OLLAMA_MODEL = "deepseek-r1:8b"
```

## Usage

### Test Without Publishing (Console Output Only)
```powershell
C:/Users/vince/Scraper/.venv/Scripts/python.exe scraper.py
```

### Publish to WordPress
```powershell
# Set WordPress credentials first
$env:WP_SITE_URL = "https://yoursite.com"
$env:WP_USERNAME = "your_username"
$env:WP_APP_PASSWORD = "your_app_password"

# Run scraper (saves as draft by default)
C:/Users/vince/Scraper/.venv/Scripts/python.exe scraper.py
```

### Auto-Publish (Skip Draft)
```powershell
$env:WP_PUBLISH = "true"
C:/Users/vince/Scraper/.venv/Scripts/python.exe scraper.py
```

## How It Works

1. **Scrapes** the top 3 most-read articles from gravinalife.it
2. **Rewrites** each article using DeepSeek AI (local Ollama)
3. **Outputs** to console (always)
4. **Publishes** to WordPress (if credentials are set)

## Troubleshooting

### Ollama Connection Error
```
[error] Ollama failed: 404
```
**Solution:** Make sure Ollama is running:
```powershell
ollama serve
```

### WordPress Authentication Error
```
[error] WordPress publish failed: 401
```
**Solution:** 
- Check your username and application password
- Make sure you're using an **Application Password**, not your regular WordPress password
- Verify your site URL is correct (include https://)

### WordPress REST API Disabled
```
[error] WordPress publish failed: 404
```
**Solution:** The WordPress REST API might be disabled. Check with your hosting provider or enable it in your WordPress settings.

## Configuration Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WP_SITE_URL` | For publishing | - | Your WordPress site URL |
| `WP_USERNAME` | For publishing | - | WordPress username |
| `WP_APP_PASSWORD` | For publishing | - | WordPress application password |
| `WP_PUBLISH` | No | `false` | Set to `true` to auto-publish |
| `OLLAMA_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `deepseek-r1:8b` | AI model to use |

## Notes

- Articles are saved as **drafts** by default. Set `WP_PUBLISH=true` to publish immediately.
- The script always prints articles to console, even when publishing to WordPress.
- Each article is published separately, so you'll get 3 new posts per run.
