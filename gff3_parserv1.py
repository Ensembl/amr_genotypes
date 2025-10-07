#!/usr/bin/env python3


import csv
import pathlib
import os
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from BCBio import GFF
from argparse import ArgumentParser
from io import StringIO
from typing import List, TextIO

gff_type = "CDS"
qualifier_columns = [
    "id",
    "gene_symbol",
    "amr_gene_symbol",
    "element_type",
    "element_subtype",
    "drug_class",
    "drug_subclass",
]
output_fieldnames = [
    "genome",
    "region",
    "region_start",
    "region_end",
    "strand",
] + qualifier_columns
conversion_field_names = {
    "id": "ID",
    "gene_symbol": "Name",
    "amr_gene_symbol": "amrfinderplus_gene_symbol",
}


def process_dir(dir: str, output: List[dict], gff_type="CDS") -> None:
    """
    Process all *.gff files in a given directory
    """
    files = list(pathlib.Path().glob(os.path.join(dir, "*.gff")))
    for f in files:
        process_file(f, output, gff_type=gff_type)


def process_files(files: str, output: List[dict], gff_type: str = "CDS") -> None:
    """
    For each line in a file, process each file as a possible GFF target
    """
    with open(files) as handle:
        for f in handle:
            if f:
                if f.startswith("#"):
                    continue
                process_file(f.strip(), output, gff_type=gff_type)


def process_file(file_path, output: List[dict], gff_type: str = "CDS") -> None:
    """
    Take a path to a GFF file and process. Add records to the given output variable
    """
    genome = (
        os.path.basename(file_path)
        .replace("_annotations.gff", "")
        .replace("_amrfinderplus.gff", "")
        .replace(".gff", "")
    )
    with open(file_path, "rt") as handle:
        processed_output = process_gff_handle(
            handle=handle, genome=genome, gff_type=gff_type
        )
        output.extend(processed_output)


def process_urls(urls: str, output: List[dict], gff_type: str = "CDS") -> None:
    """
    For a file which is a set of urls, iterate and parse targets
    as GFF. Add records to the given output variable
    """
    # Open a session and keep it open
    session = requests.Session()
    retries = Retry(
        total=10,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={"GET"},
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    with open(urls, "rt") as file:
        for url in file.readlines():
            strip = url.strip()
            # Process if it had content
            if strip:
                # Skip if it started with #
                if strip.startswith("#"):
                    continue
                process_single_url_gff(strip, session, output, gff_type=gff_type)


def process_single_url_gff(
    url: str, session, output: List[dict], gff_type: str = "CDS"
) -> None:
    genome = (
        url.split("/")[-1]
        .replace("_annotations.gff", "")
        .replace("_amrfinderplus.gff", "")
        .replace(".gff", "")
    )
    r = session.get(url.strip(), allow_redirects=True, verify=True, timeout=10)
    with StringIO(r.text) as handle:
        processed_output = process_gff_handle(handle, genome=genome, gff_type=gff_type)
        output.extend(processed_output)


def process_gff_handle(
    handle: TextIO, genome: str, gff_type: str = "CDS"
) -> List[dict]:
    """
    Workhorse of the script. Parses a line of GFF. Interprets into values and creates
    dict entries for each line which is of gff_type and is an AMR record.

    AMR is found by looking for element_type and amrfinderplus_scope in column 9
    """
    output = []
    for rec in GFF.parse(handle, limit_info={"gff_type": [gff_type]}):
        for feature in rec.features:
            if (
                "element_type" in feature.qualifiers
                and "amrfinderplus_scope" in feature.qualifiers
            ):
                record = {
                    "genome": genome,
                    "region": rec.id,
                    "region_start": int(feature.location.start),
                    "region_end": int(feature.location.end),
                    "strand": int(feature.location.strand),
                }
                for field in qualifier_columns:
                    lookup_key = conversion_field_names.get(field, field)
                    value = feature.qualifiers.get(lookup_key)
                    if value is not None:
                        value = value[0]
                    record[field] = value
                output.append(record)
    return output


def write_csv(output_file: str, output: List[dict]) -> None:
    with open(output_file, "wt") as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(output)


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
        "--gff_type",
        default="CDS",
        help="GFF object type to use to find AMR annotation",
        type=str,
    )
    args = parser.parse_args()

    output = []
    if args.dir:
        process_dir(args.dir, output, gff_type=args.gff_type)
    elif args.urls:
        process_urls(args.urls, output, gff_type=args.gff_type)
    elif args.files:
        process_files(args.files, output, gff_type=args.gff_type)

    write_csv(output_file=args.output, output=output)
