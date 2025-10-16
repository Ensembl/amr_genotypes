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
from .writer import AmrWriter
import pathlib
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class Cli:

    def __init__(self):
        self.output = []
        self.assemblies = []

    def run(self):
        if self.args.dir:
            self.process_dir()
        elif self.args.files:
            self.process_files()
        log.info(
            f"Processed {len(self.output)} AMR features from {len(self.assemblies)} assemblies"
        )
        self.write_outputs()

    def process_dir(self):
        """Process all GFF files in a given directory"""
        files = sorted(pathlib.Path(self.args.dir).glob("*.gff*"))
        for f in files:
            self.process_file(f)

    def process_files(self):
        """Process all GFF files given at the command line"""
        for f in self.args.files:
            if f:
                self.process_file(f.strip())

    def process_file(self, file: str):
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
        self.output.extend(processor.process())
        self.assemblies.append(processor.assembly_summary)

    def write_outputs(self):
        if self.args.output:
            log.info(f"Writing output to {self.args.output}")
            writer = AmrWriter(
                filename=self.args.output,
                columns=default_output_columns,
                format=AmrWriter.Formats.CSV,
            )
            writer.write_data(self.output)
            writer.close()
        if self.args.output_parquet:
            log.info(f"Writing parquet output to {self.args.output_parquet}")
            writer = AmrWriter(
                filename=self.args.output_parquet,
                columns=default_output_columns,
                format=AmrWriter.Formats.PARQUET,
            )
            writer.write_data(self.output)
            writer.close()
        if self.args.output_assembly:
            log.info(f"Writing assembly output to {self.args.output_assembly}")
            writer = AmrWriter(
                filename=self.args.output_assembly,
                columns=assembly_fields,
                format=AmrWriter.Formats.CSV,
            )
            writer.write_data(self.assemblies)
            writer.close()
        if self.args.output_assembly_parquet:
            log.info(
                f"Writing assembly parquet output to {self.args.output_assembly_parquet}"
            )
            writer = AmrWriter(
                filename=self.args.output_assembly_parquet,
                columns=assembly_fields,
                format=AmrWriter.Formats.PARQUET,
            )
            writer.write_data(self.assemblies)
            writer.close()

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
            "--output-assembly",
            default="assembly.csv",
            help="Location to write assembly CSV output to",
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
