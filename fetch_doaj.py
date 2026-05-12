import requests
import json
from urllib.parse import quote
import time
import os

def fetch_doaj_deep():
    base_query = "bibjson.apc.has_apc:false AND bibjson.other_charges.has_other_charges:false"

    all_journals = []
    current_query = base_query
    sort_param = "created_date:asc"

    # We loop until no new results
    while True:
        encoded_query = quote(current_query)
        url = f"https://doaj.org/api/search/journals/{encoded_query}"

        batch_journals = []
        stop_batch = False

        print(f"Starting batch with query: {current_query}")

        # We can fetch pages 1 to 10 (1000 items max per query)
        for page in range(1, 11):
            params = {
                "page": page,
                "pageSize": 100,
                "sort": sort_param
            }

            try:
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    print(f"Error: {resp.status_code} - {resp.text[:100]}")
                    stop_batch = True
                    break

                data = resp.json()
                results = data.get('results', [])

                if not results:
                    stop_batch = True
                    break

                for item in results:
                    bib = item.get('bibjson', {})
                    created_date = item.get('created_date')
                    journal = {
                        'title': bib.get('title', 'Unknown Title'),
                        'publisher': bib.get('publisher', {}).get('name', 'Unknown Publisher'),
                        'pissn': bib.get('pissn'),
                        'eissn': bib.get('eissn'),
                        'publication_time_weeks': bib.get('publication_time_weeks'),
                        'apc_url': bib.get('apc', {}).get('url'),
                        'subjects': bib.get('subject', []),
                        'keywords': bib.get('keywords', []),
                        'language': bib.get('language', []),
                        'country': bib.get('publisher', {}).get('country'),
                        'created_date': created_date,
                        'id': item.get('id')
                    }
                    batch_journals.append(journal)

            except Exception as e:
                print(e)
                stop_batch = True
                break

            # If we got less than 100, we are at end of results
            if len(results) < 100:
                stop_batch = True
                break

        # Add to main list with deduplication
        new_items_count = 0
        existing_ids = set(j['id'] for j in all_journals if j.get('id'))

        for j in batch_journals:
            if j.get('id') and j['id'] not in existing_ids:
                all_journals.append(j)
                existing_ids.add(j['id'])
                new_items_count += 1
            elif not j.get('id'):
                # Fallback check by title if ID missing (unlikely)
                if j['title'] not in [x['title'] for x in all_journals]:
                     all_journals.append(j)
                     new_items_count += 1

        print(f"Batch finished. Added {new_items_count} new journals. Total: {len(all_journals)}")

        if not batch_journals or len(batch_journals) < 100:
             print("Reached end of results.")
             break

        # Prepare next query
        last_date = batch_journals[-1]['created_date']

        # Use simple > syntax
        next_date_query = f"created_date:>{last_date}"
        current_query = f"{base_query} AND {next_date_query}"

        # Limit safety
        if len(all_journals) > 15000:
            break

    output_file = "data/doaj_journals.json"
    with open(output_file, 'w') as f:
        json.dump(all_journals, f, indent=2)

    print(f"Saved {len(all_journals)} journals to {output_file}")

if __name__ == "__main__":
    fetch_doaj_deep()
