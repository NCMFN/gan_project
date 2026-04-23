import pandas as pd

def inspect_file(filepath):
    print(f"Inspecting {filepath}...")
    try:
        if filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            # xls might need xlrd or openpyxl depending on version, sometimes 'header' varies
            df = pd.read_excel(filepath)

        print("Columns:", df.columns.tolist())
        print("First 3 rows:")
        print(df.head(3))
        return df
    except Exception as e:
        print(f"Error: {e}")

print("--- Source Journals ---")
inspect_file('source_journals.xlsx')

print("\n--- MU Directory ---")
inspect_file('mu_directory_new.xls')
