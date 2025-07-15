#!/usr/bin/env python3

import csv
import pathlib
import os
from BCBio import GFF
from argparse import ArgumentParser

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
output_fieldnames = ["genome", "region", "region_start", "region_end", "strand"] + qualifier_columns
conversion_field_names = {
    "id": "ID",
    "gene_symbol": "Name",
    "amr_gene_symbol": "amrfinderplus_gene_symbol",
}


def run_parser(dir, output_file, gff_type="CDS"):
    output = []
    files = list(pathlib.Path().glob(os.path.join(dir, "*.gff")))

    for f in files:
        genome = os.path.basename(f).replace("_annotations.gff", "").replace(".gff", "")
        with open(f, "rt") as handle:
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

    with open(output_file, "wt") as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--dir", required=True, help="Provide the directory to look for GFFs in"
    )
    parser.add_argument(
        "--output", default="amr_genotype.csv", help="Location to write output to"
    )
    parser.add_argument("--gff_type", default="CDS", help="GFF object type to use to find AMR annotation")
    args = parser.parse_args()
    run_parser(args.dir, args.output, args.gff_type)
