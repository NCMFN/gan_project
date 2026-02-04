import concurrent.futures
import pandas as pd
import time
import os
import matplotlib.pyplot as plt
import seaborn as sns
from data_loader import DataLoader
from apc_manager import APCManager
from scraper_v4 import ScraperV4

# Config
JOURNAL_LIST = "journals_list.xlsx"
MU_DIRECTORY = "mu_directory_2023.xls"
OUTPUT_CSV = "Bjournals_data.csv"
OUTPUT_XLSX = "Bjournals_data.xlsx"
PLOT_FILE = "scopus_status_chart.png"
MAX_WORKERS = 5

def process_journal(journal, apc_manager, scraper):
    title = journal['title']
    # Attempt to get ISSN if we had it, but currently we rely on title
    issn = journal.get('issn', None)

    # Get APC
    apc_status = apc_manager.get_apc_status(title, issn)

    # Get Metrics (Quartile, Scopus, Review Time)
    metrics = scraper.scrape_journal(title)

    # Combine
    result = {
        "Journal Name": title,
        "Publisher": journal.get('publisher', 'Not Available'),
        "APC": apc_status,
        "Review Time": metrics['Review Time'],
        "Quartile": metrics['Quartile'],
        "Scopus Status": metrics['Scopus Status'],
        "Source URL": metrics['Source URL']
    }
    return result

def main():
    print("Starting Journal Scraper Pipeline...")

    # 1. Load Data
    loader = DataLoader(JOURNAL_LIST, MU_DIRECTORY)
    loader.load_mu_directory()
    target_journals = loader.load_target_list()

    if not target_journals:
        print("No journals to process.")
        return

    # 2. Initialize Managers
    apc_manager = APCManager(loader.apc_free_journals, loader.apc_free_issns)
    scraper = ScraperV4()

    # 3. Process Journals
    results = []
    print(f"Processing {len(target_journals)} journals with {MAX_WORKERS} workers...")

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_journal = {executor.submit(process_journal, j, apc_manager, scraper): j for j in target_journals}

        for i, future in enumerate(concurrent.futures.as_completed(future_to_journal)):
            journal = future_to_journal[future]
            try:
                data = future.result()
                results.append(data)
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(target_journals)} journals...")
            except Exception as e:
                print(f"Error processing {journal['title']}: {e}")
                # Append placeholder result to maintain count if needed, or just skip
                results.append({
                    "Journal Name": journal['title'],
                    "Publisher": journal.get('publisher', 'Not Available'),
                    "APC": "Error",
                    "Review Time": "Error",
                    "Quartile": "Error",
                    "Scopus Status": "Error",
                    "Source URL": "Error"
                })

    elapsed = time.time() - start_time
    print(f"Processing complete in {elapsed:.2f} seconds.")

    # 4. Create DataFrame
    df = pd.DataFrame(results)

    # 5. Export
    print(f"Exporting to {OUTPUT_CSV} and {OUTPUT_XLSX}...")
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    # 6. Visualization
    print("Generating visualization...")
    if 'Scopus Status' in df.columns:
        plt.figure(figsize=(10, 6))
        # Filter out errors if any
        plot_df = df[df['Scopus Status'] != 'Error']
        counts = plot_df['Scopus Status'].value_counts()
        sns.barplot(x=counts.index, y=counts.values)
        plt.title('Count of Journals by Scopus Indexing Status')
        plt.xlabel('Scopus Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(PLOT_FILE)
        print(f"Chart saved to {PLOT_FILE}")

    # 7. Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Journals: {len(target_journals)}")
    print(f"Successfully Processed: {len(df)}")

    if 'Review Time' in df.columns:
        missing_rt = len(df[df['Review Time'] == 'Not Available'])
        print(f"Journals with missing Review Time: {missing_rt}")

    if 'Scopus Status' in df.columns:
        print("\nScopus Indexing Insights:")
        print(df['Scopus Status'].value_counts())

    print("\nDone.")

if __name__ == "__main__":
    main()
