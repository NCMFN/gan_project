import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote

class ScraperV4:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_journal(self, title):
        url = f"https://journalsearches.com/journal.php?title={quote(title)}"
        data = {
            "Quartile": "Not Available",
            "Scopus Status": "Not Available",
            "Review Time": "Not Available",
            "Source URL": url
        }

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return data

            text = response.text

            # 1. Quartile
            q_match = re.search(r'Quartile:.*?Q([1-4])', text, re.IGNORECASE)
            if q_match:
                data['Quartile'] = f"Q{q_match.group(1)}"

            # 2. Scopus Status
            cov_match = re.search(r'Coverage:.*?(\d{4})[-–\s]+(\d{4}|Present)', text, re.IGNORECASE)
            if cov_match:
                end_year = cov_match.group(2)
                if end_year.lower() == 'present' or int(end_year) >= 2023:
                    data['Scopus Status'] = "Indexed"
                else:
                    data['Scopus Status'] = "Not Indexed (Coverage ended)"
            else:
                if "Indexed in Scopus" in text or "Scopus" in text and "SJR" in text:
                     data['Scopus Status'] = "Likely Indexed"
                else:
                     data['Scopus Status'] = "Not Indexed"

            # 3. Review Time
            # Refined Regex: Look for number followed by time unit
            rt_patterns = [
                r'publishes research articles in\s+(\d+\s+(?:weeks?|months?|days?))',
                r'Review Time.*?(\d+\s+(?:weeks?|months?|days?))',
                r'Time to First Decision.*?(\d+\s+(?:weeks?|months?|days?))'
            ]

            for pat in rt_patterns:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    data['Review Time'] = match.group(1)
                    break

            return data

        except Exception as e:
            return data

if __name__ == "__main__":
    scraper = ScraperV4()
    print("Testing 'Nature'...")
    print(scraper.scrape_journal("Nature"))
    print("\nTesting 'PLOS ONE'...")
    print(scraper.scrape_journal("PLOS ONE"))
