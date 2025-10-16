# Basic set of columns to emit
default_output_columns = [
    "BioSample_ID",
    "assembly_ID",
    "genus",
    "species",
    "organism",
    "strain",
    "taxon_id",
    "region",
    "region_start",
    "region_end",
    "strand",
    "_bin",
    "id",
    "gene_symbol",
    "amr_element_symbol",
    "element_type",
    "element_subtype",
    "class",
    "subclass",
    "antibioticName",
    "antibioticAbbreviation",
    "antibiotic_ontology",
    "antibiotic_ontology_link",
    "evidence_accession",
    "evidence_type",
    "evidence_link",
    "evidence_description",
]

# Mapping of output column names to GFF attribute names if different
default_conversion_field_names = {
    "id": "ID",
    "gene_symbol": "Name",
    "amr_element_symbol": "amrfinderplus_element_symbol",
    "amr_element_name": "amrfinderplus_element_name",
    "class": "drug_class",
    "subclass": "drug_subclass",
    "_bin": "bin",
}

# Modified columns to exclude assembly related fields to ensure we do not overwrite them with incorrect data
assembly_fields = [
    "BioSample_ID",
    "assembly_ID",
    "taxon_id",
    "genus",
    "species",
    "organism",
    "strain",
    "region",
    "region_start",
    "region_end",
    "strand",
    "_bin",
]
default_feature_fields = [c for c in default_output_columns if c not in assembly_fields]

parquet = {
    "compression": "zstd",
    "compression_level": 3,
}

# Taken from CABBAGE antibiograms
antibiotic_acrynoyms = {
    "amikacin": "AMK",
    "ampicillin": "AMP",
    "ampicillin-sulbactam": "SAM",
    "aztreonam": "ATM",
    "cefazolin": "CZO",
    "cefepime": "FEP",
    "cefotaxime": "CTX",
    "cefoxitin": "FOX",
    "ceftazidime": "CAZ",
    "ceftriaxone": "CRO",
    "ciprofloxacin": "CIP",
    "doripenem": "DOR",
    "ertapenem": "ETP",
    "gentamicin": "GEN",
    "imipenem": "IPM",
    "levofloxacin": "LVX",
    "meropenem": "MEM",
    "minocycline": "MNO",
    "nitrofurantoin": "NIT",
    "piperacillin": "PIP",
    "piperacillin-tazobactam": "TZP",
    "tetracycline": "TCY",
    "ticarcillin-clavulanic acid": "TCC",
    "tigecycline": "TGC",
    "tobramycin": "TOB",
    "trimethoprim-sulfamethoxazole": "SXT"
}
