import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_all_links(url):
    try:
        # 1. Fetch the webpage
        headers = {'User-Agent': 'Mozilla/5.0'} # Pretend to be a browser
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Check if the page loaded correctly

        # 2. Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 3. Find all 'a' tags with an 'href' attribute
        links = set() # Use a set to avoid duplicates
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            
            # 4. Handle relative URLs (e.g., "/about" -> "https://site.com/about")
            full_url = urljoin(url, link)
            links.add(full_url)

        print(f"Found {len(links)} unique links:\n")
        for l in sorted(links):
            print(l)

    except Exception as e:
        print(f"Error: {e}")

# Test it out
target_url = input("Enter the URL (include https://): ")
get_all_links(target_url)
