import pandas as pd
import re

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    return text.strip().lower()

def normalize_issn(text):
    if not isinstance(text, str):
        return ""
    # Remove dashes and whitespace
    return re.sub(r'[\-\s]', '', text)

class DataLoader:
    def __init__(self, target_list_path, mu_directory_path):
        self.target_list_path = target_list_path
        self.mu_directory_path = mu_directory_path
        self.apc_free_journals = set()
        self.apc_free_issns = set()

    def load_mu_directory(self):
        print(f"Loading MU Directory from {self.mu_directory_path}...")
        try:
            # Header is at row index 2 (0-based)
            df = pd.read_excel(self.mu_directory_path, header=2)

            # Normalize and store
            for _, row in df.iterrows():
                if pd.notna(row['Journal']):
                    self.apc_free_journals.add(normalize_text(str(row['Journal'])))

                if pd.notna(row['ISSN']):
                    # Handle multiple ISSNs if present (comma separated)
                    issns = str(row['ISSN']).split(',')
                    for issn in issns:
                        self.apc_free_issns.add(normalize_issn(issn))

            print(f"Loaded {len(self.apc_free_journals)} titles and {len(self.apc_free_issns)} ISSNs from MU Directory.")
        except Exception as e:
            print(f"Error loading MU Directory: {e}")
            raise

    def load_target_list(self):
        print(f"Loading Target List from {self.target_list_path}...")
        try:
            df = pd.read_excel(self.target_list_path)
            # Inspect columns if needed, assuming 'Journal Title' exists based on previous inspection

            journals = []
            for _, row in df.iterrows():
                # Extract relevant initial info
                journal = {
                    'title': str(row.get('Journal Title', '')).strip(),
                    'publisher': str(row.get('Publisher', '')).strip(),
                    # Try to get ISSN if available in target list (might make matching easier)
                    # Based on inspection, there wasn't an explicit ISSN column in the first few cols,
                    # but let's check row keys if needed. For now just title.
                }
                if journal['title'] and journal['title'].lower() != 'nan':
                    journals.append(journal)

            print(f"Loaded {len(journals)} target journals.")
            return journals
        except Exception as e:
            print(f"Error loading Target List: {e}")
            raise

if __name__ == "__main__":
    # Test execution
    loader = DataLoader("journals_list.xlsx", "mu_directory_2023.xls")
    loader.load_mu_directory()
    journals = loader.load_target_list()
    print(f"First 3 journals: {journals[:3]}")
