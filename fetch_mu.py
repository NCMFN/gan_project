import requests
import os

def download_mu():
    url = "https://www.mu.ac.zm/static/final-mu-directory-without-apc-2023.xls"
    filepath = "data/mu_directory_2023.xls"

    print(f"Downloading {url} to {filepath}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Error downloading MU directory: {e}")

if __name__ == "__main__":
    download_mu()
