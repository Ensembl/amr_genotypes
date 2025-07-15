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


def process_dir(dir, output, gff_type="CDS"):
    files = list(pathlib.Path().glob(os.path.join(dir, "*.gff")))
    for f in files:
        genome = (
            os.path.basename(f)
            .replace("_annotations.gff", "")
            .replace("_amrfinderplus.gff", "")
            .replace(".gff", "")
        )
        with open(f, "rt") as handle:
            processed_output = process_file(
                handle=handle, genome=genome, gff_type=gff_type
            )
            output.extend(processed_output)


def process_urls(urls, output, gff_type="CDS"):
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


def process_single_url_gff(url: str, session, output, gff_type="CDS"):
    genome = (
        url.split("/")[-1]
        .replace("_annotations.gff", "")
        .replace("_amrfinderplus.gff", "")
        .replace(".gff", "")
    )
    r = session.get(url.strip(), allow_redirects=True, verify=True, timeout=10)
    with StringIO(r.text) as handle:
        processed_output = process_file(handle, genome=genome, gff_type=gff_type)
        output.extend(processed_output)


def process_file(handle, genome, gff_type="CDS"):
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


def write_csv(output_file, output):
    with open(output_file, "wt") as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--dir",
        help="Provide the directory to look for GFFs in. If you do not use this then use --urls",
    )
    parser.add_argument(
        "--urls",
        help="Provide a file of URLs. Assumes 1 URL per line and will be a GFF3 formatted file",
    )
    parser.add_argument(
        "--output", default="amr_genotype.csv", help="Location to write output to"
    )
    parser.add_argument(
        "--gff_type",
        default="CDS",
        help="GFF object type to use to find AMR annotation",
    )
    args = parser.parse_args()

    output = []
    if args.dir:
        process_dir(args.dir, output, gff_type=args.gff_type)
    elif args.urls:
        process_urls(args.urls, output, gff_type=args.gff_type)

    write_csv(output_file=args.output, output=output)
