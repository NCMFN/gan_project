import concurrent.futures
import pandas as pd
from data_loader import DataLoader
from apc_manager import APCManager
from scraper_v4 import ScraperV4
import time

def process_journal(journal, apc_manager, scraper):
    title = journal['title']
    issn = journal.get('issn', None)
    apc_status = apc_manager.get_apc_status(title, issn)
    metrics = scraper.scrape_journal(title)

    result = {
        "Journal Name": title,
        "Publisher": journal.get('publisher', 'Not Available'),
        "APC": apc_status,
        "Review Time": metrics['Review Time'],
        "Quartile": metrics['Quartile'],
        "Scopus Status": metrics['Scopus Status']
    }
    return result

def main():
    loader = DataLoader("journals_list.xlsx", "mu_directory_2023.xls")
    loader.load_mu_directory()
    target_journals = loader.load_target_list()

    # Slice to 5
    subset = target_journals[:5]
    print(f"Testing with {len(subset)} journals.")

    apc_manager = APCManager(loader.apc_free_journals, loader.apc_free_issns)
    scraper = ScraperV4()

    results = []
    for j in subset:
        print(f"Processing {j['title']}...")
        res = process_journal(j, apc_manager, scraper)
        results.append(res)
        print(res)
        time.sleep(1)

    df = pd.DataFrame(results)
    print("\nDataFrame Head:")
    print(df)

if __name__ == "__main__":
    main()
