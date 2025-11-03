from bs4 import BeautifulSoup
import requests

# empty list to contain the scraped data
rows = []

#open the website

url = "https://www.reuters.com/"
page = requests.get(url)
page_content = page.content
print(page_content)