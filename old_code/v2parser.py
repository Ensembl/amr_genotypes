#!/usr/bin/env python3

import gffutils
import csv
from typing import List, Dict, Optional
import pathlib
import os
import requests
import urllib.parse
import copy
from argparse import ArgumentParser
from xml.etree import ElementTree
from functools import lru_cache
import re
import logging
import pandas as pd
import time

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("v2parser")

# gff_type = "CDS"
qualifier_columns = [
    "id",
    "taxon_id",
    "genus",
    "scientific_name",
    "organism_name",
    "strain",
    "gene_symbol",
    "amr_element_symbol",
    "element_type",
    "element_subtype",
    "class",
    "subclass",
    "antibioticName",
    "antibioticOntology",
    "antibiotic_ontology_link",
    "evidence_accession",
    "evidence_type",
    "evidence_link",
    "evidence_description",
]
output_fieldnames = [
    "BioSample_ID",
    "assembly_ID",
    "region",
    "region_start",
    "region_end",
    "strand",
    "bin",
] + qualifier_columns
conversion_field_names = {
    "id": "ID",
    "gene_symbol": "Name",
    "amr_element_symbol": "amrfinderplus_element_symbol",
    "amr_element_name": "amrfinderplus_element_name",
    "class": "drug_class",
    "subclass": "drug_subclass",
}

gca_fields = ["taxon_id", "genus", "scientific_name", "organism_name", "strain"]
feature_fields = [c for c in qualifier_columns if c not in gca_fields]


def process_dir(
    dir: str,
    output: List[dict],
    gff_type: str = "CDS",
    amrfinder_plus_filter: str = "AMR",
) -> None:
    """
    Process all *.gff files in a given directory
    """
    files = sorted(pathlib.Path(dir).glob("*.gff"))
    for f in files:
        process_file(
            f, output, gff_type=gff_type, amrfinder_plus_filter=amrfinder_plus_filter
        )


def process_files(
    files: List,
    output: List[dict],
    gff_type: str = "CDS",
    amrfinder_plus_filter: str = "AMR",
) -> None:
    """
    For each line in a file, process each file as a possible GFF target
    """
    for f in files:
        if f:
            process_file(
                f.strip(),
                output,
                gff_type=gff_type,
                amrfinder_plus_filter=amrfinder_plus_filter,
            )


def process_file(
    file_path,
    output: List[dict],
    gff_type: str = "CDS",
    amrfinder_plus_filter: str = "AMR",
) -> None:
    """
    Take a path to a GFF file and process. Add records to the given output variable
    """
    log.info(f"Processing {file_path}")
    gca = (
        os.path.basename(file_path)
        .replace("_annotations.gff", "")
        .replace("_amrfinderplus.gff", "")
        .replace(".gff", "")
    )
    db = gffutils.create_db(file_path, ":memory:")
    log.info(f"Parsing AMRFinderPlus TSV for {gca}")
    amr_records = parse_amrfinderplus_tsv(file_path)
    for feature in db.features_of_type(gff_type):
        if (
            "amrfinderplus_element_symbol" in feature.attributes
            and feature.attributes["element_type"][0] == amrfinder_plus_filter
        ):
            gca_obj = gca_summary(gca)
            record = {
                "assembly_ID": gca_obj.get("gca"),
                "BioSample_ID": gca_obj.get("biosample"),
                "genus": gca_obj.get("genus"),
                "scientific_name": gca_obj.get("scientific_name"),
                "organism_name": gca_obj.get("scientific_name"),
                "strain": gca_obj.get("strain"),
                "taxon_id": gca_obj.get("taxon_id"),
                "region": feature.seqid,
                "region_start": feature.start,
                "region_end": feature.end,
                "strand": feature.strand,
                "bin": feature.bin,
            }
            for col in feature_fields:
                gff_col = conversion_field_names.get(col, col)
                if gff_col in feature.attributes:
                    record[col] = ";".join(feature.attributes[gff_col])
                else:
                    record[col] = ""

            amrfinder = amr_records[feature.id] if feature.id in amr_records else {}

            if "HMM_accession" in amrfinder and amrfinder["HMM_accession"] != "NA":
                record["evidence_accession"] = amrfinder["HMM_accession"]
                record["evidence_type"] = "HMM"
                # Link needs to have version removed and trailing slash added
                record["evidence_link"] = (
                    f"https://www.ncbi.nlm.nih.gov/genome/annotation_prok/evidence/"
                    f"{re.sub(r'\.\d+$', '/', amrfinder['HMM_accession'])}"
                )
                record["evidence_description"] = amrfinder["HMM_description"]

            amr_class = amrfinder.get("Class", "NA")
            amr_subclass = amrfinder.get("Subclass", "NA")
            is_amr_subclass = False if amr_class == amr_subclass else True
            if is_amr_subclass:
                compounds = (
                    amr_subclass.split("/") if "/" in amr_subclass else [amr_subclass]
                )
                for compound in compounds:
                    new_record = copy.deepcopy(record)
                    if amrfinder.get("Subclass") != "NA":
                        compound = convert_antibiotic(compound)
                        new_record["antibioticName"] = compound.get("label")
                        new_record["antibioticOntology"] = compound.get("short_form")
                        new_record["antibiotic_ontology_link"] = compound.get(
                            "ontology_link"
                        )
                    output.append(new_record)
            else:
                record["antibioticName"] = ""
                record["antibiotic_ontology_link"] = ""
                output.append(record)
    log.info(f"Completed {file_path}")


@lru_cache(maxsize=None)
def gca_summary(gca: str) -> Dict[str, str]:
    req = _safe_get(f"https://www.ebi.ac.uk/ena/browser/api/xml/{gca}")
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
        "gca": assembly.get("accession"),
        "taxon_id": taxon_id,
        "scientific_name": scientific_name,
        "genus": genus,
        "strain": strain,
        "biosample": biosample,
    }


def write_csv(output_file: str, output: List[dict]) -> None:
    log.info(f"Writing {len(output)} record(s) in CSV output to {output_file}")
    with open(output_file, "wt") as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(output)


def write_parquet(output_file: str, output: List[dict]) -> None:
    log.info(f"Writing Parquet output to {output_file}")
    df = pd.DataFrame(output, columns=output_fieldnames)
    df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)


def parse_amrfinderplus_tsv(gca: str) -> Dict[str, dict]:
    path = find_amrfinderplus_tsv(gca)
    if not path:
        return {}
    records = {}
    with open(path, "rt") as f:
        reader = csv.DictReader(f, delimiter="\t", dialect="excel")
        for row in reader:
            records[row["Protein_id"]] = row
    return records


def find_amrfinderplus_tsv(file_path: str):
    """
    Given a directory, find one amrfinderplus TSV file
    """
    new_path = file_path.replace("_annotations.gff", "_amrfinderplus.tsv")
    files = list(pathlib.Path().glob(new_path))
    return files.pop() if files else None


@lru_cache(maxsize=None)
def convert_antibiotic(antibiotic: str) -> Optional[dict]:
    mapping = {
        "aro": "http://purl.obolibrary.org/obo/ARO_1000003",
        "chebi": "http://purl.obolibrary.org/obo/CHEBI_33281",
    }
    for ontology in ("aro", "chebi"):
        term = _search_ols(antibiotic, ontology, mapping[ontology])
        if term:
            return term
    log.warning(f"No ontology match for antibiotic {antibiotic}")
    return None


ols_url = "https://www.ebi.ac.uk/ols4/api/search"


def _search_ols(antibiotic: str, ontology: str, children_of: str) -> Optional[dict]:
    req = _safe_get(
        ols_url,
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


def _safe_get(url, params=None, retries=3, timeout=10):
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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--dir",
        help="Provide the directory to look for GFFs in. If you do not use this then use --urls or --files",
        type=str,
    )
    parser.add_argument(
        "--files",
        help="Provide a file of file paths. Assumes 1 file path per line and will be a GFF3 formatted file",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--urls",
        help="Provide a file of URLs. Assumes 1 URL per line and will be a GFF3 formatted file",
        type=str,
    )
    parser.add_argument(
        "--output",
        default="amr_genotype.csv",
        help="Location to write output to",
        type=str,
    )
    parser.add_argument(
        "--output-parquet",
        default="amr_genotype.parquet",
        help="Location to write parquet output to",
        type=str,
    )
    parser.add_argument(
        "--gff_type",
        default="CDS",
        help="GFF object type to use to find AMR annotation",
        type=str,
    )
    parser.add_argument(
        "--filter",
        default="AMR",
        help="Filter AMRFinderPlus records by this element type",
        type=str,
    )
    args = parser.parse_args()

    output = []
    if args.dir:
        process_dir(args.dir, output, gff_type=args.gff_type)
    # elif args.urls:
    #     process_urls(args.urls, output, gff_type=args.gff_type)
    elif args.files:
        process_files(args.files, output, gff_type=args.gff_type)

    write_csv(output_file=args.output, output=output)
    write_parquet(output_file=args.output_parquet, output=output)
