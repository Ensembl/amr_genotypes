from typing import Optional, Dict
import requests
import urllib.parse
import time
from functools import lru_cache
import logging
from xml.etree import ElementTree

log = logging.getLogger(__name__)


class Lookup:
    ols_url = "https://www.ebi.ac.uk/ols4/api/search"

    @lru_cache(maxsize=None)
    def convert_antibiotic(self, antibiotic: str) -> Optional[dict]:
        """Attempts to convert an antibiotic name to an ontology
        term using OLS and will return either an ARO or ChEBI term. In
        both cases the term will be a child of an antibiotic compound term.

        Args:
            antibiotic (str): The string name of the antibiotic to convert

        Returns:
            Optional[dict]: returns a dictionary with ontology information
            or None if no match is found. Keys include 'ontology', 'id',
            'label', 'iri', 'short_form', and 'ontology_link'.

            Terms are taken from the OLS service at EMBL-EBI
        """
        mapping = {
            "aro": "http://purl.obolibrary.org/obo/ARO_1000003",
            "chebi": "http://purl.obolibrary.org/obo/CHEBI_33281",
        }
        for ontology in ("aro", "chebi"):
            term = self._search_ols(antibiotic, ontology, mapping[ontology])
            if term:
                return term
        log.warning(f"No ontology match for antibiotic {antibiotic}")
        return None

    @lru_cache(maxsize=None)
    def assembly_summary(self, assembly_id: str) -> Dict[str, any]:
        """Takes an INSDC accession (like GCA) and returns a summary dictionary
        with taxon and assembly information.

        Args:
            assembly_id (str): The id accession to look up

        Returns:
            Dict[str, any]: A dictionary including information including
            'Assembly_ID', 'taxon_id', 'scientific_name', 'genus', 'strain', and 'Biosample_ID'.
            If the id is not found an empty dictionary is returned.
        """
        req = self._safe_get(f"https://www.ebi.ac.uk/ena/browser/api/xml/{assembly_id}")
        if not req:
            return {}
        return self.parse_assembly_xml(assembly_id, req.text)

    def parse_assembly_xml(self, assembly_id, content: str) -> Dict[str, any]:
        """Parses the XML content from the ENA assembly API and returns a summary dictionary

        Args:
            content (str): XML content from ENA assembly API

        Returns:
            Dict[str, any]: A dictionary including information including
            'Assembly_ID', 'taxon_id', 'scientific_name', 'genus', 'strain', and 'Biosample_ID'.
            If the id is not found an empty dictionary is returned.
        """
        tree = ElementTree.fromstring(content)
        if assembly_id.startswith("GCA"):
            return self._parse_gca(tree)
        elif assembly_id.startswith("ERZ"):
            return self._parse_erz(tree)

    def _parse_gca(self, tree: ElementTree) -> Dict[str, any]:
        assembly = tree.find(".//ASSEMBLY")
        taxon = tree.find(".//TAXON")
        scientific_name = taxon.findtext("SCIENTIFIC_NAME")
        genus = scientific_name.split(" ")[0]
        strain = taxon.findtext("STRAIN", default="")
        taxon_id = int(taxon.findtext("TAXON_ID").strip())
        biosample = tree.findtext(".//SAMPLE_REF/IDENTIFIERS/PRIMARY_ID")
        return {
            "assembly_ID": assembly.get("accession"),
            "taxon_id": taxon_id,
            "species": scientific_name,
            "organism": scientific_name,
            "genus": genus,
            "strain": strain,
            "BioSample_ID": biosample,
        }

    def _parse_erz(self, tree: ElementTree) -> Dict[str, any]:
        analysis = tree.find(".//ANALYSIS")
        assembly_ID = analysis.get("accession").strip()
        for ext_id in tree.findall(".//EXTERNAL_ID"):
            if ext_id.attrib.get("namespace") == "BioSample":
                biosample = ext_id.text
                break
        else:
            raise ValueError(f"No BioSample found for ERZ accession {assembly_ID}")

        biosample_obj = self._safe_get(
            f"https://www.ebi.ac.uk/biosamples/samples/{biosample}.json"
        ).json()
        scientific_name = biosample_obj["characteristics"]["organism"][0]["text"]
        genus = scientific_name.split(" ")[0] if scientific_name else ""
        strain = ""
        taxon_id = biosample_obj["taxId"]
        return {
            "assembly_ID": assembly_ID,
            "taxon_id": taxon_id,
            "species": scientific_name,
            "organism": scientific_name,
            "genus": genus,
            "strain": strain,
            "BioSample_ID": biosample,
        }

    def _search_ols(
        self, antibiotic: str, ontology: str, children_of: str
    ) -> Optional[dict]:
        req = self._safe_get(
            self.ols_url,
            params={
                "q": antibiotic,
                "ontology": ontology,
                "allChildrenOf": children_of,
            },
        )
        results = req.json().get("response", {}).get("docs", [])
        for r in results:
            res = {
                "ontology": r["ontology_name"],
                "id": r["obo_id"],
                "label": r["label"],
                "iri": r["iri"],
                "short_form": r["short_form"],
            }
            url = f"https://www.ebi.ac.uk/ols4/ontologies/{ontology}/classes/{urllib.parse.quote_plus(r['iri'])}"
            res["ontology_link"] = url
            return res
        return None

    def _safe_get(self, url, params=None, retries=3, timeout=10):
        for i in range(retries):
            try:
                r = requests.get(url, params=params, timeout=timeout)
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                log.warning(f"Request failed ({e}); retrying {i+1}/{retries}")
                time.sleep(2 * i)
        log.error(f"Failed after {retries} retries for {url}")
        return None
