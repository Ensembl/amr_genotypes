from src.lookup import Lookup
import unittest

# Uses live connections to ENA and BioSamples both at EBI so don't run as a matter of course
# To run, use: python -m unittest integration-tests/test_ena_accessions.py
class TestEnaAccessions(unittest.TestCase):
    def setUp(self):
        self.lookup = Lookup()

    def test_erz_accession(self):
        # Example ERZ accession
        erz_accession = "ERZ5174833"
        summary = self.lookup.assembly_summary(erz_accession)
        self.assert_fields(summary)
        self.assertEqual(summary.get("assembly_ID"), erz_accession)
        self.assertEqual(summary.get("taxon_id"), 1773)
        self.assertEqual(summary.get("scientific_name"), "Mycobacterium tuberculosis")
        self.assertEqual(summary.get("genus"), "Mycobacterium")

    def test_ena_accession(self):
        # Example ENA accession
        ena_accession = "GCA_000091005.1"
        summary = self.lookup.assembly_summary(ena_accession)
        self.assert_fields(summary)
    
    def assert_fields(self, summary):
        self.assertIsInstance(summary, dict)
        self.assertIn("assembly_ID", summary)
        self.assertIsInstance(summary.get("assembly_ID"), str)
        self.assertIn("taxon_id", summary)
        self.assertIsInstance(summary.get("taxon_id"), int)
        self.assertIn("scientific_name", summary)
        self.assertIsInstance(summary.get("scientific_name"), str)
        self.assertIn("genus", summary)
        self.assertIsInstance(summary.get("genus"), str)
        self.assertIn("strain", summary)
        self.assertIsInstance(summary.get("strain"), str)
        self.assertIn("BioSample_ID", summary)
        self.assertIsInstance(summary.get("BioSample_ID"), str)

if __name__ == "__main__":
    unittest.main()