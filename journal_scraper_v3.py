import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import matplotlib.pyplot as plt
import seaborn as sns
import re
import concurrent.futures
from urllib.parse import quote, urlparse

# Constants
BASE_URL = "https://journalsearches.com"
MAIN_PAGE = f"{BASE_URL}/free-publishing-journals.php"
APC_FILE = "mu_directory_new.xls"
OUTPUT_CSV = "Ajournals_data.csv"
OUTPUT_XLSX = "Ajournals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def load_apc_data(filepath):
    """Loads the APC XLS file and returns a set of journal names and ISSNs."""
    print(f"Loading APC data from {filepath}...")
    try:
        # Based on inspection, header is at row 2 (index 2)
        df = pd.read_excel(filepath, header=2)
        # Filter for rows where NO# is numeric (actual journals)
        if 'NO#' in df.columns:
            df = df[pd.to_numeric(df['NO#'], errors='coerce').notnull()]

        # Normalize names and ISSNs
        journal_names = set()
        issns = set()

        if 'Journal' in df.columns:
            journal_names = set(df['Journal'].astype(str).str.strip().str.lower())

        if 'ISSN' in df.columns:
            issns = set(df['ISSN'].astype(str).str.strip().str.replace('-', '').replace(' ', ''))

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

        journals = []
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if 'journal.php?title=' in href:
                title = link.get_text(strip=True)

                # Handle URL encoding for the title param
                if '?' in href:
                    path, query = href.split('?', 1)
                    if 'title=' in query:
                        # Extract the raw title from query string to properly quote it
                        key, val = query.split('title=', 1)
                        # Remove any fragments
                        val = val.split('#')[0]
                        encoded_val = quote(val)
                        href = f"{path}?title={encoded_val}"

                full_url = f"{BASE_URL}/{href}" if not href.startswith('http') else href

                # Deduplicate
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

def check_doaj_apc(issn):
    """Checks DOAJ API for APC info."""
    if not issn or issn == 'Not Available':
        return None

    # DOAJ requires ISSN with dash often, or without. Let's try provided format.
    # The scraped ISSN might be comma separated. Use the first one.
    clean_issn = issn.split(',')[0].strip()

    url = f"https://doaj.org/api/v4/search/journals/issn:{clean_issn}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('results'):
                result = data['results'][0]
                bibjson = result.get('bibjson', {})
                apc = bibjson.get('apc', {})
                if apc:
                     currency = apc.get('currency', '')
                     price = apc.get('price', '')
                     if price == 0:
                         return "No Publication Fees (DOAJ)"
                     return f"{price} {currency} (DOAJ)"
                else:
                    # Check if it says 'no apc'
                    if not bibjson.get('apc_url'):
                        # This is heuristic.
                        pass
                    return "No APC data in DOAJ"
    except Exception:
        pass
    return None

def check_springer_review_time(url):
    """Checks Springer/SpringerOpen pages for review time."""
    if not url or 'springer' not in url:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            # Patterns: "Submission to first decision", "Time to first decision"
            # Followed by some number and days/weeks
            match = re.search(r'(Submission to first decision|Time to first decision).*?(\d+\s+(?:days|weeks))', text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(2)
    except Exception:
        pass
    return None

def scrape_journal_details(journal_entry, apc_names, apc_issns):
    """Scrapes details for a single journal."""
    journal_url = journal_entry['url']
    # Default data structure
    data = {
        'Journal Title': journal_entry['title'],
        'Publisher': 'Not Available',
        'ISSN': 'Not Available',
        'Review Time': 'Not Available',
        'APC': 'Not Available',
        'Scopus Indexing': 'Not Available',
        'Quartile': 'Not Available',
        'SJR': 'Not Available',
        'Source URL': 'Not Available',
        'Review Time Source': 'Aggregator',
        'APC Source': 'Unknown'
    }

    try:
        response = requests.get(journal_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()

        # --- Metadata ---
        # Journal Title
        # Journal Title from table or H1
        # Stop at "Publisher" or Newline
        title_match = re.search(r'Journal Title:\s*(.*?)(?:\s+Publisher|\s+ISSN|\n|$)', text)
        if title_match and len(title_match.group(1)) < 200: # Sanity check length
            data['Journal Title'] = title_match.group(1).strip()

        # Publisher
        pub_match = re.search(r'Publisher:\s*(.*?)(?:\s+(?:P-|E-)?ISSN|Review|Language|Country|\n|$)', text)
        if pub_match:
            data['Publisher'] = pub_match.group(1).strip()

        # ISSN
        issn_match = re.search(r'(?:P-|E-)?ISSN:\s*([0-9X\-,\s]+)(?:\s+[A-Z][a-z]+|Review|\n|$)', text)
        if issn_match:
            data['ISSN'] = issn_match.group(1).strip()

        # Source URL
        # Found in "Sources: <a href=...>"
        # Using soup to find the link in "Sources" section might be safer than regex on text
        sources_header = soup.find(lambda tag: tag.name == "b" and "Sources:" in tag.get_text())
        if sources_header:
            # The link usually follows
            link = sources_header.find_next('a', href=True)
            if link:
                data['Source URL'] = link['href']

        # --- Metrics from Aggregator (journalsearches.com) ---

        # Review Time
        # "publishes research articles in 12 weeks on an average"
        time_match = re.search(r'publishes research articles in\s*(\d+\s*weeks?)', text, re.IGNORECASE)
        if time_match:
            data['Review Time'] = time_match.group(1)
            data['Review Time Source'] = "journalsearches.com"
        else:
             # Fallback: check table "Processing Time (Weeks): 12"
             table_time = re.search(r'Processing Time \(Weeks\):\s*(\d+)', text)
             if table_time:
                 data['Review Time'] = f"{table_time.group(1)} weeks"
                 data['Review Time Source'] = "journalsearches.com"

        # APC
        # Check APC file first
        norm_title = data['Journal Title'].lower().strip()
        raw_issn = data['ISSN']
        issn_candidates = [x.strip().replace('-', '') for x in re.split(r'[,\s]+', raw_issn) if x.strip()]

        in_mu_list = (norm_title in apc_names) or any(issn in apc_issns for issn in issn_candidates)

        if in_mu_list:
             data['APC'] = "Free (MU Directory)"
             data['APC Source'] = "MU Directory"
        else:
             # Check website text
             if "does not charge any publication fee" in text.lower():
                 data['APC'] = "Free (Stated on Website)"
                 data['APC Source'] = "journalsearches.com"
             elif "publication fee" in text.lower():
                 # Maybe extract fee?
                 fee_match = re.search(r'publication fee\s*is\s*([\$\€\£]\d+)', text, re.IGNORECASE)
                 if fee_match:
                     data['APC'] = fee_match.group(1)
                     data['APC Source'] = "journalsearches.com"

        # Scopus Indexing
        # Check "Indexing" section
        indexing_section = soup.find(lambda tag: tag.name == "h2" and "Indexing" in tag.get_text())
        if indexing_section:
            # Look at siblings until next h2
            idx_text = ""
            curr = indexing_section.find_next_sibling()
            while curr and curr.name != "h2":
                idx_text += curr.get_text() + " "
                curr = curr.find_next_sibling()

            if "Scopus" in idx_text:
                data['Scopus Indexing'] = "Indexed"
            else:
                data['Scopus Indexing'] = "Not Indexed"
        else:
            # Fallback global search
            if "Indexed in" in text and "Scopus" in text:
                 data['Scopus Indexing'] = "Indexed"
            elif "Scopus Coverage" in text:
                 data['Scopus Indexing'] = "Indexed"
            else:
                 data['Scopus Indexing'] = "Not Indexed"

        # Quartile & SJR
        # Look for "Quartile: Q1" or "SJR: 0.418"
        # Stop at H-Index, Newline, or next label
        q_match = re.search(r'Quartile:\s*(.*?)(?:H-Index|SJR|\n|$)', text, re.IGNORECASE)
        if q_match and "Q" in q_match.group(1):
             data['Quartile'] = q_match.group(1).strip()
        else:
             # Fallback: specific match for Q1-Q4
             q_specific = re.search(r'(Q[1-4])', text)
             if q_specific and "Quartile" in text:
                 data['Quartile'] = q_specific.group(1)

        sjr_match = re.search(r'SJR.*:\s*([\d\.]+)', text)
        if sjr_match:
            data['SJR'] = sjr_match.group(1)

        # --- Enrichment (External Sources) ---

        # DOAJ APC Check (if not already found in MU)
        if data['APC Source'] != "MU Directory":
            doaj_apc = check_doaj_apc(data['ISSN'])
            if doaj_apc:
                data['APC'] = doaj_apc
                data['APC Source'] = "DOAJ"

        # Springer Review Time Check (only if source is Springer)
        if "springer" in data['Source URL'].lower():
            springer_time = check_springer_review_time(data['Source URL'])
            if springer_time:
                data['Review Time'] = springer_time
                data['Review Time Source'] = "Springer (Direct)"

        return data

    except Exception as e:
        # print(f"Error scraping {journal_url}: {e}")
        return None

def process_journal(journal, apc_names, apc_issns):
    """Wrapper for thread execution."""
    return scrape_journal_details(journal, apc_names, apc_issns)

def main():
    start_time = time.time()

    # 1. Load APC Data
    apc_names, apc_issns = load_apc_data(APC_FILE)

    # 2. Get Journal List
    journal_list = get_journal_list()
    if not journal_list:
        print("No journals found. Exiting.")
        return

    print(f"Starting processing of {len(journal_list)} journals with threading...")

    # 3. Process Journals concurrently
    scraped_data = []
    # Use max_workers=10 to be polite but faster
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_journal = {executor.submit(process_journal, j, apc_names, apc_issns): j for j in journal_list}

        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_journal):
            data = future.result()
            if data:
                scraped_data.append(data)

            completed_count += 1
            if completed_count % 10 == 0:
                print(f"Processed {completed_count}/{len(journal_list)}")

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
        plt.tight_layout()
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
    missing_apc = len(df[df['APC'] == 'Not Available'])

    print(f"Journals with missing Review Time: {missing_review}")
    print(f"Journals with missing APC info: {missing_apc}")

    if 'Scopus Indexing' in df.columns:
        print("\nScopus Indexing Distribution:")
        print(df['Scopus Indexing'].value_counts())

    print(f"\nTotal Time Taken: {time.time() - start_time:.2f} seconds")
    print("\nProcess completed successfully.")

if __name__ == "__main__":
    main()
