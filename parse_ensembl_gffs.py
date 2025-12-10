#!/usr/bin/env python3

import logging
import argparse
from src.utils import open_file
import pathlib
from typing import List
from src.writer import Formats, StreamingAmrWriter
from src.gff_parser import GFF3StreamingParser, Feature
from src.lookup import Lookup

log = logging.getLogger(__name__)

gene_fields = [
    "species",
    "assembly_accession",
    "assembly_version",
    "annotation_build_date",
    "taxon_id",
    "stable_id",
    "version",
    "stable_id_version",
    "symbol",
    "description",
    "biotype",
    "region_name",
    "region_start",
    "region_end",
    "strand",
    "_bin",
]
transcript_fields = [
    "species",
    "assembly_accession",
    "assembly_version",
    "annotation_build_date",
    "taxon_id",
    "stable_id",
    "version",
    "stable_id_version",
    "biotype",
    "region_name",
    "region_start",
    "region_end",
    "strand",
    "_bin",
    "tags",
    "transcript_support_level",
    "canonical",
    "gencode_primary",
]


class Cli:
    def __init__(self):
        self.records = 0
        self.files = 0

    def args(self):
        parser = argparse.ArgumentParser(description="Parse Ensembl GFF files.")
        parser.add_argument(
            "--dir",
            help="Provide the directory to look for GFFs in. Assumes anything called *.gff* should be parsed. If you do not use this then use --files or --files-list",
            type=str,
        )
        parser.add_argument(
            "--files",
            help="Provide a file to parse. Assumes each file is a GFF3 formatted file. Supports compressed files",
            nargs="+",
            type=str,
        )
        parser.add_argument(
            "--files-list",
            help="Provide a file of file paths. Assumes 1 file path per line and will be a GFF3 formatted file",
            type=str,
        )
        parser.add_argument(
            "--output-genes",
            help="Output file for genes",
            type=str,
            default="genes.csv",
        )
        parser.add_argument(
            "--output-transcripts",
            help="Output file for transcripts",
            type=str,
            default="transcripts.csv",
        )
        parser.add_argument(
            "--output-proteins",
            help="Output file for proteins",
            type=str,
            default="proteins.csv",
        )
        return parser.parse_args()

    def run(self):
        files = []
        args = self.args()
        log.info("Parsing Ensembl GFF files...")
        if args.dir:
            files = sorted(list(pathlib.Path(args.dir).rglob("*.gff*")))
        elif args.files:
            files = [s.strip() for s in args.files]
        elif args.files_list:
            with open_file(args.files_list) as f:
                files = [line.strip() for line in f]
        if files:
            self.process_files(args, files)
        log.info(
            f"Processed {self.records} GFF records features from {self.files} files"
        )
        log.info("Parsing completed.")

    def process_files(self, args, files: List):
        lookup = Lookup()
        transcript_types = [
            "lnc_RNA",
            "miRNA",
            "mRNA",
            "ncRNA",
            "pseudogenic_transcript",
            "rRNA",
            "scRNA",
            "snoRNA",
            "snRNA",
            "unconfirmed_transcript",
        ]
        with StreamingAmrWriter(
            args.output_genes, columns=gene_fields, format=Formats.CSV
        ) as gene_csv, StreamingAmrWriter(
            args.output_transcripts, columns=transcript_fields, format=Formats.CSV
        ) as transcript_csv:
            for file in files:
                with GFF3StreamingParser(path=file) as stream:
                    records = 0
                    accession = None
                    version = None
                    annotation_build_date = None
                    assembly_info = None
                    for feature in stream:
                        if accession is None:
                            accession = stream.extract_directive(
                                "genome-build-accession"
                            )
                            assembly_info = lookup.assembly_summary(accession)
                        if version is None:
                            version = stream.extract_directive("genome-version")
                        if annotation_build_date is None:
                            annotation_build_date = stream.extract_directive(
                                "genebuild-last-updated"
                            )
                        if "gene" in feature.type:
                            gene_csv.write_data(
                                [
                                    self.feature_to_gene(
                                        feature,
                                        assembly_info,
                                        version,
                                        annotation_build_date,
                                    )
                                ]
                            )
                        elif feature.type in transcript_types:
                            transcript_csv.write_data(
                                [
                                    self.feature_to_transcript(
                                        feature,
                                        assembly_info,
                                        version,
                                        annotation_build_date,
                                    )
                                ]
                            )
                        else:
                            continue
                        records += 1
                    log.info(f"Processed {records} features from file {file}")
                    self.records += records
                    self.files += 1

    def feature_to_gene(
        self,
        feature: Feature,
        assembly_info: dict[str, any],
        assembly_version,
        annotation_build_date,
    ) -> dict:
        id = feature.get_single_attribute("gene_id")
        version = feature.get_single_attribute("version")
        if version:
            full_id = f"{id}.{version}"
        else:
            full_id = id
        return {
            "species": assembly_info.get("species"),
            "assembly_accession": assembly_info.get("assembly_ID"),
            "assembly_version": assembly_version,
            "annotation_build_date": annotation_build_date,
            "taxon_id": assembly_info.get("taxon_id"),
            "stable_id": id,
            "version": version,
            "stable_id_version": full_id,
            "symbol": feature.get_single_attribute("Name", ""),
            "description": feature.get_single_attribute("description", ""),
            "biotype": feature.get_single_attribute("biotype", ""),
            "region_name": feature.seqid,
            "region_start": feature.start,
            "region_end": feature.end,
            "strand": feature.strand,
            "_bin": feature.bin(),
        }

    def feature_to_transcript(
        self,
        feature: Feature,
        assembly_info: dict[str, any],
        assembly_version,
        annotation_build_date,
    ) -> dict:
        id = feature.get_single_attribute("transcript_id")
        version = feature.get_single_attribute("version")
        if version:
            full_id = f"{id}.{version}"
        else:
            full_id = id
        vals = {
            "species": assembly_info.get("species"),
            "assembly_accession": assembly_info.get("assembly_ID"),
            "assembly_version": assembly_version,
            "annotation_build_date": annotation_build_date,
            "taxon_id": assembly_info.get("taxon_id"),
            "stable_id": id,
            "version": version,
            "stable_id_version": full_id,
            "biotype": feature.get_single_attribute("biotype", ""),
            "region_name": feature.seqid,
            "region_start": feature.start,
            "region_end": feature.end,
            "strand": feature.strand,
            "_bin": feature.bin(),
            "tags": feature.get_concatenated_attribute("tag"),
            "transcript_support_level": feature.get_single_attribute(
                "transcript_support_level", "NA"
            ),
        }
        tags = feature.get_attribute_list("tag")
        vals["canonical"] = "Ensembl_canonical" in tags
        vals["gencode_primary"] = "gencode_primary" in tags
        return vals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Cli().run()
