import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import matplotlib.pyplot as plt
import seaborn as sns
import os
import urllib3
import concurrent.futures

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
SOURCE_FILE = 'source_journals.xlsx'
MU_FILE = 'mu_directory_new.xls'
OUTPUT_CSV = '3journals_data.csv'
OUTPUT_XLSX = '3journals_data.xlsx'
PLOT_FILE = 'scopus_status_chart.png'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def load_data():
    """Loads source data and MU directory."""
    print("Loading source data...")
    try:
        source_df = pd.read_excel(SOURCE_FILE)
    except Exception as e:
        print(f"Error loading source file: {e}")
        return None, None

    print("Loading MU Directory...")
    try:
        # Based on inspection, header is at row index 2
        mu_df = pd.read_excel(MU_FILE, header=2)
        # Create a set of normalized titles and ISSNs for fast lookup
        # Assuming 'Journal' column holds the name
        mu_titles = set(mu_df['Journal'].astype(str).str.strip().str.lower())
        # Clean ISSNs
        mu_issns = set()
        if 'ISSN' in mu_df.columns:
            for issn in mu_df['ISSN'].dropna().astype(str):
                mu_issns.add(issn.strip().replace('-', ''))

        return source_df, (mu_titles, mu_issns)
    except Exception as e:
        print(f"Error loading MU file: {e}")
        return source_df, (set(), set())

def get_doaj_apc(title, issn):
    """Queries DOAJ API for APC info."""
    # Try ISSN first as it's more precise
    if issn and isinstance(issn, str):
        # DOAJ API expects ISSN
        url = f"https://doaj.org/api/v4/search/journals/{issn}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('results'):
                    return extract_doaj_apc(data['results'][0])
        except Exception:
            pass

    # Try Title search
    if title:
        url = f"https://doaj.org/api/v4/search/journals/title:{requests.utils.quote(title)}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('results'):
                    return extract_doaj_apc(data['results'][0])
        except Exception:
            pass

    return None

def extract_doaj_apc(result):
    """Extracts APC string from DOAJ result object."""
    try:
        bibjson = result.get('bibjson', {})
        apc = bibjson.get('apc', {})
        if apc.get('has_apc'):
            currency = apc.get('currency', '')
            price = apc.get('price', '')
            return f"{price} {currency} (DOAJ)"
        else:
            return "No APC (DOAJ)"
    except:
        return None

def check_scimago(title):
    """Checks Scimago for indexing status."""
    # Note: Scimago blocks automated requests often.
    # We will try, but expect 403.
    url = f"https://www.scimagojr.com/journalsearch.php?q={requests.utils.quote(title)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            if "Displaying" in r.text or "Total results" in r.text:
                 # Minimal check: if we see search results, it might be there.
                 # Better: check for the specific link to the journal details
                 soup = BeautifulSoup(r.text, 'html.parser')
                 # If there is a result link
                 results = soup.find_all('div', class_='search_results')
                 if results:
                     return "Indexed (Scimago)"
    except Exception:
        pass
    return None

def scrape_website(url):
    """Scrapes the journal homepage for clues."""
    data = {
        'review_time': None,
        'apc': None,
        'scopus': None
    }

    if not isinstance(url, str) or not url.startswith('http'):
        return data

    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        text = soup.get_text(" ", strip=True)
        lower_text = text.lower()

        # --- Review Time ---
        # Look for "X weeks" or "X days" near "first decision" or "review"
        # Pattern 1: "Time to first decision: X weeks"
        # Pattern 2: "First decision: X weeks"
        # Pattern 3: "Average review time: X days"

        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:weeks?|days?)\s+(?:to|for)\s+(?:first\s+decision|review)',
            r'(?:first\s+decision|review\s+time)(?:\s+is)?\s*(?:[:\-])?\s*(\d+(?:\.\d+)?)\s*(?:weeks?|days?)',
            r'average\s+time\s+to\s+first\s+decision\s*(?:is)?\s*(?:[:\-])?\s*(\d+(?:\.\d+)?)\s*(?:weeks?|days?)'
        ]

        for pat in patterns:
            match = re.search(pat, lower_text)
            if match:
                # We found a number, need to grab the unit too to be useful
                # Let's just grab the whole match string
                # Re-running search on original text (case insensitive) to get the pretty string
                match_orig = re.search(pat, text, re.IGNORECASE)
                if match_orig:
                    data['review_time'] = match_orig.group(0)
                    break

        # --- APC ---
        if "no publication fee" in lower_text or "no article processing charge" in lower_text or "free of charge" in lower_text:
            data['apc'] = "Free (Website)"
        elif "article processing charge" in lower_text or "apc" in lower_text:
            # Try to find a price? Too complex for now, just flag it.
            # data['apc'] = "Check Website"
            pass

        # --- Scopus ---
        if "scopus" in lower_text:
            # Check context to avoid "Not indexed in Scopus"
            if "indexed in" in lower_text and "scopus" in lower_text:
                data['scopus'] = "Indexed (Website)"
            elif "scopus" in lower_text:
                # Fallback
                 data['scopus'] = "Likely Indexed (Website)"

    except Exception as e:
        # print(f"Failed to scrape {url}: {e}")
        pass

    return data

def process_journal(row, mu_data):
    mu_titles, mu_issns = mu_data

    title = str(row.get('Journal Title', '')).strip()
    issn = str(row.get('ISSN', '')).strip() if pd.notnull(row.get('ISSN')) else None
    url = row.get('Link')

    result = {
        'Journal Name': title,
        'Publisher': row.get('Publisher', 'Unknown'),
        'APC': 'Not Available',
        'Review Time': 'Not Available',
        'Scopus Status': 'Not Available',
        'Source URL': url
    }

    # 1. APC Logic
    # Check MU
    if title.lower() in mu_titles or (issn and issn.replace('-', '') in mu_issns):
        result['APC'] = "Free (MU Directory)"
    else:
        # Check DOAJ
        doaj_apc = get_doaj_apc(title, issn)
        if doaj_apc:
            result['APC'] = doaj_apc

    # 2. Scrape Website (for missing APC, Review Time, Scopus)
    web_data = scrape_website(url)

    # Fill APC if still missing
    if result['APC'] == 'Not Available' and web_data['apc']:
        result['APC'] = web_data['apc']

    # Fill Review Time
    if web_data['review_time']:
        result['Review Time'] = web_data['review_time']

    # 3. Scopus Logic
    # Check Scimago
    scimago_status = check_scimago(title)
    if scimago_status:
        result['Scopus Status'] = scimago_status
    elif web_data['scopus']:
         result['Scopus Status'] = web_data['scopus']
    else:
        # Fallback to source file claim if available
        source_claim = str(row.get('Scopus', '')).lower()
        if 'scopus' in source_claim and 'yes' in source_claim or source_claim == 'scopus':
             result['Scopus Status'] = "Indexed (Source File)"
        else:
             result['Scopus Status'] = "Not Indexed"

    return result

def main(limit=None):
    source_df, mu_data = load_data()
    if source_df is None:
        return

    processed_data = []
    total = len(source_df)
    if limit:
        total = min(total, limit)
        print(f"Running partial execution on first {total} journals.")
    else:
        print(f"Running full execution on {total} journals.")

    # Prepare rows
    rows_to_process = []
    for i, row in source_df.iterrows():
        if limit and i >= limit:
            break
        rows_to_process.append(row)

    # Use ThreadPoolExecutor
    max_workers = 10
    print(f"Starting processing with {max_workers} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_row = {executor.submit(process_journal, row, mu_data): i for i, row in enumerate(rows_to_process)}

        for future in concurrent.futures.as_completed(future_to_row):
            idx = future_to_row[future]
            try:
                res = future.result()
                processed_data.append(res)
                if len(processed_data) % 10 == 0:
                    print(f"Processed {len(processed_data)}/{len(rows_to_process)} journals.")
            except Exception as e:
                print(f"Error processing row {idx}: {e}")

    # Create DataFrame
    df = pd.DataFrame(processed_data)

    # Export
    print(f"Exporting to {OUTPUT_CSV} and {OUTPUT_XLSX}...")
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    # Visualization
    print("Generating visualization...")
    plt.figure(figsize=(10, 6))
    if 'Scopus Status' in df.columns:
        counts = df['Scopus Status'].value_counts()
        sns.barplot(x=counts.index, y=counts.values)
        plt.title('Count of Journals by Scopus Indexing Status')
        plt.xlabel('Scopus Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(PLOT_FILE)
        plt.close()

    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals Processed: {len(df)}")
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_XLSX}")
    print(f"Visualization saved to {PLOT_FILE}")

    missing_apc = len(df[df['APC'] == 'Not Available'])
    missing_rt = len(df[df['Review Time'] == 'Not Available'])
    print(f"Journals with missing APC: {missing_apc}")
    print(f"Journals with missing Review Time: {missing_rt}")
    print("\nScopus Status Distribution:")
    print(df['Scopus Status'].value_counts())

if __name__ == "__main__":
    import sys
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    main(limit)
