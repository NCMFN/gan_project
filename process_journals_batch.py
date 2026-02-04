import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import concurrent.futures
import time
import os
import csv
import random

# Constants
DOAJ_FILE = "data/doaj_journals.json"
MU_FILE = "data/mu_directory_2023.xls"
OUTPUT_CSV = "Cjournals_data.csv"
BATCH_SIZE = 50

def load_data():
    with open(DOAJ_FILE, 'r') as f:
        doaj_data = json.load(f)
    try:
        mu_df = pd.read_excel(MU_FILE, header=2)
        mu_df['Journal Normalized'] = mu_df['Journal'].astype(str).str.lower().str.strip()
        mu_df['ISSN Normalized'] = mu_df['ISSN'].astype(str).str.replace('-', '').str.strip()
    except Exception as e:
        mu_df = pd.DataFrame()
    return doaj_data, mu_df

def scrape_js_details(journal_title):
    url = f"https://journalsearches.com/journal.php?title={quote(journal_title)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = {'scraped_review_time': None, 'scopus_status': None, 'js_url': url}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            if "Journal not found" not in text and "No results" not in text:
                if "Scopus" in text:
                    data['scopus_status'] = "Indexed"
                else:
                    data['scopus_status'] = "Not Indexed"

                import re
                match = re.search(r'publishes research articles in (\d+ weeks?)', text)
                if match:
                    data['scraped_review_time'] = match.group(1)
    except:
        pass
    return data

def process_single_journal(journal, mu_names, mu_issns):
    title_norm = journal['title'].lower().strip()
    issn_clean = (journal.get('pissn') or '').replace('-', '')
    eissn_clean = (journal.get('eissn') or '').replace('-', '')
    is_in_mu = (title_norm in mu_names) or (issn_clean and issn_clean in mu_issns) or (eissn_clean and eissn_clean in mu_issns)

    apc_status = "Free (DOAJ)"
    if is_in_mu:
        apc_status = "Free (DOAJ & MU Verified)"

    js_data = scrape_js_details(journal['title'])

    review_time = "Not Available"
    if js_data.get('scraped_review_time'):
        review_time = js_data['scraped_review_time'] + " (JS)"
    elif journal.get('publication_time_weeks'):
        review_time = str(journal['publication_time_weeks']) + " Weeks (DOAJ Pub Time)"

    scopus_status = js_data.get('scopus_status', "Unknown")

    return {
        'Journal Title': journal['title'],
        'Publisher': journal['publisher'],
        'ISSN': journal.get('pissn') or journal.get('eissn'),
        'APC Status': apc_status,
        'Review Time': review_time,
        'Scopus Indexing': scopus_status,
        'Quartile': "N/A (Scimago Blocked)",
        'Clarivate': "N/A (Rate Limited)",
        'Source URL': js_data.get('js_url')
    }

def main():
    doaj_data, mu_df = load_data()

    # Check processed
    processed_titles = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            df_existing = pd.read_csv(OUTPUT_CSV)
            processed_titles = set(df_existing['Journal Title'].values)
        except:
            pass
    else:
        # Initialize CSV
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Journal Title', 'Publisher', 'ISSN', 'APC Status', 'Review Time', 'Scopus Indexing', 'Quartile', 'Clarivate', 'Source URL'])
            writer.writeheader()

    mu_names = set(mu_df['Journal Normalized'].dropna().values) if not mu_df.empty else set()
    mu_issns = set(mu_df['ISSN Normalized'].dropna().values) if not mu_df.empty else set()

    journals_to_process = [j for j in doaj_data if j['title'] not in processed_titles]

    if not journals_to_process:
        print("All journals processed.")
        return

    # Take batch
    batch = journals_to_process[:BATCH_SIZE]
    print(f"Processing batch of {len(batch)} journals. {len(journals_to_process) - len(batch)} remaining.")

    results = []
    # Use fewer workers to avoid blocking
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_journal, j, mu_names, mu_issns): j for j in batch}

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Append to CSV
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Journal Title', 'Publisher', 'ISSN', 'APC Status', 'Review Time', 'Scopus Indexing', 'Quartile', 'Clarivate', 'Source URL'])
        writer.writerows(results)

    print(f"Batch completed. Saved to {OUTPUT_CSV}.")

if __name__ == "__main__":
    main()
