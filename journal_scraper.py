import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import matplotlib.pyplot as plt
import seaborn as sns
from urllib.parse import quote
import os
import concurrent.futures

# Configuration
INPUT_FILE = "input_journals.xlsx"
APC_FILE = "mu_directory_2023.xls"
OUTPUT_CSV = "Djournals_data.csv"
OUTPUT_XLSX = "Djournals_data.xlsx"
CHART_FILE = "scopus_status_chart.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def load_mu_directory(filepath):
    """Loads the MU directory for APC cross-referencing."""
    print(f"Loading MU Directory from {filepath}...")
    try:
        # Memory says header at row 2 (index 2, which is 3rd row? Or 2 as in 0,1,2?)
        # Let's assume index 2 based on previous code.
        df = pd.read_excel(filepath, header=2)

        # Normalize
        # Assuming columns 'Journal' and 'ISSN' exist
        names = set()
        issns = set()

        if 'Journal' in df.columns:
            names = set(df['Journal'].astype(str).str.strip().str.lower())

        if 'ISSN' in df.columns:
            # Handle potential mixed types/NaNs
            raw_issns = df['ISSN'].apply(str).str.strip().str.replace('-', '')
            issns = set(raw_issns)

        print(f"Loaded {len(names)} names and {len(issns)} ISSNs from MU Directory.")
        return names, issns
    except Exception as e:
        print(f"Error loading MU Directory: {e}")
        return set(), set()

def search_doaj(query):
    """Searches DOAJ API for journal details."""
    # Try searching by ISSN first if query looks like ISSN, else Title
    # API: https://doaj.org/api/search/journals/{query}

    url = f"https://doaj.org/api/search/journals/{quote(query)}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                # Take the first result
                journal = results[0]['bibjson']

                # Extract ISSNs
                pissn = journal.get('pissn', '')
                eissn = journal.get('eissn', '')
                issns = []
                if pissn: issns.append(pissn)
                if eissn: issns.append(eissn)

                # Extract APC
                apc_info = journal.get('apc', {})
                has_apc = apc_info.get('has_apc', False)
                apc_url = apc_info.get('url', '')

                apc_status = "Unknown"
                if not has_apc:
                    apc_status = "No APC (DOAJ)"
                else:
                    # Try to get currency and amount
                    # Sometimes it's in a different structure
                    apc_status = f"Has APC (See {apc_url})"

                publisher = journal.get('publisher', {}).get('name', '')

                return {
                    'found': True,
                    'issns': issns,
                    'apc': apc_status,
                    'title': journal.get('title', ''),
                    'publisher': publisher
                }
    except Exception as e:
        # print(f"DOAJ Error for {query}: {e}")
        pass

    return {'found': False}

def get_journalsearches_data(journal_name):
    """Scrapes journalsearches.com for Quartile, Scopus Status, and Review Time."""
    # This is a fallback/proxy because Scimago and Publisher sites block requests.

    url = f"https://journalsearches.com/journal.php?title={quote(journal_name)}"

    data = {
        'Quartile': 'Not Available',
        'Scopus Status': 'Not Available',
        'Review Time': 'Not Available',
        'Publisher': 'Not Available'
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            text = soup.get_text()

            # Publisher
            # Pattern: Publisher: Name
            pub_match = re.search(r'Publisher:\s*(.*?)(?:\s+(?:P-|E-)?ISSN|Review|Language|Country|\n|$)', text)
            if pub_match:
                data['Publisher'] = pub_match.group(1).strip()

            # Scopus
            if "Scopus Coverage" in text or "Indexed in Scopus" in text or ("Indexed in" in text and "Scopus" in text):
                data['Scopus Status'] = "Indexed"
            else:
                 # Check negative? No, usually absence means no.
                 # But let's look for indicators.
                 if "Scopus" in text:
                     data['Scopus Status'] = "Likely Indexed"

            # Quartile
            # Look for Q1-Q4
            q_matches = re.findall(r'(Q[1-4])', text)
            if q_matches:
                data['Quartile'] = q_matches[0] # Take first

            # Review Time
            # Pattern: "publishes research articles in X weeks"
            m = re.search(r'publishes research articles in (\d+ weeks?)', text)
            if m:
                data['Review Time'] = m.group(1)
            else:
                # Fallback text search
                m2 = re.search(r'Review Time[:\s]+([\d\.]+\s*(?:weeks|days))', text, re.IGNORECASE)
                if m2:
                    data['Review Time'] = m2.group(1)

    except Exception as e:
        # print(f"JournalSearches Error {journal_name}: {e}")
        pass

    return data

def main():
    print("Starting Journal Scraper...")

    # 1. Load Data
    try:
        df_input = pd.read_excel(INPUT_FILE)
        print(f"Loaded {len(df_input)} journals from input.")
    except Exception as e:
        print(f"Failed to load input file: {e}")
        return

    mu_names, mu_issns = load_mu_directory(APC_FILE)

    results = []

    # 2. Process Journals
    total = len(df_input)
    print(f"Processing {total} journals with threading...")

    def process_journal(row_tuple):
        idx, row = row_tuple
        journal_name = str(row['Journal']).strip()
        pub_link = str(row['Link']) if pd.notna(row['Link']) else ""

        # Data container
        entry = {
            'Journal Name': journal_name,
            'Publisher': 'Not Available', # Initial info
            'Initial Link': pub_link,
            'ISSN': 'Not Available',
            'APC': 'Not Available',
            'Quartile': 'Not Available',
            'Scopus Status': 'Not Available',
            'Review Time': 'Not Available'
        }

        try:
            # A. DOAJ Search (Primary source for ISSN & APC)
            doaj_data = search_doaj(journal_name)

            found_issn = None
            if doaj_data['found']:
                if doaj_data['issns']:
                    entry['ISSN'] = ", ".join(doaj_data['issns'])
                    found_issn = doaj_data['issns'][0] # Use first for other searches

                entry['APC'] = doaj_data['apc']
                if doaj_data.get('publisher'):
                    entry['Publisher'] = doaj_data['publisher']

            # B. APC Check vs MU Directory
            is_in_mu = False
            if journal_name.lower() in mu_names:
                is_in_mu = True
            elif found_issn and found_issn.replace('-', '') in mu_issns:
                is_in_mu = True

            if is_in_mu:
                entry['APC'] = "Free (MU Directory)"
            elif entry['APC'] == 'Not Available' and doaj_data['found']:
                pass
            elif entry['APC'] == 'Not Available':
                entry['APC'] = "Unknown"

            # C. Scopus/Quartile/Review Time via JournalSearches (Proxy)
            js_data = get_journalsearches_data(journal_name)
            entry['Quartile'] = js_data['Quartile']
            entry['Scopus Status'] = js_data['Scopus Status']

            # If publisher still not available, use JS data
            if entry['Publisher'] == 'Not Available' and js_data.get('Publisher') != 'Not Available':
                entry['Publisher'] = js_data['Publisher']

            # For review time, if we found it in proxy, use it.
            if js_data['Review Time'] != 'Not Available':
                entry['Review Time'] = js_data['Review Time']

            # Try specific publisher link if proxy didn't find review time
            if entry['Review Time'] == 'Not Available' and pub_link:
                 # Simple scrape of the link provided
                 try:
                    if any(d in pub_link for d in ['sagepub', 'springer', 'elsevier', 'wiley']):
                        r = requests.get(pub_link, headers=HEADERS, timeout=5)
                        if r.status_code == 200:
                            txt = r.text.lower()
                            m = re.search(r'(?:review time|first decision)[:\s]+([\d\.]+\s*(?:days|weeks|months))', txt)
                            if m:
                                entry['Review Time'] = m.group(1)
                 except:
                     pass

        except Exception as e:
            print(f"Error processing {journal_name}: {e}")

        if (idx + 1) % 50 == 0:
            print(f"Completed {idx + 1}/{total}")

        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(process_journal, df_input.iterrows()))

    # 3. Create DataFrame
    df_out = pd.DataFrame(results)

    # 4. Export
    df_out.to_csv(OUTPUT_CSV, index=False)
    df_out.to_excel(OUTPUT_XLSX, index=False)
    print(f"Data exported to {OUTPUT_CSV} and {OUTPUT_XLSX}")

    # 5. Visualization
    plt.figure(figsize=(10, 6))
    if not df_out['Scopus Status'].dropna().empty:
        # Clean up status for charting
        # Maybe group by simplified status
        sns.countplot(y='Scopus Status', data=df_out, order=df_out['Scopus Status'].value_counts().index)
        plt.title('Distribution of Scopus Indexing Status')
        plt.xlabel('Count')
        plt.ylabel('Status')
        plt.tight_layout()
        plt.savefig(CHART_FILE)
        print(f"Chart saved to {CHART_FILE}")
    else:
        print("No Scopus data to plot.")

    # 6. Summary
    print("\nProcessing Complete.")
    print(f"Total Journals: {len(df_out)}")
    print(f"Scopus Info Found: {len(df_out[df_out['Scopus Status'] != 'Not Available'])}")
    print(f"APC Info Found: {len(df_out[df_out['APC'] != 'Unknown'])}")
    print(f"Review Time Found: {len(df_out[df_out['Review Time'] != 'Not Available'])}")

if __name__ == "__main__":
    main()
