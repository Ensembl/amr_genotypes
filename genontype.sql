CREATE TABLE amr_genotype (
    genome VARCHAR,
    region VARCHAR,
    region_start INTEGER,
    region_end INTEGER,
    strand INTEGER,
    id VARCHAR,
    gene_symbol VARCHAR,
    amr_gene_symbol VARCHAR,
    element_type VARCHAR,
    element_subtype VARCHAR,
    drug_class VARCHAR,
    drug_subclas VARCHAR
);

copy amr_genotype from 'amr_genotype.csv';

COPY amr_genotype to 'amr_genotype.parquet' (FORMAT parquet, COMPRESSION zstd);
