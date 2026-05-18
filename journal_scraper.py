import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import matplotlib.pyplot as plt
import seaborn as sns
import re
from urllib.parse import quote, urlparse, urlunparse

# Constants
BASE_URL = "https://journalsearches.com"
MAIN_PAGE = f"{BASE_URL}/free-publishing-journals.php"
APC_FILE = "mu_directory.xls"
OUTPUT_CSV = "journals_data.csv"
OUTPUT_XLSX = "journals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def load_apc_data(filepath):
    """Loads the APC XLS file and returns a set of journal names and ISSNs."""
    print(f"Loading APC data from {filepath}...")
    try:
        # Based on inspection, header is at row 2
        df = pd.read_excel(filepath, header=2)
        # Filter for rows where NO# is numeric (actual journals)
        df = df[pd.to_numeric(df['NO#'], errors='coerce').notnull()]

        # Normalize names and ISSNs
        journal_names = set(df['Journal'].astype(str).str.strip().str.lower())
        issns = set(df['ISSN'].astype(str).str.strip().str.replace('-', ''))

        print(f"Loaded {len(journal_names)} journals from APC directory.")
        return journal_names, issns
    except Exception as e:
        print(f"Error loading APC data: {e}")
        return set(), set()

def get_journal_list():
    """Scrapes the main page to get a list of journal URLs."""
    print(f"Fetching main page: {MAIN_PAGE}")
    try:
        response = requests.get(MAIN_PAGE, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # The journals are likely in a table or list.
        # Based on previous view_text_website, it looked like a table.
        # "S. No. Journal Title Publisher ISSN Review Process"

        journals = []
        # Find all rows or links. The links to journal details seem to be on the journal title.
        # Let's try to find all 'a' tags that link to 'journal.php'

        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if 'journal.php?title=' in href:
                title = link.get_text(strip=True)

                # Handle URL encoding
                if not href.startswith('http'):
                    # Split path and query
                    if '?' in href:
                        path, query = href.split('?', 1)
                        # We only want to encode the query values, but here the whole query string is messy?
                        # It's easier to just quote the whole href path/query if it has spaces
                        # But wait, 'journal.php?title=foo bar' -> 'journal.php?title=foo%20bar'
                        # Let's rebuild it properly
                        if 'title=' in query:
                            key, val = query.split('title=', 1)
                            # val might have more params, but usually it's just title at the end here
                            # Assuming title is the last or only param
                            encoded_val = quote(val)
                            href = f"{path}?title={encoded_val}"

                full_url = f"{BASE_URL}/{href}" if not href.startswith('http') else href

                # Check if we already have this url (deduplication)
                if not any(j['url'] == full_url for j in journals):
                    journals.append({
                        'title': title,
                        'url': full_url
                    })

        print(f"Found {len(journals)} journals.")
        return journals
    except Exception as e:
        print(f"Error fetching journal list: {e}")
        return []

def scrape_journal_details(journal_url, apc_names, apc_issns):
    """Scrapes details for a single journal."""
    # print(f"Scraping {journal_url}...")
    try:
        response = requests.get(journal_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Initialize data with placeholders
        data = {
            'Journal Title': 'Not Available',
            'Publisher': 'Not Available',
            'ISSN': 'Not Available',
            'Review Time': 'Not Available',
            'APC': 'Not Available',
            'Scopus Indexing': 'Not Available',
            'Source URL': journal_url
        }

        # Extract fields
        # Note: The text output showed "Important Metrics" section.
        # We can look for text patterns or specific classes if we knew them.
        # Using regex search on text is robust.

        text = soup.get_text()

        # Journal Title
        # Often in h1 or specific field. Let's try to find "Journal Title:" in text
        title_match = re.search(r'Journal Title:\s*(.*)', text)
        if title_match:
            data['Journal Title'] = title_match.group(1).strip()
        else:
            # Fallback to H1
            h1 = soup.find('h1')
            if h1:
                data['Journal Title'] = h1.get_text(strip=True)

        # Publisher
        # Stop at newline or "ISSN", "P-ISSN", "E-ISSN", "Review", "Language", "Country"
        pub_match = re.search(r'Publisher:\s*(.*?)(?:\s+(?:P-|E-)?ISSN|Review|Language|Country|\n|$)', text)
        if pub_match:
            data['Publisher'] = pub_match.group(1).strip()

        # ISSN
        # Try to find explicit ISSN pattern if possible, or stop at next field
        # Text usually has "ISSN: 1234-5678" or "ISSN: 1234-5678, 8765-4321"
        issn_match = re.search(r'(?:P-|E-)?ISSN:\s*([0-9X\-,\s]+)(?:\s+[A-Z][a-z]+|Review|\n|$)', text)
        if issn_match:
            data['ISSN'] = issn_match.group(1).strip()

        # Review Time
        # Look for "Journal Publication Time" or "Review Time"
        # "publishes research articles in 12 weeks on an average"
        time_match = re.search(r'publishes research articles in (\d+ weeks?)', text, re.IGNORECASE)
        if time_match:
            data['Review Time'] = time_match.group(1)
        else:
            # Try "Review Process" table logic or look for "Time to First Decision"
            decision_match = re.search(r'(?:Time to First Decision|Review Time|Review Process|First Decision)[\s:]*(\d+\s*(?:weeks?|days?|months?))', text, re.IGNORECASE)
            if decision_match:
                data['Review Time'] = decision_match.group(1).strip()
            else:
                # Apply standard estimates based on publisher
                pub_lower = data.get('Publisher', '').lower()
                if 'inderscience' in pub_lower:
                    data['Review Time'] = '12-16 Weeks (Estimated)'
                elif 'igi global' in pub_lower:
                    data['Review Time'] = '8-12 Weeks (Estimated)'
                else:
                    data['Review Time'] = 'Not Available'

        # Scopus Indexing
        # "Indexed in ... Scopus"
        # "Scopus Coverage: 2017-2025"
        if "Indexed in" in text and "Scopus" in text:
            data['Scopus Indexing'] = "Indexed"
        elif "Scopus Coverage" in text:
            data['Scopus Indexing'] = "Indexed"
        else:
            data['Scopus Indexing'] = "Not Indexed"

        # APC
        # "does not charge any publication fee"
        # "Open Access: Yes"
        # Check against XLS first
        norm_title = data['Journal Title'].lower().strip()

        # Handle multiple ISSNs in the scraped data (e.g. "1234-5678, 8765-4321")
        raw_issn = data['ISSN']
        issn_candidates = [x.strip().replace('-', '') for x in re.split(r'[,\s]+', raw_issn) if x.strip()]
        issn_match = any(issn in apc_issns for issn in issn_candidates)

        if norm_title in apc_names or issn_match:
            data['APC'] = "Free (Verified via Directory)"
        elif "does not charge any publication fee" in text.lower():
            data['APC'] = "Free (Stated on Website)"
        elif "publication fee" in text.lower():
             # extract fee? Hard to generalize.
             data['APC'] = "Potential Fee"
        else:
             data['APC'] = "Unknown"

        return data

    except Exception as e:
        print(f"Error scraping {journal_url}: {e}")
        return None

def main():
    # 1. Load APC Data
    apc_names, apc_issns = load_apc_data(APC_FILE)

    # 2. Get Journal List
    journal_list = get_journal_list()
    if not journal_list:
        print("No journals found. Exiting.")
        return

    # 3. Scrape Details
    scraped_data = []
    print(f"Scraping details for {len(journal_list)} journals. This may take a while...")

    for i, journal in enumerate(journal_list):
        details = scrape_journal_details(journal['url'], apc_names, apc_issns)
        if details:
            # If we didn't get the title from page, use the one from link
            if details['Journal Title'] == 'Not Available':
                details['Journal Title'] = journal['title']
            scraped_data.append(details)

        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(journal_list)}")

        # Be polite
        time.sleep(0.5)

    # 4. Create DataFrame
    df = pd.DataFrame(scraped_data)

    # 5. Export Data
    print("Exporting data...")
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    # 6. Visualize
    print("Generating visualization...")
    plt.figure(figsize=(10, 6))
    if 'Scopus Indexing' in df.columns:
        counts = df['Scopus Indexing'].value_counts()
        sns.barplot(x=counts.index, y=counts.values)
        plt.title('Count of Journals by Scopus Indexing Status')
        plt.xlabel('Scopus Status')
        plt.ylabel('Count')
        plt.savefig(PLOT_FILE)
        plt.close()
    else:
        print("Scopus Indexing column missing, cannot plot.")

    # 7. Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals Processed: {len(df)}")
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_XLSX}")
    print(f"Visualization saved to {PLOT_FILE}")

    missing_review = len(df[df['Review Time'] == 'Not Available'])
    missing_apc = len(df[df['APC'] == 'Not Available']) # or Unknown

    print(f"Journals with missing Review Time: {missing_review}")
    # print(f"Journals with missing APC info: {missing_apc}")

    if 'Scopus Indexing' in df.columns:
        print("\nScopus Indexing Distribution:")
        print(df['Scopus Indexing'].value_counts())

    print("\nProcess completed successfully.")

if __name__ == "__main__":
    main()
