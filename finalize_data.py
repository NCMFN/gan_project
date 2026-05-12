import json
import pandas as pd
import requests
import csv
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Constants
DOAJ_FILE = "data/doaj_journals.json"
MU_FILE = "data/mu_directory_2023.xls"
OUTPUT_CSV = "Cjournals_data.csv"
OUTPUT_XLSX = "Cjournals_data.xlsx"
CHART_FILE = "scopus_status_chart.png"

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

def process_single_journal_fast(journal, mu_names, mu_issns):
    title_norm = journal['title'].lower().strip()
    issn_clean = (journal.get('pissn') or '').replace('-', '')
    eissn_clean = (journal.get('eissn') or '').replace('-', '')
    is_in_mu = (title_norm in mu_names) or (issn_clean and issn_clean in mu_issns) or (eissn_clean and eissn_clean in mu_issns)

    apc_status = "Free (DOAJ)"
    if is_in_mu:
        apc_status = "Free (DOAJ & MU Verified)"

    # Fast processing: Skip scraping
    review_time = "Not Available"
    if journal.get('publication_time_weeks'):
        review_time = str(journal['publication_time_weeks']) + " Weeks (DOAJ Pub Time)"

    scopus_status = "Unknown (Scraping Skipped)"

    return {
        'Journal Title': journal['title'],
        'Publisher': journal['publisher'],
        'ISSN': journal.get('pissn') or journal.get('eissn'),
        'APC Status': apc_status,
        'Review Time': review_time,
        'Scopus Indexing': scopus_status,
        'Quartile': "N/A",
        'Clarivate': "N/A",
        'Source URL': "https://journalsearches.com"
    }

def main():
    doaj_data, mu_df = load_data()

    # Check processed
    processed_titles = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            df_existing = pd.read_csv(OUTPUT_CSV)
            processed_titles = set(df_existing['Journal Title'].values)
            print(f"Existing processed journals: {len(processed_titles)}")
        except:
            pass

    mu_names = set(mu_df['Journal Normalized'].dropna().values) if not mu_df.empty else set()
    mu_issns = set(mu_df['ISSN Normalized'].dropna().values) if not mu_df.empty else set()

    journals_to_process = [j for j in doaj_data if j['title'] not in processed_titles]
    print(f"Filling remaining {len(journals_to_process)} journals with fallback data...")

    fallback_results = []
    for j in journals_to_process:
        fallback_results.append(process_single_journal_fast(j, mu_names, mu_issns))

    # Append
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Journal Title', 'Publisher', 'ISSN', 'APC Status', 'Review Time', 'Scopus Indexing', 'Quartile', 'Clarivate', 'Source URL'])
        if os.stat(OUTPUT_CSV).st_size == 0:
             writer.writeheader()
        writer.writerows(fallback_results)

    # Finalize
    print("Generating final XLSX and Chart...")
    df = pd.read_csv(OUTPUT_CSV)
    df.to_excel(OUTPUT_XLSX, index=False)

    plt.figure(figsize=(10, 6))
    if 'Scopus Indexing' in df.columns:
        counts = df['Scopus Indexing'].value_counts()
        sns.barplot(x=counts.index, y=counts.values)
        plt.title('Count of Journals by Scopus Indexing Status')
        plt.tight_layout()
        plt.savefig(CHART_FILE)
        plt.close()

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals in CSV: {len(df)}")
    print(f"Scraped (Indexed/Not Indexed): {len(df[df['Scopus Indexing'].str.contains('Indexed', na=False)])}")
    print(f"Unknown (Skipped): {len(df[df['Scopus Indexing'].str.contains('Unknown', na=False)])}")

if __name__ == "__main__":
    main()
