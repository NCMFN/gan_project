import urllib.request
import re
from bs4 import BeautifulSoup
import pandas as pd
import time

urls = [
    "https://askbisht.com/journals/ieee-journal-of-biomedical-and-health-informatics",
    "https://askbisht.com/journals/health-education-and-health-promotion",
    "https://askbisht.com/journals/asia-pacific-journal-of-health-management",
    "https://askbisht.com/journals/journal-of-associated-medical-sciences",
    "https://askbisht.com/journals/journal-of-medical-systems",
    "https://askbisht.com/journals/chinese-journal-of-health-management",
    "https://askbisht.com/journals/health-information-science-and-systems",
    "https://askbisht.com/journals/international-journal-of-bioinformatics-research-and-applications",
    "https://askbisht.com/journals/acm-transactions-on-computing-for-healthcare",
    "https://askbisht.com/journals/applied-medical-informatics",
    "https://askbisht.com/journals/methods-of-information-in-medicine",
    "https://askbisht.com/journals/telehealth-and-medicine-today",
    "https://askbisht.com/journals/healthcare-switzerland",
    "https://askbisht.com/journals/statistical-methods-in-medical-research",
    "https://askbisht.com/journals/studies-in-health-technology-and-informatics",
    "https://askbisht.com/journals/patient-experience-journal",
    "https://askbisht.com/journals/telemedicine-and-e-health",
    "https://askbisht.com/journals/community-and-physician",
    "https://askbisht.com/journals/international-journal-of-reliable-and-quality-e-healthcare",
    "https://askbisht.com/journals/international-journal-of-statistics-in-medical-research"
]

results = []

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    return html

for url in urls:
    try:
        html = fetch(url)
        soup = BeautifulSoup(html, 'html.parser')

        title = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"

        # Publisher extraction
        publisher_match = re.search(r'publisher=.*?">(.*?)</a>', html, re.IGNORECASE)
        publisher = publisher_match.group(1).strip() if publisher_match else "Not specified"

        # Quartile extraction
        quartile_match = re.search(r'Current Quartile</div>\s*<div[^>]*>\s*<a[^>]*>(Q[1-4])</a>', html, re.IGNORECASE)
        if not quartile_match:
            quartile_match = re.search(r'quartile=q[1-4]"[^>]*>(Q[1-4])</a>', html, re.IGNORECASE)
        quartile = quartile_match.group(1).strip() if quartile_match else "Not specified"

        # Review time extraction
        review_time_match = re.search(r'Average Review Time: (.*?)(?:<| \()', html, re.IGNORECASE)
        if not review_time_match:
            # Let's see if there's any text mentioning "Review Time"
            review_time_match = re.search(r'Review Time.{0,20}?(\d+\s*(?:Weeks|Months|Days))', html, re.IGNORECASE)

        review_time = review_time_match.group(1).strip() if review_time_match else "Not specified"

        results.append({
            'Journal Name': title,
            'Publisher': publisher,
            'Average Review Time': review_time,
            'Scopus Quartile': quartile,
            'Publication Cost': 'Free / No APC'
        })
        time.sleep(0.5)
    except Exception as e:
        print(f"Error for {url}: {e}")

df = pd.DataFrame(results)
print(df.to_markdown())
df.to_csv('top_20_journals.csv', index=False)
