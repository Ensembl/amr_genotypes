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
        if not assembly_id.startswith("GCA"):
            raise ValueError(
                "Only GCA accessions are supported at this point. You provided {assembly_id}. Code will require checking for ERZ accessions and similar."
            )
        req = self._safe_get(f"https://www.ebi.ac.uk/ena/browser/api/xml/{assembly_id}")
        if not req:
            return {}
        tree = ElementTree.fromstring(req.content)
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
            "scientific_name": scientific_name,
            "organism_name": scientific_name,
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
