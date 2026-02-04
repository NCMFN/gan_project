import requests
import time
from urllib.parse import quote

class APCManager:
    def __init__(self, mu_titles, mu_issns):
        self.mu_titles = mu_titles
        self.mu_issns = mu_issns
        self.session = requests.Session()

    def check_mu_directory(self, title, issn=None):
        if title and title.lower().strip() in self.mu_titles:
            return True
        if issn and issn.replace('-', '').strip() in self.mu_issns:
            return True
        return False

    def get_doaj_apc(self, title, issn=None):
        query = ""
        if issn:
            query = f'issn:"{issn}"'
        elif title:
            query = f'title:"{title}"'

        if not query:
            return "Not Available"

        url = f"https://doaj.org/api/v4/search/journals/{quote(query)}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    res = data['results'][0]
                    bibjson = res.get('bibjson', {})
                    apc = bibjson.get('apc', {})

                    if apc:
                        if apc.get('has_apc'):
                            # Try to get max price
                            max_fees = apc.get('max', [])
                            if max_fees:
                                price = max_fees[0].get('price', '')
                                currency = max_fees[0].get('currency', '')
                                return f"{price} {currency} (DOAJ)"
                            else:
                                return "APC Charged (Amount Unknown) (DOAJ)"
                        else:
                            return "No APC (DOAJ)"
                    else:
                        # Sometimes apc object is missing but 'has_apc' isn't explicitly false
                        # But typically DOAJ records have this if they are indexed.
                        return "No APC Data (DOAJ)"
            return "Not Found in DOAJ"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_apc_status(self, title, issn=None):
        # 1. Check MU Directory (Free)
        if self.check_mu_directory(title, issn):
            return "Free (MU Directory)"

        # 2. Check DOAJ
        time.sleep(0.5)
        doaj_res = self.get_doaj_apc(title, issn)
        if "Not Found" not in doaj_res and "Error" not in doaj_res:
            return doaj_res

        return "Not Available"

if __name__ == "__main__":
    mu_titles = {"agriculture and natutal resources", "sample free journal"}
    mu_issns = {"12345678"}

    manager = APCManager(mu_titles, mu_issns)

    print(f"Test 1 (MU): {manager.get_apc_status('Sample Free Journal')}")
    print(f"Test 2 (DOAJ APC): {manager.get_apc_status('PLOS ONE')}")
    print(f"Test 3 (DOAJ No Found): {manager.get_apc_status('Random Journal XYZ')}")
