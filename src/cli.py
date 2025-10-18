from argparse import ArgumentParser
from functools import cached_property
from .lookup import Lookup
from .processor import Processor
from .config import (
    default_output_columns,
    default_feature_fields,
    default_conversion_field_names,
    assembly_fields,
)
from .writer import Formats, StreamingAmrWriter
from .utils import open_file
import pathlib
import logging
from typing import List

log = logging.getLogger(__name__)


class Cli:

    def __init__(self):
        self.records = 0
        self.assemblies = 0

    def run(self):
        files = []
        if self.args.dir:
            files = sorted(list(pathlib.Path(self.args.dir).rglob("*.gff*")))
        elif self.args.files:
            files = [s.strip() for s in self.args.files]
        elif self.args.files_list:
            with open_file(self.args.files_list) as f:
                files = [line.strip() for line in f]
        if files:
            self.process_files(files)
        log.info(
            f"Processed {self.records} AMR features from {self.assemblies} assemblies"
        )

    def process_files(self, files: List):
        # with StreamingAmrWriter(
        #     self.args.output, columns=default_output_columns, format=Formats.CSV
        # ) as amr_csv, StreamingAmrWriter(
        #     self.args.output_parquet,
        #     columns=default_output_columns,
        #     format=Formats.PARQUET,
        # ) as amr_parquet, StreamingAmrWriter(
        #     self.args.output_assembly, columns=assembly_fields, format=Formats.CSV
        # ) as assembly_csv, StreamingAmrWriter(
        #     self.args.output_assembly_parquet,
        #     columns=assembly_fields,
        #     format=Formats.PARQUET,
        # ) as assembly_parquet:
        with StreamingAmrWriter(
            self.args.output, columns=default_output_columns, format=Formats.CSV
        ) as amr_csv, StreamingAmrWriter(
            self.args.output_assembly, columns=assembly_fields, format=Formats.CSV
        ) as assembly_csv:
            for file in files:
                log.info(f"Processing file {file}")
                assembly = Processor.gff_path_to_assembly(file)
                amrfinderplus_path = Processor.find_amrfinderplus_tsv(file)

                processor = Processor(
                    lookup=self.lookup,
                    gff_path=file,
                    gff_fields=default_feature_fields,
                    gff_conversion_field_names=default_conversion_field_names,
                    gff_type=self.args.gff_type,
                    amrfinderplus_path=amrfinderplus_path,
                    amrfinderplus_type=self.args.filter,
                    assembly=assembly,
                )

                try:
                    output = processor.process()
                    amr_csv.write_data(output)
                    # amr_parquet.write_data(output)
                    assembly_csv.write_data([processor.assembly_summary], flush=True)
                    # assembly_parquet.write_data([processor.assembly_summary])
                    self.records += len(output)
                    self.assemblies += 1
                except EOFError:
                    log.error(
                        f"{assembly} file {file} might be corrupted. Check the file. Skipping record"
                    )
                except Exception as e:
                    log.error(
                        f"Unknown issue with {assembly} file {file}. {e}. Skipping record"
                    )

    @cached_property
    def args(self):
        parser = self.create_argument_parser()
        return parser.parse_args()

    @cached_property
    def lookup(self):
        return Lookup()

    def create_argument_parser(self):
        parser = ArgumentParser()
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
            "--urls",
            help="Provide a file of URLs. Assumes 1 URL per line and will be a GFF3 formatted file",
            type=str,
        )
        parser.add_argument(
            "--output",
            default="amr_genotype.csv",
            help="Location to write output to. Adding a compression extension (e.g. .gz, .bz2, .xz, .br) will compress the file accordingly",
            type=str,
        )
        parser.add_argument(
            "--output-parquet",
            default="amr_genotype.parquet",
            help="Location to write parquet output to",
            type=str,
        )
        parser.add_argument(
            "--output-assembly",
            default="assembly.csv",
            help="Location to write assembly CSV output to. Adding a compression extension (e.g. .gz, .bz2, .xz, .br) will compress the file accordingly",
            type=str,
        )
        parser.add_argument(
            "--output-assembly-parquet",
            default="assembly.parquet",
            help="Location to write assembly parquet output to",
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
        return parser
