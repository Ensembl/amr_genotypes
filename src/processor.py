import copy
import csv

from BCBio import GFF
import logging
import os
from pathlib import Path
import re

from functools import cached_property
from typing import List, Dict

from .lookup import Lookup, LocalAntibioticLookup
from .utils import open_file, bin_from_range_extended
from .config import (
    default_conversion_field_names,
    default_feature_fields,
    default_gff_filter,
    default_amr_filter,
)

from config import Leak

log = logging.getLogger(__name__)

ncbi_evidence_link = "https://www.ncbi.nlm.nih.gov/genome/annotation_prok/evidence/"


class Processor:

    @staticmethod
    def default_processor(
        lookup: Lookup,
        local_antibiotic_lookup: LocalAntibioticLookup,
        gff_path,
        amrfinderplus_path: str = None,
        gff_type: str = default_gff_filter,
        amrfinderplus_type: str = default_amr_filter,
        assembly: str = None,
        leak: Leak = Leak.NONE,
    ):
        if amrfinderplus_path is None:
            amrfinderplus_path = Processor.find_amrfinderplus_tsv(gff_path)
        processor = Processor(
            lookup=lookup,
            local_antibiotic_lookup=local_antibiotic_lookup,
            gff_path=gff_path,
            gff_fields=default_feature_fields,
            gff_conversion_field_names=default_conversion_field_names,
            gff_type=gff_type,
            amrfinderplus_path=amrfinderplus_path,
            amrfinderplus_type=amrfinderplus_type,
            assembly=assembly,
            leak=leak,
        )
        return processor

    @staticmethod
    def gff_path_to_assembly(gff_path: str) -> str:
        """Extract the assembly from a given GFF filename

        Args:
            gff_path (str): File path to a GFF file. Assumes the name can be GCA_XXXX_annotations.gff, GCA_XXXX_amrfinderplus.gff or GCA_XXXX.gff. Removes .gz if present.

        Returns:
            str: The assembly accession parsed from the filename
        """
        assembly = (
            os.path.basename(gff_path)
            .replace(".gz", "")
            .replace("_annotations.gff", "")
            .replace("_amrfinderplus.gff", "")
            .replace(".gff", "")
        )
        return assembly

    @staticmethod
    def find_amrfinderplus_tsv(gff_path: str):
        """
        Given a GFF file path, find the corresponding AMRFinderPlus TSV file
        by replacing '_annotations.gff' with '_amrfinderplus.tsv' and searching
        in the same directory.
        """
        gff_path = Path(gff_path)
        # Build the expected TSV filename
        tsv_name = gff_path.name.replace("_annotations.gff", "_amrfinderplus.tsv")
        tsv_path = gff_path.parent / tsv_name
        if tsv_path.exists():
            return tsv_path

        # If GFF was compressed but TSV is not, try removing .gz
        if tsv_path.suffix == ".gz":
            uncompressed_tsv_path = tsv_path.with_suffix("")
            if uncompressed_tsv_path.exists():
                return uncompressed_tsv_path

        return None

    @cached_property
    def assembly_summary(self) -> List[Dict[str, any]]:
        """Return the assembly summary information from ENA

        Returns:
            List[Dict[str, any]]: Description of the assembly record from ENA
        """
        summary = self.lookup.assembly_summary(self.assembly)
        # set some basic information
        summary["phenotype"] = False
        summary["genotype"] = True
        return summary

    def __init__(
        self,
        lookup: Lookup,
        local_antibiotic_lookup: LocalAntibioticLookup,
        gff_path: str,
        gff_fields: List[str],
        gff_conversion_field_names: Dict[str, str] = {},
        gff_type: str = default_gff_filter,
        amrfinderplus_path: str = None,
        amrfinderplus_type: str = default_amr_filter,
        assembly: str = None,
        leak: Leak = Leak.NONE,
    ):
        """Initalise the processor module

        Args:
            lookup (Lookup): The lookup object to use for ontology and GCA lookups
            local_antibiotic_lookup (LocalAntibioticLookup): Local antibiotic lookup object
            gff_path (str): Path to the GFF file to process
            gff_fields (List[str]): Fields which should be extracted from the GFF file's column 9
            gff_conversion_field_names (Dict[str, str], optional): Translates from a column name given in gff_fields to the intended GFF column 9 attribute name. Defaults to {}.
            gff_type (str, optional): Type of GFF feature to process. Defaults to "CDS".
            amrfinderplus_path (str, optional): Path to the AMRFinderPlus file. Defaults to None.
            amrfinderplus_type (str, optional): Type of AMR record to process. Defaults to "AMR".
            assembly (str, optional): Assembly to process. If not given we will attempt to decipher it from the given GFF filename. Defaults to None.
        """
        self.lookup = lookup
        self.local_antibiotic_lookup = local_antibiotic_lookup
        self.gff_path = gff_path
        self.gff_fields = gff_fields
        self.gff_conversion_field_names = gff_conversion_field_names
        self.gff_type = gff_type
        self.amrfinderplus_path = amrfinderplus_path
        self.amrfinderplus_type = amrfinderplus_type
        if assembly:
            self.assembly = assembly
        else:
            self.assembly = Processor.gff_path_to_assembly(gff_path)
        self.leak = leak

    def process(self) -> List[Dict[str, any]]:
        log.info(
            f"Processing GFF {self.gff_path} and AMRFinderPlus data {self.amrfinderplus_path}"
        )
        log.info(f"Parsing AMRFinderPlus TSV for {self.assembly}")
        amr_records = self.parse_amrfinderplus_tsv()
        output = []
        if self.leak == Leak.SKIP_ASSEMBLY_LOOKUP:
            assembly_obj = {
                "assembly_ID": self.assembly,
                "BioSample_ID": "",
                "genus": "",
                "species": "",
                "strain": "",
                "taxon_id": "",
            }
        else:
            assembly_obj = self.lookup.assembly_summary(self.assembly)
        log.info(
            f"Filtering GFF types '{self.gff_type}' and AMRFinderPlus element types '{self.amrfinderplus_type}'"
        )
        with open_file(self.gff_path, mode="rt") as fh:
            for gff_record in GFF.parse(fh, limit_info={"gff_type": [self.gff_type]}):
                for feature in gff_record.features:
                    if self.leak == Leak.SKIP_GFF_PROCESSING:
                        continue
                    if (
                        "amrfinderplus_element_symbol" in feature.qualifiers
                        and feature.qualifiers["element_type"][0]
                        == self.amrfinderplus_type
                    ):
                        location = feature.location
                        bin = bin_from_range_extended(location.start, location.end)
                        strand = "-" if location.strand == -1 else "+"
                        record = {
                            "assembly_ID": assembly_obj.get("assembly_ID"),
                            "BioSample_ID": assembly_obj.get("BioSample_ID"),
                            "genus": assembly_obj.get("genus"),
                            "species": assembly_obj.get("species"),
                            "organism": assembly_obj.get("species"),
                            "strain": assembly_obj.get("strain"),
                            "taxon_id": assembly_obj.get("taxon_id"),
                            "region": gff_record.id,
                            "region_start": int(location.start) + 1,
                            "region_end": int(location.end),
                            "strand": strand,
                            "_bin": bin,
                        }
                        for col in self.gff_fields:
                            gff_col = self.gff_conversion_field_names.get(col, col)
                            if gff_col in feature.qualifiers:
                                record[col] = ";".join(feature.qualifiers[gff_col])
                            else:
                                record[col] = ""
                        amrfinder = (
                            amr_records[feature.id] if feature.id in amr_records else {}
                        )

                        if (
                            "HMM_accession" in amrfinder
                            and amrfinder["HMM_accession"] != "NA"
                        ):
                            record["evidence_accession"] = amrfinder["HMM_accession"]
                            record["evidence_type"] = "HMM"
                            # Link needs to have version removed and trailing slash added
                            hmm_accession_clean = re.sub(
                                r"\.\d+$", "/", amrfinder["HMM_accession"]
                            )
                            record["evidence_link"] = (
                                f"{ncbi_evidence_link}{hmm_accession_clean}"
                            )
                            record["evidence_description"] = amrfinder[
                                "HMM_description"
                            ]

                        amr_class = amrfinder.get("Class", "NA")
                        amr_subclass = amrfinder.get("Subclass", "NA")
                        is_amr_subclass = False if amr_class == amr_subclass else True
                        if is_amr_subclass:
                            compounds = (
                                amr_subclass.split("/")
                                if "/" in amr_subclass
                                else [amr_subclass]
                            )
                            for compound in compounds:
                                new_record = copy.deepcopy(record)
                                if amrfinder.get("Subclass") != "NA":
                                    if self.leak == Leak.SKIP_ANTIBIOTIC_LOOKUP:
                                        compound_obj = None
                                    else:
                                        compound_obj = (
                                            self.local_antibiotic_lookup.convert_antibiotic(
                                                compound
                                            )
                                        )
                                        if compound_obj is None:
                                            # Try the REST lookup
                                            compound_obj = self.lookup.convert_antibiotic(
                                                compound
                                            )
                                    # Both lookups failed
                                    if compound_obj is None:
                                        record["antibioticName"] = ""
                                        record["antibiotic_ontology_link"] = ""
                                    # Successful lookup
                                    else:
                                        antibiotic_name = compound_obj.get("label")
                                        new_record["antibioticName"] = antibiotic_name
                                        # Abbreviations are only found locally
                                        new_record["antibioticAbbreviation"] = (
                                            compound_obj.get("abbreviation", "")
                                        )
                                        new_record["antibiotic_ontology"] = (
                                            compound_obj.get("short_form")
                                        )
                                        new_record["antibiotic_ontology_link"] = (
                                            compound_obj.get("ontology_link")
                                        )
                                output.append(new_record)
                        else:
                            record["antibioticName"] = ""
                            record["antibiotic_ontology_link"] = ""
                            output.append(record)
        log.info(f"Processed {len(output)} AMR records")
        return output

    def parse_amrfinderplus_tsv(self) -> List[Dict[str, any]]:
        if not self.amrfinderplus_path or not os.path.exists(self.amrfinderplus_path):
            return {}
        records = {}
        with open_file(self.amrfinderplus_path, mode="rt") as f:
            reader = csv.DictReader(f, delimiter="\t", dialect="excel")
            for row in reader:
                records[row["Protein_id"]] = row
        return records
