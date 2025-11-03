from bs4 import BeautifulSoup
import requests
import os
import json
import re
import sys

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

## No social integrations: keep code minimal

# Style: keep it simple - narrative, ironic, clear
STYLE_INSTRUCTIONS = (
	"Rewrite in English with an ironic, direct tone. "
	"Keep all information but completely rephrase it so it's unrecognizable from the original. "
	"Be clear and fluent. No code fences or HTML tags."
)

# Store articles here
articles = []
def extract_json(text):
	"""Extract JSON from model output (handles code fences and <think> blocks)"""
	if not text:
		return None
	
	# Clean up the text
	t = text.strip()
	
	# Remove code fences
	if t.startswith("```"):
		lines = t.splitlines()
		t = "\n".join(lines[1:])
		if t.endswith("```"):
			t = t[:-3]
		t = t.strip()
	
	# Remove DeepSeek thinking blocks
	t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL)
	
	# Try parsing directly
	try:
		return json.loads(t)
	except:
		pass
	
	# Find JSON in text
	start = t.find('{')
	end = t.rfind('}')
	if start != -1 and end != -1 and end > start:
		try:
			return json.loads(t[start:end+1])
		except:
			pass
	
	return None


def rewrite_with_ollama(title, body):
	"""Send article to Ollama and get rewritten version"""
	prompt = f"""Titolo: {title}
Testo: {body}

{STYLE_INSTRUCTIONS}

Restituisci SOLO JSON con chiavi 'title' e 'body'."""

	try:
		response = requests.post(
			f"{OLLAMA_URL}/api/generate",
			json={
				"model": OLLAMA_MODEL,
				"prompt": prompt,
				"stream": False,
				"format": "json",
				"options": {
					"num_predict": 2048,
					"temperature": 0.7,
					"num_ctx": 8192,
				}
			},
			timeout=300,
		)
		
		# If generate endpoint doesn't exist, try chat
		if response.status_code == 404:
			response = requests.post(
				f"{OLLAMA_URL}/api/chat",
				json={
					"model": OLLAMA_MODEL,
					"messages": [
						{"role": "system", "content": "Riscrivi notizie. Rispondi SOLO in JSON."},
						{"role": "user", "content": prompt}
					],
					"stream": False,
					"format": "json",
					"options": {"num_predict": 2048, "temperature": 0.7, "num_ctx": 8192}
				},
				timeout=300,
			)
			response.raise_for_status()
			content = response.json().get("message", {}).get("content", "").strip()
		else:
			response.raise_for_status()
			content = response.json().get("response", "").strip()
		
		# Parse JSON from response
		parsed = extract_json(content)
		if parsed:
			return {"title": parsed.get("title", ""), "body": parsed.get("body", "")}
		
		# Fallback if not JSON
		return {"title": title, "body": content}
		
	except Exception as e:
		print(f"[error] Ollama failed: {e}", file=sys.stderr)
		return None


def rewrite_article(title, text):
	"""Rewrite article or return original if fails"""
	result = rewrite_with_ollama(title, text)
	return result if result else {"title": title, "body": text}


## Removed all Twitter helpers to keep the script focused on rewriting only


# === STEP 1: Get homepage ===
url = "https://www.gravinalife.it"
page = requests.get(url, timeout=20)
soup = BeautifulSoup(page.text, 'html.parser')

# === STEP 2: Find "Più letti" section ===
most_read = soup.find('div', class_='side-title', string='Più letti questa settimana')
if not most_read:
	print("Could not find 'Più letti' section")
	sys.exit(1)

# Get the article list
wrapper = most_read.find_parent('div', class_='side-wrapper')
article_list = wrapper.find('div', class_='side-list')
top_3 = article_list.find_all('div', class_='side side-text', limit=3)

# === STEP 3: Extract each article ===
for item in top_3:
	# Get title
	sharing = item.find('div', class_='sharing')
	title = sharing.get('data-title') if sharing and sharing.has_attr('data-title') else None
	
	if not title:
		title_link = item.find('span', class_='title')
		if title_link and title_link.find('a'):
			title = title_link.find('a').get_text(strip=True)
	
	# Get URL
	url_link = item.find('span', class_='title')
	article_url = None
	if url_link and url_link.find('a'):
		href = url_link.find('a').get('href')
		if href:
			article_url = "https://www.gravinalife.it" + href
	
	# Fetch full article text
	full_text = None
	if article_url:
		try:
			article_page = requests.get(article_url, timeout=20)
			article_soup = BeautifulSoup(article_page.text, 'html.parser')
			
			# Get all paragraph blocks
			paragraphs = article_soup.select('.p')
			if not paragraphs:
				paragraphs = article_soup.select('div.content-wrapper p, article p')
			
			text_parts = [p.get_text(" ", strip=True) for p in paragraphs if p.get_text(strip=True)]
			if text_parts:
				full_text = "\n\n".join(text_parts)
		except:
			pass
	
	# Save article
	articles.append({'title': title, 'text': full_text})

# === STEP 4: Rewrite and print ===
for idx, article in enumerate(articles, 1):
	title = article.get('title', '')
	text = article.get('text', '')
	
	# Separator between articles (for console output)
	if idx > 1:
		print("\n" + "="*80 + "\n")
	
	# Rewrite
	rewritten = rewrite_article(title, text)
	rewritten_title = rewritten.get('title', '').strip()
	rewritten_body = rewritten.get('body', '').strip()
	
	# Print to console
	print(rewritten_title)
	print()
	print(rewritten_body)
	
	# No external publishing: print only