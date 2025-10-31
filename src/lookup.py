from typing import Optional, Dict
from functools import cached_property
import requests
import urllib.parse
import time
from functools import lru_cache
import logging
from xml.etree import ElementTree
import duckdb

log = logging.getLogger(__name__)


class LocalAntibioticLookup:
    def __init__(self, path: str):
        self.path = path

    @cached_property
    def db(self):
        db = duckdb.connect(database=":memory:")

        db.execute(
            f"""
        CREATE TABLE antibiotics AS 
        SELECT * FROM read_csv('{self.path}')
        """
        )
        db.execute("INSTALL fts")
        db.execute("LOAD fts")
        db.execute(
            """
        PRAGMA create_fts_index('antibiotics', 'antibiotic_name', 'antibiotic_name')
        """
        )

        return db

    @lru_cache(maxsize=200)
    def convert_antibiotic(self, antibiotic: str) -> Optional[dict]:
        """Attempts to convert an antibiotic name to an ontology
        term using a local DuckDB FTS index.

        Args:
            antibiotic (str): The string name of the antibiotic to convert

        Returns:
            Optional[dict]: returns a dictionary with ontology information
            or None if no match is found. Keys include 'ontology', 'id',
            'label', 'iri', 'short_form', and 'ontology_link'.
        """

        common_columns = "ontology, antibiotic_ontology as id, antibiotic_name as label, antibiotic_abbreviation, antibiotic_ontology_link as ontology_link, iri"

        # Try a direct match first
        result = self.db.execute(
            f"""
        SELECT {common_columns}
        FROM antibiotics
        where lower(antibiotic_name) = lower(?)
        """,
            [antibiotic],
        ).fetchone()

        # Now try FTS match
        if not result:
            result = self.db.execute(
                f"""
            SELECT {common_columns}, score FROM 
            (
                select *, fts_main_antibiotics.match_bm25(antibiotic_name, ?) as score from antibiotics
            )
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT 1
            """,
                [antibiotic],
            ).fetchone()

        if result:
            return {
                "ontology": result[0],
                "id": result[1].replace("_", ":") if result[1] else None,
                "short_form": result[1],
                "label": result[2],
                "abbreviation": result[3],
                "ontology_link": result[4],
                "iri": result[5],
            }
        log.warning(f"No ontology match for antibiotic {antibiotic}")
        return None


class Lookup:
    ols_url = "https://www.ebi.ac.uk/ols4/api/search"
    mapping = {
        "aro": "http://purl.obolibrary.org/obo/ARO_1000003",
        "chebi": "http://purl.obolibrary.org/obo/CHEBI_33281",
    }

    def __init__(self):
        self.session = requests.Session()

    @lru_cache(maxsize=50)
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

        for ontology in ("aro", "chebi"):
            term = self._search_ols(antibiotic, ontology, self.mapping[ontology])
            if term:
                return term
        log.warning(f"No ontology match for antibiotic {antibiotic}")
        return None

    def antibiotic_iri_to_group(
        self, iri: str, ontology: str = "aro"
    ) -> Dict[str, str]:
        """Takes an antibiotic ontology IRI and returns the antibiotic group
        information by querying OLS. Assumes the group is the one below either
        ARO:1000003 or CHEBI:33281.

        Args:
            iri (str): The ontology IRI to look up. Will double URL encode as needed.
            ontology (str, optional): The ontology to query. Defaults to "aro".

        Returns:
            Dict[str]: A dictionary with ontology information including
            'ontology', 'id', 'label', 'iri', 'short_form', and 'ontology_link'.
            If no match is found an empty dictionary is returned.
        """
        double_encoded_iri = urllib.parse.quote_plus(urllib.parse.quote_plus(iri))
        url = f"https://www.ebi.ac.uk/ols4/api/ontologies/aro/terms/{double_encoded_iri}/hierarchicalAncestors"
        req = self._safe_get(
            url,
            params={
                "onto": ontology,
                "lang": "en",
            },
            headers={"Accept": "application/json"},
        )
        bound_term = self.mapping[ontology]
        count = req.json().get("page", {}).get("totalElements", 0)
        if count:
            results = req.json().get("_embedded", {}).get("terms", [])
            last_term = None
            for r in results:
                # Always assigned to the first one
                if last_term is None:
                    last_term = r
                    next
                if r["iri"] == bound_term:
                    break
                last_term = r
            return {
                "ontology": last_term["ontology_name"],
                "id": last_term["obo_id"],
                "label": last_term["label"],
                "iri": last_term["iri"],
                "short_form": last_term["short_form"],
                "ontology_link": f"https://www.ebi.ac.uk/ols4/ontologies/{last_term['ontology_name']}/classes/{urllib.parse.quote_plus(last_term['iri'])}",
            }
        return {}

    def assembly_summary(self, assembly_id: str) -> Dict[str, any]:
        """Takes an INSDC accession (like GCA) and returns a summary dictionary
        with taxon and assembly information.

        Args:
            assembly_id (str): The id accession to look up

        Returns:
            Dict[str, any]: A dictionary including information including
            'Assembly_ID', 'taxon_id', 'scientific_name', 'genus', 'isolate', and 'Biosample_ID'.
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
            'Assembly_ID', 'taxon_id', 'scientific_name', 'genus', 'isolate', and 'Biosample_ID'.
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
        isolate = taxon.findtext("STRAIN", default="")
        taxon_id = int(taxon.findtext("TAXON_ID").strip())
        biosample = tree.findtext(".//SAMPLE_REF/IDENTIFIERS/PRIMARY_ID")
        return {
            "assembly_ID": assembly.get("accession"),
            "taxon_id": taxon_id,
            "species": scientific_name,
            "organism": scientific_name,
            "genus": genus,
            "isolate": isolate,
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
        isolate = ""
        taxon_id = biosample_obj["taxId"]
        return {
            "assembly_ID": assembly_ID,
            "taxon_id": taxon_id,
            "species": scientific_name,
            "organism": scientific_name,
            "genus": genus,
            "isolate": isolate,
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

    def _safe_get(self, url, params=None, headers={}, retries=5, timeout=10):
        for i in range(retries):
            try:
                r = self.session.get(
                    url, params=params, timeout=timeout, headers=headers
                )
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                log.warning(f"Request failed ({e}); retrying {i+1}/{retries}")
                time.sleep(2 * i)
        log.error(f"Failed after {retries} retries for {url}")
        return None
