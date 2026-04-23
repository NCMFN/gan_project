import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import os
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import concurrent.futures
import urllib3

# Disable warnings for unverified HTTPS
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
MU_URL = "https://www.mu.ac.zm/static/final-mu-directory-without-apc-2023.xls"
DOAJ_URL = "https://doaj.org/csv"
SOURCE1_URL = "https://docs.google.com/spreadsheets/d/1E9miIQX4YVslP-AXTONUlF_VkXMyOCAW/export?format=xlsx"

MU_FILE = "mu_directory_new.xls"
DOAJ_FILE = "doaj_journals.csv"
SOURCE_FILE = "source1_journals.xlsx"
OUTPUT_CSV = "2journals_data.csv"
OUTPUT_XLSX = "2journals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def download_file(url, filepath):
    if os.path.exists(filepath):
        print(f"File {filepath} already exists. Skipping download.")
        return

    print(f"Downloading {url} to {filepath}...")
    try:
        response = requests.get(url, headers=HEADERS, stream=True, verify=False, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def download_inputs():
    print("Verifying input files...")
    download_file(SOURCE1_URL, SOURCE_FILE)
    download_file(MU_URL, MU_FILE)
    download_file(DOAJ_URL, DOAJ_FILE)

def normalize_issn(issn):
    if not isinstance(issn, str) or pd.isna(issn):
        return ""
    return re.sub(r'[^0-9X]', '', issn.strip().upper())

def normalize_title(title):
    if not isinstance(title, str) or pd.isna(title):
        return ""
    return title.strip().lower()

def load_mu_data(filepath):
    print(f"Loading MU Directory data from {filepath}...")
    try:
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found. Skipping MU data.")
            return set(), set()

        df = pd.read_excel(filepath, header=2)
        df = df.dropna(subset=['Journal'])

        no_apc_journals = set()
        no_apc_issns = set()

        for _, row in df.iterrows():
            title = normalize_title(str(row['Journal']))
            if title:
                no_apc_journals.add(title)
            if 'ISSN' in row:
                issn = normalize_issn(str(row['ISSN']))
                if issn:
                    no_apc_issns.add(issn)

        print(f"Loaded {len(no_apc_journals)} journals from MU Directory.")
        return no_apc_journals, no_apc_issns
    except Exception as e:
        print(f"Error loading MU data: {e}")
        return set(), set()

def load_doaj_data(filepath):
    print(f"Loading DOAJ data from {filepath}...")
    try:
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found. Skipping DOAJ data.")
            return {}

        usecols = ['Journal title', 'Journal ISSN (print version)', 'Journal EISSN (online version)', 'APC', 'APC amount']

        # Handle potential read errors (large file)
        try:
            df = pd.read_csv(filepath, usecols=usecols, dtype=str, on_bad_lines='skip')
        except Exception as csv_err:
             print(f"CSV Read Error: {csv_err}. Attempting with latin1.")
             df = pd.read_csv(filepath, usecols=usecols, dtype=str, encoding='latin1', on_bad_lines='skip')

        doaj_map = {}

        for _, row in df.iterrows():
            apc_status = str(row['APC']).strip()

            if apc_status.lower() == 'yes':
                amount = str(row['APC amount']).strip()
                if amount.lower() == 'nan':
                    amount = "Yes (Amount not specified)"
                apc_info = f"Yes - {amount}"
            else:
                apc_info = "Free (DOAJ)"

            p_issn = normalize_issn(row.get('Journal ISSN (print version)', ''))
            e_issn = normalize_issn(row.get('Journal EISSN (online version)', ''))
            title = normalize_title(row.get('Journal title', ''))

            if p_issn: doaj_map[p_issn] = apc_info
            if e_issn: doaj_map[e_issn] = apc_info
            if title: doaj_map[title] = apc_info

        print(f"Loaded DOAJ data for {len(doaj_map)} Keys (ISSN/Title).")
        return doaj_map
    except Exception as e:
        print(f"Error loading DOAJ data: {e}")
        return {}

def check_scimago(journal_name):
    """
    Attempts to check Scimago.
    Returns: 'Indexed', 'Not Indexed', 'Blocked', 'Error'
    """
    search_url = f"https://www.scimagojr.com/journalsearch.php?q={requests.utils.quote(journal_name)}"
    try:
        # time.sleep(1) # Be polite
        resp = requests.get(search_url, headers=HEADERS, timeout=10)

        if resp.status_code == 403 or "challenge" in resp.text.lower():
            return "Blocked"

        soup = BeautifulSoup(resp.content, 'html.parser')

        # If we are on search results page
        if "No results found" in soup.get_text():
             return "Not Indexed"

        # If there are results
        results = soup.find_all('div', class_='search_results')
        if results:
            return "Indexed (Scimago)"

        # If it redirected to a journal detail page immediately
        if "journalrank.php" in resp.url:
             return "Indexed (Scimago)"

        # Fallback
        return "Not Indexed"

    except Exception as e:
        return "Error"

def scrape_journal_page(url, journal_name):
    """
    Scrapes the journal page for Review Time and Scopus indexing status.
    """
    result = {
        'review_time': 'Not Available',
        'scopus_status': 'Not Verified',
        'url_visited': url
    }

    # 1. Check Scimago (Primary Verification)
    # Note: If Scimago blocks us, we will fallback to website check.
    # We won't call it for every thread if we detect blocking to avoid spamming,
    # but implementing a global flag in concurrent setup is tricky.
    # We'll just try it.

    scimago_status = check_scimago(journal_name)
    if scimago_status == "Indexed (Scimago)":
        result['scopus_status'] = scimago_status
    elif scimago_status == "Not Indexed":
        # If Scimago explicitly says not indexed (no results), we trust it?
        # Or we double check website? Scimago is authoritative.
        result['scopus_status'] = "Not Indexed (Scimago)"
    else:
        # Blocked or Error -> Fallback to website
        pass

    if not url or not isinstance(url, str) or not url.startswith('http'):
        return result

    try:
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()

        # --- Scopus Verification (Website Fallback) ---
        if result['scopus_status'] != "Indexed (Scimago)":
            if re.search(r'(Indexed|Abstracted).{0,100}Scopus', text, re.IGNORECASE) or "Scopus" in text:
                result['scopus_status'] = "Indexed (Verified on Website)"
            else:
                result['scopus_status'] = "Not Found on Website"

        # --- Review Time ---
        patterns = [
            r'Time to First Decision:?\s*([\d\.]+\s*(?:weeks?|days?))',
            r'Review Time:?\s*([\d\.]+\s*(?:weeks?|days?))',
            r'Submission to first decision:?\s*([\d\.]+\s*(?:weeks?|days?))',
            r'first decision:?\s*([\d\.]+\s*(?:weeks?|days?))',
             r'publishes.+in\s*(\d+\s*weeks?)',
             r'Average time to decision:?\s*([\d\.]+\s*(?:weeks?|days?))'
        ]

        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                result['review_time'] = match.group(1).strip()
                break

        # Springer Specific
        if "springer.com" in url:
             if result['review_time'] == 'Not Available':
                 match = re.search(r'(\d+)\s+days\s+to\s+first\s+decision', text, re.IGNORECASE)
                 if match:
                     result['review_time'] = f"{match.group(1)} days"

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        pass

    return result

def get_apc_info(journal_name, issn, mu_data_names, mu_data_issns, doaj_data):
    norm_name = normalize_title(journal_name)
    norm_issn = normalize_issn(issn)

    if norm_name in mu_data_names:
        return "Free (MU Directory)"
    if norm_issn and norm_issn in mu_data_issns:
        return "Free (MU Directory)"

    if norm_issn and norm_issn in doaj_data:
        return doaj_data[norm_issn]
    if norm_name in doaj_data:
        return doaj_data[norm_name]

    return "Not Available"

def process_journals(input_file, mu_names, mu_issns, doaj_data, limit=None):
    print(f"Processing journals from {input_file}...")
    try:
        df = pd.read_excel(input_file)
        if limit:
            df = df.head(limit)
            print(f"Limit applied: Processing first {limit} journals.")

        results = []
        total = len(df)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_row = {}
            for index, row in df.iterrows():
                url = row.get('Link', '')
                journal = str(row.get('Journal', ''))
                future = executor.submit(scrape_journal_page, url, journal)
                future_to_row[future] = row

            completed = 0
            for future in concurrent.futures.as_completed(future_to_row):
                row = future_to_row[future]
                journal_name = str(row.get('Journal', ''))
                try:
                    scrape_data = future.result()
                except Exception as e:
                    print(f"Thread Error for {journal_name}: {e}")
                    scrape_data = {
                        'review_time': 'Not Available',
                        'scopus_status': 'Not Verified',
                        'url_visited': row.get('Link', '')
                    }

                apc_info = get_apc_info(journal_name, "", mu_names, mu_issns, doaj_data)

                entry = {
                    'Journal Name': journal_name,
                    'Publisher URL': row.get('Link', ''),
                    'APC Status': apc_info,
                    'Review Time': scrape_data.get('review_time', 'Not Available'),
                    'Scopus Indexing': scrape_data.get('scopus_status', 'Not Verified')
                }
                results.append(entry)

                completed += 1
                if completed % 10 == 0:
                    print(f"Processed {completed}/{total}")

        return pd.DataFrame(results)

    except Exception as e:
        print(f"Error processing journals: {e}")
        return pd.DataFrame()

def save_and_plot(df):
    print("Saving data...")
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    print("Generating visualization...")
    try:
        plt.figure(figsize=(10, 6))
        if 'Scopus Indexing' in df.columns:
            counts = df['Scopus Indexing'].value_counts()
            sns.barplot(x=counts.index, y=counts.values)
            plt.title('Count of Journals by Scopus Indexing Status')
            plt.xlabel('Scopus Status')
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(PLOT_FILE)
            plt.close()
    except Exception as e:
        print(f"Error generating plot: {e}")

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals Processed: {len(df)}")
    print(f"Data saved to {OUTPUT_CSV} and {OUTPUT_XLSX}")
    if os.path.exists(PLOT_FILE):
        print(f"Visualization saved to {PLOT_FILE}")

    if 'Scopus Indexing' in df.columns:
        print("\nScopus Indexing Distribution:")
        print(df['Scopus Indexing'].value_counts())

    missing_review = len(df[df['Review Time'] == 'Not Available'])
    missing_apc = len(df[df['APC Status'] == 'Not Available'])
    print(f"\nMissing Review Times: {missing_review}")
    print(f"Missing APC Info: {missing_apc}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help="Limit number of journals to process")
    parser.add_argument('--dry-run', action='store_true', help="Run on first 5 journals")
    args = parser.parse_args()

    limit = 5 if args.dry_run else args.limit

    # Ensure inputs
    download_inputs()

    # Load Data
    mu_names, mu_issns = load_mu_data(MU_FILE)
    doaj_data = load_doaj_data(DOAJ_FILE)

    # Process
    df = process_journals(SOURCE_FILE, mu_names, mu_issns, doaj_data, limit=limit)

    # Save
    if not df.empty:
        save_and_plot(df)

if __name__ == "__main__":
    main()
