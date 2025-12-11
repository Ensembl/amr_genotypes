#!/usr/bin/env python3

import argparse
import csv
import json
import os
import sys

import requests

CSV_FIELDS = [
    "species_key",
    "scientific_name",
    "taxon_id",
    "species_taxon_id",
    "common_name",
    "type",
    "type_class",
    "biosample_id",
    "assembly_accession",
    "assembly_name",
    "assembly_level",
    "provider",
    "release",
    "homologies",
    "variation",
    "regulation",
]


def make_base_row(species_key, sp):
    return {
        "species_key": species_key,
        "scientific_name": sp.get("scientific_name"),
        "taxon_id": sp.get("taxid"),
        "species_taxon_id": sp.get("species_taxonomy_id"),
        "common_name": sp.get("common_name"),
        "type": sp.get("strain"),
        "type_class": sp.get("strain_type"),
        "biosample_id": sp.get("biosample_id"),
        # filled in later
        "assembly_accession": None,
        "assembly_name": None,
        "assembly_level": None,
        "provider": None,
        "release": None,
        "homologies": False,
        "variation": False,
        "regulation": False,
    }


def present_files(paths, key):
    """Return True if paths[key]['files'] exists and is non-empty."""
    if not isinstance(paths, dict):
        return False
    v = paths.get(key)
    if not isinstance(v, dict):
        return False
    files = v.get("files")
    return bool(files)


def emit_row(writer, base, **overrides):
    row = base.copy()
    row.update(overrides)
    writer.writerow(row)


def process_species_dict(species_dict, writer):
    """
    species_dict: mapping of species_key -> species_object
    writer: csv.DictWriter
    """
    for species_key, sp in species_dict.items():
        base = make_base_row(species_key, sp)
        assemblies = sp.get("assemblies")

        for acc, assembly in assemblies.items():
            assembly_name = assembly.get("name")
            assembly_level = assembly.get("level")

            base_assembly = {
                "assembly_accession": acc,
                "assembly_name": assembly_name,
                "assembly_level": assembly_level,
            }

            providers = assembly.get("genebuild_providers")

            for provider_name, releases in providers.items():

                for release_key, release_data in releases.items():
                    paths = release_data.get("paths")

                    hom = present_files(paths, "homologies")
                    var = present_files(paths, "variation")
                    reg = present_files(paths, "regulation")

                    emit_row(
                        writer,
                        base,
                        **base_assembly,
                        provider=provider_name,
                        release=release_key,
                        homologies=hom,
                        variation=var,
                        regulation=reg,
                    )


def load_json_from_source(source):
    """Return parsed JSON (dict). Source may be a local path or a URL."""
    if source.startswith(("http://", "https://")):
        r = requests.get(source)
        r.raise_for_status()
        return r.json()
    with open(source, mode="r", encoding="utf-8") as fh:
        return json.load(fh)


def run(source, output):
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    data = load_json_from_source(source)
    species = data.get("species")

    with open(output, mode="w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        process_species_dict(species, writer)


def main():
    p = argparse.ArgumentParser(description="Convert species JSON → CSV.")
    p.add_argument(
        "--source", "-s", required=True, help="Local path or URL to species.json"
    )
    p.add_argument("--output", "-o", required=True, help="CSV output filename")
    args = p.parse_args()

    try:
        run(args.source, args.output)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
