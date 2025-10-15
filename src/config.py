# Basic set of columns to emit
default_columns = [
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

# Mapping of output column names to GFF attribute names if different
default_conversion_field_names = {
    "id": "ID",
    "gene_symbol": "Name",
    "amr_element_symbol": "amrfinderplus_element_symbol",
    "amr_element_name": "amrfinderplus_element_name",
    "class": "drug_class",
    "subclass": "drug_subclass",
}

# Full set of columns to emit in default output
default_output_columns = [
    "BioSample_ID",
    "assembly_ID",
    "region",
    "region_start",
    "region_end",
    "strand",
    "bin",
] + default_columns

# Modified columns to exclude assembly related fields to ensure we do not overwrite them with incorrect data
assembly_fields = [
    "BioSample_ID",
    "assembly_ID",
    "taxon_id",
    "genus",
    "scientific_name",
    "organism_name",
    "strain",
]
default_feature_fields = [c for c in default_columns if c not in assembly_fields]
