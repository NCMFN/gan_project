import requests
import pandas as pd
from bs4 import BeautifulSoup
import concurrent.futures
import time
import re
import urllib.parse
import os
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Constants
DOAJ_API_BASE = "https://doaj.org/api/search/journals/"
MU_DIRECTORY_URL = "https://www.mu.ac.zm/static/final-mu-directory-without-apc-2023.xls"
METADATA_BASE_URL = "https://journalsearches.com/journal.php"
OUTPUT_CSV = "Cjournals_data.csv"
OUTPUT_XLSX = "Cjournals_data.xlsx"
CHART_FILE = "scopus_status_chart.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=200, pool_maxsize=200)
SESSION.mount('http://', adapter)
SESSION.mount('https://', adapter)
SESSION.headers.update(HEADERS)

def fetch_doaj_journals():
    """
    Fetches all journals from DOAJ matching the APC-free criteria.
    Uses created_date sorting and range queries to paginate.
    """
    print("Fetching journals from DOAJ API...")
    journals = []
    base_query = "bibjson.apc.has_apc:false AND bibjson.other_charges.has_other_charges:false"

    page_size = 100
    last_date = None
    total_fetched = 0

    while True:
        query = base_query
        if last_date:
            query += f" AND created_date:>{last_date}"

        encoded_query = urllib.parse.quote(query)
        url = f"{DOAJ_API_BASE}{encoded_query}?pageSize={page_size}&sort=created_date"

        try:
            resp = SESSION.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"Error fetching DOAJ data: {resp.status_code}")
                break

            data = resp.json()
            results = data.get('results', [])

            if not results:
                break

            for res in results:
                bib = res.get('bibjson', {})
                eissn = bib.get('eissn')
                pissn = bib.get('pissn')
                links = bib.get('link', [])
                url_link = next((l.get('url') for l in links if l.get('type') == 'homepage'), None)
                publisher = bib.get('publisher', {}).get('name', 'Not Available')

                journal_entry = {
                    'Journal Name': bib.get('title', 'Not Available'),
                    'Publisher': publisher,
                    'E-ISSN': eissn if eissn else 'Not Available',
                    'P-ISSN': pissn if pissn else 'Not Available',
                    'Source URL': url_link if url_link else 'Not Available',
                    'Created Date': res.get('created_date')
                }
                journals.append(journal_entry)

            total_fetched += len(results)
            if total_fetched % 1000 == 0:
                print(f"Fetched {total_fetched} journals...")

            new_last_date = results[-1].get('created_date')
            if new_last_date == last_date:
                print("Warning: Date didn't advance. Breaking to avoid infinite loop.")
                break
            last_date = new_last_date

            if len(results) < page_size:
                break

        except Exception as e:
            print(f"Exception in DOAJ fetch: {e}")
            break

    print(f"Total DOAJ Journals fetched: {len(journals)}")
    return pd.DataFrame(journals)

def load_mu_directory():
    """
    Downloads and loads the MU directory to identifying verified APC-free journals.
    """
    print("Processing MU Directory...")
    local_filename = "mu_directory_temp.xls"
    try:
        # Use a fresh request or session for MU with verify=False
        resp = requests.get(MU_DIRECTORY_URL, verify=False, timeout=30)
        with open(local_filename, 'wb') as f:
            f.write(resp.content)

        df = pd.read_excel(local_filename, header=2)

        if os.path.exists(local_filename):
            os.remove(local_filename)

        # Use .apply(str) to force string conversion even for NaNs/floats
        mu_journals = set(df['Journal'].apply(str).str.strip().str.lower())

        mu_issns = set()
        # Drop NaNs first to be cleaner, then convert to string
        issn_series = df['ISSN'].dropna().apply(str)

        for issn in issn_series:
            clean = issn.strip().replace('-', '')
            if len(clean) >= 7:
                mu_issns.add(clean)

        print(f"Loaded {len(mu_journals)} journals and {len(mu_issns)} ISSNs from MU Directory.")
        return mu_journals, mu_issns

    except Exception as e:
        print(f"Error loading MU Directory: {e}")
        # Return empty sets so we can continue (but APC check will be just 'DOAJ Listed')
        return set(), set()

def scrape_metadata_single(journal_row):
    """
    Scrapes metadata for a single journal from journalsearches.com.
    """
    title = journal_row['Journal Name']
    # Use quote_plus for spaces -> + (which is common in URLs) or quote (%20)
    # journalsearches.com/journal.php?title=... usually expects %20
    url = f"{METADATA_BASE_URL}?title={urllib.parse.quote(title)}"

    meta = {
        'Review Time': 'Not Available',
        'Quartile': 'Not Available',
        'Scopus Status': 'Not Available'
    }

    try:
        resp = SESSION.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            text = soup.get_text()

            # Review Time
            # Pattern: "publishes research articles in X weeks"
            time_match = re.search(r'(?:Review Time|publishes research articles in)\s*[:]?\s*(\d+\s*\w+)', text, re.IGNORECASE)
            if time_match:
                meta['Review Time'] = time_match.group(1).strip()

            # Quartile
            q_match = re.search(r'Quartile\s*[:]?\s*(Q[1-4])', text, re.IGNORECASE)
            if q_match:
                meta['Quartile'] = q_match.group(1)

            # Scopus Status
            if "Indexed in" in text and "Scopus" in text:
                meta['Scopus Status'] = "Indexed"
            elif "Scopus Coverage" in text:
                meta['Scopus Status'] = "Indexed"
            else:
                meta['Scopus Status'] = "Not Indexed"

        else:
            pass

    except Exception:
        pass

    return meta

def process_journal_record(journal):
    meta = scrape_metadata_single(journal)
    journal.update(meta)
    return journal

def main():
    start_time = time.time()

    # 1. Fetch from DOAJ
    df = fetch_doaj_journals()
    if df.empty:
        print("No journals found from DOAJ. Exiting.")
        return

    # 2. Load MU Directory for APC verification
    mu_names, mu_issns = load_mu_directory()

    # 3. Enrich with Metadata (Scraping)
    enriched_records = []
    records = df.to_dict('records')

    print(f"Starting concurrent scraping for {len(records)} journals...")
    # Using 50 workers to be polite to the server while maintaining reasonable speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(process_journal_record, r) for r in records]

        completed = 0
        total = len(records)
        # Use simple progress updates
        for future in concurrent.futures.as_completed(futures):
            enriched_records.append(future.result())
            completed += 1
            if completed % 100 == 0:
                 print(f"Scraped {completed}/{total}...", end='\r')

    print("\nScraping done.")

    # 4. Consolidate and Check APC
    final_df = pd.DataFrame(enriched_records)

    def check_apc(row):
        title = str(row.get('Journal Name', '')).lower().strip()
        eissn = str(row.get('E-ISSN', '')).strip().replace('-', '')
        pissn = str(row.get('P-ISSN', '')).strip().replace('-', '')

        is_mu_verified = False
        if title in mu_names:
            is_mu_verified = True
        elif eissn and eissn in mu_issns:
            is_mu_verified = True
        elif pissn and pissn in mu_issns:
            is_mu_verified = True

        if is_mu_verified:
            return "Free (Verified via MU Directory)"
        else:
            return "Free (DOAJ Listed)"

    final_df['APC Status'] = final_df.apply(check_apc, axis=1)

    cols = ['Journal Name', 'Publisher', 'E-ISSN', 'P-ISSN', 'Review Time', 'Quartile', 'Scopus Status', 'APC Status', 'Source URL']
    for col in cols:
        if col not in final_df.columns:
            final_df[col] = 'Not Available'

    final_df = final_df[cols].fillna('Not Available')

    # 5. Export
    print(f"Exporting to {OUTPUT_CSV} and {OUTPUT_XLSX}...")
    final_df.to_csv(OUTPUT_CSV, index=False)
    final_df.to_excel(OUTPUT_XLSX, index=False)

    # 6. Visualization
    print("Generating Chart...")
    plt.figure(figsize=(10, 6))
    if not final_df.empty:
        counts = final_df['Scopus Status'].value_counts()
        sns.barplot(x=counts.index, y=counts.values, palette='viridis')
        plt.title('Distribution of Scopus Indexing Status')
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.savefig(CHART_FILE)
        plt.close()

    # 7. Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals Processed: {len(final_df)}")
    print(f"Successfully processed {len(final_df)} journals.")
    print(f"Metadata completeness:")
    print(f" - Review Time Found: {len(final_df[final_df['Review Time'] != 'Not Available'])}")
    print(f" - Quartile Found: {len(final_df[final_df['Quartile'] != 'Not Available'])}")
    if 'Scopus Status' in final_df.columns:
        print(f" - Scopus Status: {final_df['Scopus Status'].value_counts().to_dict()}")
    print(f"Output files: {OUTPUT_CSV}, {OUTPUT_XLSX}, {CHART_FILE}")
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    print("="*50)

if __name__ == "__main__":
    main()
