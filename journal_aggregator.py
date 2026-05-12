import pandas as pd
import requests
import time
import random
import os
import concurrent.futures
from urllib.parse import quote
import matplotlib.pyplot as plt
import seaborn as sns
import re
from io import StringIO

# Constants
# Note: DOAJ API v1 is deprecated/404. Using the current search endpoint which accepts Lucene queries in the path.
DOAJ_API_URL = "https://doaj.org/api/search/journals/"
QUERY = "bibjson.apc.has_apc:false AND bibjson.other_charges.has_other_charges:false"
APC_FILES = ["final-mu-directory-without-apc-2023.xls", "mu_directory.xls"]
SCIMAGO_URL = "https://www.scimagojr.com/journalrank.php?out=xls"
SCIMAGO_FILE = "scimagojr.csv" # Local fallback
OUTPUT_CSV = "Ejournals_data.csv"
OUTPUT_XLSX = "Ejournals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"
LIMIT = None # Set to None for full run (~14k journals), or int (e.g., 50) for testing
WORKERS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_doaj_journals(limit=None):
    print("Fetching journals from DOAJ API...")
    encoded_query = quote(QUERY)
    url = f"{DOAJ_API_URL}{encoded_query}"

    page = 1
    page_size = 100
    journals = []

    while True:
        try:
            params = {'page': page, 'pageSize': page_size}
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            results = data.get('results', [])
            if not results:
                break

            for item in results:
                bib = item.get('bibjson', {})
                title = bib.get('title', 'Unknown')
                publisher = bib.get('publisher', {}).get('name', 'Unknown')
                eissn = bib.get('eissn')
                pissn = bib.get('pissn')
                link = bib.get('ref', {}).get('journal')

                # Prioritize E-ISSN, then P-ISSN
                issn = eissn if eissn else pissn

                journals.append({
                    'Journal Name': title,
                    'Publisher': publisher,
                    'ISSN': issn,
                    'URL': link,
                    'APC_Status': 'No APC (DOAJ)',
                    'Source': 'DOAJ'
                })

                if limit and len(journals) >= limit:
                    break

            print(f"Fetched {len(journals)} journals...")
            if limit and len(journals) >= limit:
                break

            total = data.get('total', 0)
            if len(journals) >= total:
                break

            page += 1
            time.sleep(1) # Be polite to API

        except Exception as e:
            print(f"Error fetching DOAJ data: {e}")
            break

    return pd.DataFrame(journals)

def load_apc_data(filepath_arg=None):
    target_file = None
    # If a specific file is passed and exists, use it
    if filepath_arg and os.path.exists(filepath_arg):
        target_file = filepath_arg
    else:
        # Otherwise check the list
        for f in APC_FILES:
            if os.path.exists(f):
                target_file = f
                break

    if not target_file:
        print(f"APC file not found. Checked: {APC_FILES}")
        return pd.DataFrame()

    print(f"Loading APC data from {target_file}...")
    try:
        # Header at row 2 based on previous inspection
        df = pd.read_excel(target_file, header=2)
        # Clean ISSN
        if 'ISSN' in df.columns:
            df['ISSN'] = df['ISSN'].astype(str).str.strip().str.replace('-', '')
        return df
    except Exception as e:
        print(f"Error loading APC data: {e}")
        return pd.DataFrame()

def load_scimago_data():
    print("Attempting to load Scimago data...")
    df = None

    # Try download
    try:
        resp = requests.get(SCIMAGO_URL, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            csv_data = StringIO(resp.text)
            df = pd.read_csv(csv_data, sep=';', on_bad_lines='skip')
            print("Downloaded Scimago data successfully.")
        else:
            print(f"Could not download Scimago data (Status {resp.status_code}).")
    except Exception as e:
        print(f"Error downloading Scimago data: {e}")

    # Fallback to local
    if df is None:
        if os.path.exists(SCIMAGO_FILE):
            try:
                df = pd.read_csv(SCIMAGO_FILE, sep=';', on_bad_lines='skip')
                print(f"Loaded Scimago data from local file {SCIMAGO_FILE}.")
            except:
                try:
                    df = pd.read_csv(SCIMAGO_FILE, on_bad_lines='skip')
                    print(f"Loaded Scimago data from local file {SCIMAGO_FILE} (comma sep).")
                except Exception as e:
                    print(f"Error loading local Scimago file: {e}")

    return df

def get_review_time(url):
    if not url:
        return "N/A"

    try:
        # Random sleep
        time.sleep(random.uniform(2, 5))

        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return "N/A"

        text = resp.text.lower()

        keywords = ["average review time", "time to first decision", "submission to acceptance", "review process", "weeks"]

        patterns = [
            r"(?:average review time|time to first decision|submission to acceptance)[^0-9]*(\d+\s+(?:days|weeks|months))",
            r"(\d+\s+(?:days|weeks|months))\s+(?:avg|average)?\s*(?:review time|to first decision)"
        ]

        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)

        # Fallback
        for k in keywords:
            if k in text:
                return "Mentioned (Parse Failed)"

        return "N/A"

    except Exception as e:
        return "N/A"

def check_clarivate(issn, title):
    # Lightweight check. Since Clarivate MJL is heavily protected and we don't have an API key,
    # and direct scraping of the SPA is not possible with requests,
    # we return a placeholder. In a production environment with API access, we would query the API here.
    return "Unknown (Protected)"

def process_review_times(df):
    if df.empty:
        return df

    print(f"Scraping review times for {len(df)} journals using {WORKERS} workers...")
    urls = df['URL'].tolist()
    results = ["Unknown"] * len(df)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_to_idx = {executor.submit(get_review_time, url): i for i, url in enumerate(urls)}

        completed = 0
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                data = future.result()
            except Exception:
                data = "Error"
            results[idx] = data

            completed += 1
            if completed % 10 == 0:
                print(f"Scraped {completed}/{len(df)}")

    df['Review_Time'] = results
    return df

def main():
    # 1. Extraction
    df = fetch_doaj_journals(limit=LIMIT)
    if df.empty:
        print("No journals found from DOAJ.")
        return

    # Normalize ISSN in main DF
    df['ISSN_Clean'] = df['ISSN'].astype(str).str.strip().str.replace('-', '')

    # 2. Enrichment (APC)
    apc_df = load_apc_data()
    df['In_APC_Directory'] = False

    if not apc_df.empty:
        # Create a set of ISSNs from APC file (assuming 'ISSN' column exists and is cleaned in load function)
        # Note: load_apc_data already replaces '-'
        apc_issns = set(apc_df['ISSN'].tolist())

        # Also create a set of titles for fallback?
        # The prompt says: "fallback to clean Title match if ISSN fails".
        # Let's clean titles: lower, strip
        apc_titles = set(apc_df['Journal'].astype(str).str.lower().str.strip().tolist()) if 'Journal' in apc_df.columns else set()

        # Function to check
        def check_apc(row):
            issn = row['ISSN_Clean']
            title = str(row['Journal Name']).lower().strip()
            if issn in apc_issns:
                return True
            if title in apc_titles:
                return True
            return False

        df['In_APC_Directory'] = df.apply(check_apc, axis=1)
        print(f"Verified {df['In_APC_Directory'].sum()} journals in APC directory.")

    # 3. Enrichment (Scimago)
    scimago_df = load_scimago_data()
    df['Scopus_Indexed'] = False
    df['Quartile'] = "Unknown"
    df['H_Index'] = "Unknown"

    if scimago_df is not None:
        scimago_map = {}
        for idx, row in scimago_df.iterrows():
            row_keys = row.keys()
            issn_col = next((k for k in row_keys if 'issn' in k.lower()), None)
            quartile_col = next((k for k in row_keys if 'quartile' in k.lower() or 'sjr' in k.lower()), None)
            h_col = next((k for k in row_keys if 'h index' in k.lower()), None)

            if issn_col:
                issns = str(row[issn_col]).replace('issn', '').replace('ISSN', '')
                parts = re.split(r'[,\s]+', issns)
                q_val = row.get(quartile_col, 'Unknown') if quartile_col else 'Unknown'
                h_val = row.get(h_col, 'Unknown') if h_col else 'Unknown'

                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        scimago_map[clean_p] = {
                            'Quartile': q_val,
                            'H_Index': h_val
                        }

        def get_scimago_info(issn):
            if issn in scimago_map:
                return scimago_map[issn]
            return None

        scimago_data = df['ISSN_Clean'].apply(get_scimago_info)

        for i, val in enumerate(scimago_data):
            if val:
                df.at[i, 'Scopus_Indexed'] = True
                df.at[i, 'Quartile'] = val['Quartile']
                df.at[i, 'H_Index'] = val['H_Index']

        print(f"Matched {df['Scopus_Indexed'].sum()} journals with Scimago data.")
    else:
        print("Skipping Scimago enrichment (No data).")

    # 4. Clarivate Verification (Only if Scopus missing)
    # Perform lightweight check for mjl.clarivate.com only if Scopus data is missing
    # We will just add the column for now as we don't have API access.
    # If we could, we would loop over rows where Scopus_Indexed is False.
    df['Clarivate_Check'] = "N/A"

    # Example logic if we had the check:
    # missing_scopus = df[~df['Scopus_Indexed']]
    # for idx in missing_scopus.index:
    #     df.at[idx, 'Clarivate_Check'] = check_clarivate(df.at[idx, 'ISSN'], df.at[idx, 'Journal Name'])

    # 5. Web Scraping
    df = process_review_times(df)

    # 6. Output
    final_cols = ['Journal Name', 'Publisher', 'ISSN', 'APC_Status', 'Review_Time', 'Quartile', 'Scopus_Indexed', 'H_Index', 'In_APC_Directory', 'Clarivate_Check', 'URL']

    if 'Journal Name' not in df.columns and 'title' in df.columns:
        df.rename(columns={'title': 'Journal Name'}, inplace=True)

    for col in final_cols:
        if col not in df.columns:
            df[col] = "Unknown"

    output_df = df[final_cols]

    output_df.to_csv(OUTPUT_CSV, index=False)
    output_df.to_excel(OUTPUT_XLSX, index=False)

    try:
        plt.figure(figsize=(8, 6))
        plot_data = output_df['Scopus_Indexed'].astype(str)
        sns.countplot(x=plot_data)
        plt.title('Scopus Indexing Status')
        plt.savefig(PLOT_FILE)
    except Exception as e:
        print(f"Error creating plot: {e}")

    print(f"\nSuccessfully processed {len(output_df)} journals.")
    scopus_rate = (output_df['Scopus_Indexed'].sum() / len(output_df)) * 100
    print(f"Scopus Indexing Rate: {scopus_rate:.2f}%.")

if __name__ == "__main__":
    main()
