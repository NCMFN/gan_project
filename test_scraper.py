
import unittest
from unittest.mock import patch, MagicMock
import journal_scraper

class TestJournalScraper(unittest.TestCase):
    def setUp(self):
        self.sample_html = """
        <html>
        <body>
            <h1>Some Header</h1>
            <p>
                Journal Title: International Journal of Testing
                Publisher: Test Press
                ISSN: 1234-5678
                publishes research articles in 4 weeks on an average
                Indexed in Scopus
            </p>
        </body>
        </html>
        """
        self.apc_names = {"international journal of testing"}
        self.apc_issns = {"12345678"}

    @patch('journal_scraper.requests.get')
    def test_scrape_journal_details(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = self.sample_html.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call function
        result = journal_scraper.scrape_journal_details("http://example.com", self.apc_names, self.apc_issns)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['Journal Title'], "International Journal of Testing")
        self.assertEqual(result['Publisher'], "Test Press")
        self.assertEqual(result['ISSN'], "1234-5678")
        self.assertEqual(result['Review Time'], "4 weeks")
        self.assertEqual(result['Scopus Indexing'], "Indexed")
        # Since it is in apc_names/apc_issns (I added it to setUp), it should be verified
        self.assertEqual(result['APC'], "Free (Verified via Directory)")

    @patch('journal_scraper.requests.get')
    def test_scrape_journal_details_regex_fallback(self, mock_get):
        # Test the fallback/variation regexes if needed
        # Or test a case where title is not in text but in H1 (logic in code)
        html = """
        <html>
        <body>
            <h1>Fallback Title</h1>
            <p>
                Publisher: Fallback Press
                E-ISSN: 9876-5432
                publishes research articles in 12 weeks
            </p>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = html.encode('utf-8')
        mock_get.return_value = mock_response

        result = journal_scraper.scrape_journal_details("http://example.com/2", set(), set())

        self.assertEqual(result['Journal Title'], "Fallback Title")
        self.assertEqual(result['Publisher'], "Fallback Press")
        self.assertEqual(result['ISSN'], "9876-5432")
        self.assertEqual(result['Review Time'], "12 weeks")

if __name__ == '__main__':
    unittest.main()
