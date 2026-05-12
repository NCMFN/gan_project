import pandas as pd
import requests
import concurrent.futures
import time
import re
import os
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import seaborn as sns
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
DOAJ_CSV_URL = "https://doaj.org/csv"
DOAJ_CSV_FILE = "doaj_journals.csv"
MU_DIRECTORY_FILE = "mu_directory_2023.xls"
OUTPUT_CSV = "Gjournals_data.csv"
OUTPUT_XLSX = "Gjournals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"
BASE_URL = "https://journalsearches.com"

# Setup Session
def get_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })
    return session

SESSION = get_session()

def fetch_doaj_journals(limit=None):
    """Fetches all journals from DOAJ matching the No-APC criteria via CSV dump."""
    print("Fetching journals from DOAJ CSV dump...")

    # Download CSV if not exists or force update (here we assume check first)
    # Using streaming download for memory efficiency if needed, but 25MB is small.
    try:
        if not os.path.exists(DOAJ_CSV_FILE):
            print("Downloading DOAJ CSV...")
            resp = SESSION.get(DOAJ_CSV_URL)
            resp.raise_for_status()
            with open(DOAJ_CSV_FILE, 'wb') as f:
                f.write(resp.content)

        print("Reading CSV...")
        df = pd.read_csv(DOAJ_CSV_FILE)

        # Filter for No APC and No Other Fees
        # Columns: 'APC', 'Has other fees'
        # Values expected: 'No'

        # Verify columns exist
        if 'APC' not in df.columns or 'Has other fees' not in df.columns:
            print("Error: Expected columns not found in DOAJ CSV")
            return []

        # Filter
        df_filtered = df[(df['APC'] == 'No') & (df['Has other fees'] == 'No')]

        if limit:
            df_filtered = df_filtered.head(limit)

        journals = []
        for _, row in df_filtered.iterrows():
            title = row['Journal title']
            publisher = row['Publisher'] if pd.notna(row['Publisher']) else 'Unknown'
            # ISSN
            eissn = row['Journal EISSN (online version)']
            pissn = row['Journal ISSN (print version)']
            issn = eissn if pd.notna(eissn) else pissn
            if pd.isna(issn):
                issn = "Unknown"

            journals.append({
                'Journal Title': str(title).strip(),
                'Publisher': str(publisher).strip(),
                'ISSN': str(issn).strip(),
                'APC': 'Free (DOAJ)'
            })

        print(f"Total DOAJ journals filtered: {len(journals)}")
        return journals

    except Exception as e:
        print(f"Error fetching/processing DOAJ CSV: {e}")
        return []

def load_mu_directory(filepath):
    """Loads the MU directory XLS to get a set of verified free journals."""
    print(f"Loading MU directory from {filepath}...")
    try:
        # Header at row index 2 (row 3) based on inspection
        df = pd.read_excel(filepath, header=2)
        # Normalize
        journal_names = set(df['Journal'].astype(str).str.strip().str.lower())
        print(f"Loaded {len(journal_names)} journals from MU directory.")
        return journal_names
    except Exception as e:
        print(f"Error loading MU directory: {e}")
        return set()

def scrape_details(journal):
    """Scrapes details for a single journal from journalsearches.com."""
    title = journal['Journal Title']
    # Use the journal title to construct the search URL
    # Note: journalsearches.com expects exact title match often
    encoded_title = quote(title)
    url = f"{BASE_URL}/journal.php?title={encoded_title}"

    details = {
        'Source URL': url,
        'Review Time': 'Not Available',
        'Scopus Indexing': 'Not Available',
        'Quartile': 'Not Available',
        # Keep original publisher from DOAJ unless we find a better one
        'Publisher': journal['Publisher']
    }

    try:
        response = SESSION.get(url, timeout=10)
        if response.status_code != 200:
            return details # Return defaults if page not found

        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()

        # 1. Review Time
        # Pattern example: "publishes research articles in 12 weeks on an average"
        time_match = re.search(r'publishes research articles in\s+(\d+\s+\w+)', text, re.IGNORECASE)
        if time_match:
            details['Review Time'] = time_match.group(1)

        # 2. Scopus Indexing
        # Pattern: "Indexed in ... Scopus" or "Scopus Coverage"
        if "Scopus" in text and ("Indexed in" in text or "Coverage" in text):
            details['Scopus Indexing'] = "Indexed"
        else:
            details['Scopus Indexing'] = "Not Indexed"

        # 3. Publisher
        # Using regex on cleaned text is better
        # Look for "Publisher:" followed by text until newline or ISSN/Language keywords
        pub_match = re.search(r'Publisher:\s*(.*?)(?:\s+(?:P-|E-)?ISSN|Review|Language|Country|\n|$)', text)
        if pub_match:
            cand_pub = pub_match.group(1).strip()
            if cand_pub and len(cand_pub) < 100: # Sanity check for length
                details['Publisher'] = cand_pub

        # 4. Quartile
        # Look for "Quartile: Q1" or "Q1 (20xx)"
        q_match = re.search(r'Quartile:\s*(Q[1-4])', text, re.IGNORECASE)
        if q_match:
            details['Quartile'] = q_match.group(1)

    except Exception as e:
        # print(f"Error scraping {title}: {e}")
        pass

    return details

def main():
    print("Starting Journal Scraper...")

    # 1. Load MU Directory
    mu_list = load_mu_directory(MU_DIRECTORY_FILE)

    # 2. Fetch DOAJ Journals
    doaj_journals = fetch_doaj_journals()
    if not doaj_journals:
        print("No journals found from DOAJ. Exiting.")
        return

    # 3. Scrape Details Concurrently
    print(f"Scraping details for {len(doaj_journals)} journals with 50 workers...")

    final_data = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_journal = {executor.submit(scrape_details, journal): journal for journal in doaj_journals}

        completed = 0
        total = len(doaj_journals)

        for future in concurrent.futures.as_completed(future_to_journal):
            journal = future_to_journal[future]
            try:
                details = future.result()

                # Merge Data
                merged = journal.copy()
                merged.update(details)

                # Refine APC based on MU Directory
                # Check by Title
                norm_title = merged['Journal Title'].lower().strip()
                if norm_title in mu_list:
                    merged['APC'] = "Free (DOAJ + MU Directory)"

                final_data.append(merged)

            except Exception as e:
                print(f"Exception for {journal['Journal Title']}: {e}")

            completed += 1
            if completed % 100 == 0:
                print(f"Processed {completed}/{total} journals")

    # 4. Create DataFrame
    df = pd.DataFrame(final_data)

    # 5. Export Data
    print(f"Exporting data to {OUTPUT_CSV} and {OUTPUT_XLSX}...")
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    # 6. Visualization
    print("Generating Scopus status visualization...")
    plt.figure(figsize=(10, 6))
    if 'Scopus Indexing' in df.columns:
        counts = df['Scopus Indexing'].value_counts()
        sns.barplot(x=counts.index, y=counts.values)
        plt.title('Count of Journals by Scopus Indexing Status')
        plt.xlabel('Scopus Status')
        plt.ylabel('Count')
        plt.savefig(PLOT_FILE)
        plt.close()
        print(f"Visualization saved to {PLOT_FILE}")

    # 7. Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals Processed: {len(df)}")

    missing_review = len(df[df['Review Time'] == 'Not Available'])
    scopus_counts = df['Scopus Indexing'].value_counts().to_dict()

    print(f"Journals with missing Review Time: {missing_review}")
    print(f"Scopus Indexing Status: {scopus_counts}")
    print("\nData collected successfully.")

if __name__ == "__main__":
    main()
