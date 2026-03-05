# Using Groq (FREE)

## Get Your Free API Key

1. Go to https://console.groq.com
2. Sign up (free, no payment required)
3. Create an API key in the "API keys" section
4. Copy the key

## Run the Scraper

```powershell
# Set your Groq API key
$env:GROQ_API_KEY = "gsk_YOUR_KEY_HERE"

# Run the scraper
python scraper.py
```

## Free Tier Limits

- **30 requests/minute** - plenty for article rewriting
- **100 requests/day** - free forever
- **Plus other free models**: Mixtral, Llama 2, and more

## Models Available (All Free)

- `mixtral-8x7b-32768` - **Default** (best quality/speed)
- `llama2-70b-4096` - Larger, slightly slower
- `gemma-7b-it` - Faster, smaller

To use a different model, edit `config.json`:

```json
{
  "llm": {
    "provider": "groq",
    "model": "llama2-70b-4096",
    "max_tokens": 2048,
    "temperature": 0.7
  }
}
```

## Switching to Claude (Paid)

If you want to use Claude instead:

```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

Then run with:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-KEY_HERE"
python scraper.py
```

---

That's it! Groq is completely free and works great for article rewriting.
