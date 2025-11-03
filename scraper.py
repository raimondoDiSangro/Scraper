from bs4 import BeautifulSoup
import requests

# empty list to contain the scraped data
rows = []

# Open the website (homepage)
url = "https://www.gravinalife.it"
page = requests.get(url, timeout=20)
page.raise_for_status()
page_content = page.text

# Parse the HTML with BeautifulSoup
soup = BeautifulSoup(page_content, 'html.parser')

# Find the "Più letti questa settimana" section
most_read_section = soup.find('div', class_='side-title', string='Più letti questa settimana')

if not most_read_section:
	print("Could not find 'Più letti questa settimana' section")
else:
	# Get the parent wrapper and then find the side-list
	side_wrapper = most_read_section.find_parent('div', class_='side-wrapper')
	if not side_wrapper:
		print("Could not find wrapper for 'Più letti questa settimana'")
	else:
		side_list = side_wrapper.find('div', class_='side-list')
		if not side_list:
			print("Could not find list for 'Più letti questa settimana'")
		else:
			# Find all article items (first 3)
			articles = side_list.find_all('div', class_='side side-text', limit=3)

			print("Extracting top 3 most-read articles (title from sharing data-title + first paragraph from article page)\n")

			for i, article in enumerate(articles, 1):
				# Extract share title from the sharing div's data-title
				sharing_div = article.find('div', class_='sharing')
				share_title = None
				if sharing_div and sharing_div.has_attr('data-title'):
					share_title = sharing_div.get('data-title')

				# Fallback: use visible title if sharing title not present
				if not share_title:
					title_span = article.find('span', class_='title')
					if title_span and title_span.find('a'):
						share_title = title_span.find('a').get_text(strip=True)

				# Extract URL (prefer anchor href)
				article_url = None
				title_span = article.find('span', class_='title')
				if title_span and title_span.find('a'):
					href = title_span.find('a').get('href')
					if href:
						article_url = "https://www.gravinalife.it" + href
				# Fallback: try sharing data-url
				if not article_url and sharing_div and sharing_div.has_attr('data-url'):
					article_url = sharing_div.get('data-url')

				# Fetch article page and extract first paragraph content
				first_paragraph = None
				if article_url:
					try:
						article_page = requests.get(article_url, timeout=20)
						article_page.raise_for_status()
						article_soup = BeautifulSoup(article_page.text, 'html.parser')
						# Select any element that has both classes 'p' and 'first'
						first_el = article_soup.select_one('.p.first')
						if first_el:
							first_paragraph = first_el.get_text(" ", strip=True)
						else:
							# Gentle fallback: try the first <p> under a likely content container
							main_p = article_soup.select_one('div.content-wrapper p, article p')
							if main_p:
								first_paragraph = main_p.get_text(" ", strip=True)
					except Exception as e:
						first_paragraph = None

				# Print and store
				print(f"{i}. {share_title or '[No title found]'}")
				print(f"   URL: {article_url or '[No URL found]'}")
				print(f"   First paragraph: {first_paragraph or '[No content found]'}\n")

				rows.append({
					'rank': i,
					'title': share_title,
					'url': article_url,
					'first_paragraph': first_paragraph,
				})

			print(f"Total articles scraped: {len(rows)}")