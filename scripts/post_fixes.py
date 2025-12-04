#!/usr/bin/env python3

import argparse
from pathlib import Path
import duckdb


def load_duckdb(con, args) -> None:
    print(f"Loading database tables into DuckDB")
    print(f" > Loading genotype from {args.genotype}")
    con.execute(
        "CREATE TABLE genotype AS SELECT * FROM read_parquet(?)", [str(args.genotype)]
    )
    print(f" > Loading phenotype from {args.phenotype}")
    con.execute(
        "CREATE TABLE phenotype AS SELECT * FROM read_parquet(?)", [str(args.phenotype)]
    )
    con.execute(
        "CREATE TABLE fix_antibiotics as select * FROM read_csv(?)",
        [str(args.antibiotic_lookup)],
    )
    print(f" > Loading antibiotic fixes from {args.antibiotic_lookup}")
    antib_fix = con.execute("SELECT count(*) FROM fix_antibiotics").fetchone()[0]
    print(f" > Found {antib_fix} entries to use for fixing antibiotic naming")
    if args.filter_genomes:
        print(f" > Loading genomes filter from {args.filter_genomes}")
        con.execute(
            "CREATE TABLE filter_genomes as SELECT * from read_csv(?)",
            [str(args.filter_genomes)],
        )
        filter_genomes = con.execute("SELECT count(*) FROM filter_genomes").fetchone()[
            0
        ]
        print(
            f" > Found {filter_genomes} entries to use for fltering genomes in genotypes"
        )


species_names_override = [
    ["Salmonella enterica", "Salmonella enterica subsp. enterica serovar Kentucky"],
    ["Salmonella enterica", "Salmonella enterica subsp. enterica serovar Hadar"],
]


def update_genotype(con) -> None:
    print("Updating the genotype table")
    # print(" > Updating genotype species names from phenotype")
    table = "genotype"
#     query = """
# UPDATE genotype 
# SET species = phenotype.species 
# FROM phenotype 
# WHERE genotype.BioSample_ID = phenotype.BioSample_ID and genotype.assembly_ID = phenotype.assembly_ID;
# """
#     con.execute(query)
    for overrides in species_names_override:
        print(f" > Applying specific override for {overrides[1]}")
        con.execute("UPDATE genotype SET species =? WHERE species=?", overrides)

    print(" > Removing any 'subsp.' information from species")
    con.execute(
        "UPDATE genotype SET species = regexp_replace(species, ?, '') WHERE species LIKE ?",
        ["\\ssubsp\\..+$", "%subsp.%"],
    )
    print(" > Removing any 'complex' information from species")
    con.execute(
        "UPDATE genotype SET species = regexp_replace(species, ?, '') WHERE species LIKE ?",
        ["\\scomplex.+$", "%complex%"],
    )
    print(" > Removing any 'variant' information from species")
    con.execute(
        "UPDATE genotype SET species = regexp_replace(species, ?, '') WHERE species LIKE ?",
        ["\\svariant.+$", "%variant%"],
    )
    print(" > Removing any 'sp.' information from species")
    con.execute(
        "UPDATE genotype SET species = regexp_replace(species, ?, '') WHERE species LIKE ?",
        ["\\ssp\\..*$", "%sp.%"],
    )
    print(" > Removing anything beyond the first two words in species")
    con.execute(
        "UPDATE genotype SET species = COALESCE(NULLIF(regexp_extract(species, ?), ''), species)",
        ["^(\\S+\\s+\\S+)"],
    )
    print(" > Ensuring the species are 'Upper lower' formatted e.g. Haemophilus influenzae")
    con.execute(
        """UPDATE genotype SET species = upper(left(species, 1)) || lower(substr(species, 2))"""
    )

    rows = con.execute(
        "SELECT count(*) FROM genotype where taxon_id IS NULL"
    ).fetchone()[0]
    if rows:
        print(f"Deleting any extra rows from genotype")
        query = """
DELETE FROM genotype
WHERE taxon_id IS NULL
"""
        con.execute(query)

    drop_generated_columns(con, table)

    print(" > Fixing missing antibiotics")
    con.execute(
        """
UPDATE genotype
SET antibiotic_name = a.label, antibiotic_ontology = replace(a.id, ':', '_'), antibiotic_ontology_link = a.ontology_link
FROM fix_antibiotics a
WHERE genotype.subclass = a.subclass and genotype.antibiotic_name = ''
"""
    )
    drop_antibiotic_abbreviations(con, table)
    set_string_column_to_null(con, table, "antibiotic_name")
    con.commit()


def update_phenotype(con) -> None:
    table = "phenotype"
    print(f"Updating the table {table}")
    print(f" > Updating known BioSample_ID data error in {table} table")
    affected_ids = [["SAMEA1028830", "8830"]]
    for ids in affected_ids:
        print(f"  > Changing {ids[1]} to {ids[0]}")
        query = f"UPDATE {table} SET BioSample_ID = ? WHERE BioSample_ID = ?"
        con.execute(query, ids)
    drop_generated_columns(con, table)
    drop_antibiotic_abbreviations(con, table)
    con.commit()


def drop_generated_columns(con, table) -> None:
    print(f" > Dropping generated columns from {table}")
    print(f" > Finding columns in {table} with a 'gen_' prefix")
    columns = con.execute(
        """
SELECT column_name
FROM duckdb_columns()
WHERE table_name = ?
AND column_name LIKE ?
""",
        (table, "gen\\_%"),
    ).fetchall()
    for col in columns:
        drop_column(col, table, col[0])


def drop_antibiotic_abbreviations(con, table: str) -> None:
    col = "antibiotic_abbreviation"
    drop_column(con, table, col)


def drop_column(con, table: str, column: str) -> None:
    print(f" > Dropping {column} column from {table} if it exists")
    con.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")


def set_string_column_to_null(con, table: str, column: str) -> None:
    print(f" > Setting {table}.{column} = '' to NULL")
    con.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} = ''")


def filter_genomes(con) -> None:
    """Remove assemblies as specified in the assemblies list"""
    print("Deleting genotype records where they have been suppressed")
    con.execute(
        "DELETE FROM genotype WHERE assembly_ID IN (select id from filter_genomes)"
    )


def create_assembly(con) -> None:
    print("Creating assembly table from phenotype and genotype tables")

    print(" > Creating unique assembly records from phenotype")
    con.execute(
        """
CREATE OR REPLACE TABLE uniq_pheno_ass AS
SELECT DISTINCT
    BioSample_ID,
    assembly_ID,
    genus,
    species,
    organism,
    isolate,
FROM phenotype
"""
    )

    print(" > Creating unique assembly records from genotype")
    con.execute(
        """
CREATE OR REPLACE TABLE uniq_geno_ass AS
SELECT DISTINCT
    BioSample_ID,
    assembly_ID,
    genus,
    species,
    organism,
    isolate,
    taxon_id
FROM genotype
"""
    )

    print(" > Generating unique assembly table based on phenotype data")
    con.execute(
        """
CREATE OR REPLACE TABLE assembly AS 
SELECT DISTINCT 
    p.BioSample_ID, 
    p.assembly_ID, 
    p.genus, 
    p.species,
    ANY_VALUE(COALESCE(p.organism, g.organism)) as organism, 
    ANY_VALUE(COALESCE(g.isolate, p.isolate)) as isolate,
    ANY_VALUE(g.taxon_id) as taxon_id,
    IF(ANY_VALUE(p.BioSample_ID) is null, false, true) as phenotype, 
    IF(ANY_VALUE(g.BioSample_ID) is null, false, true) as genotype
FROM uniq_pheno_ass p
LEFT JOIN uniq_geno_ass g on (p.BioSample_ID = g.BioSample_ID and p.assembly_ID = g.assembly_ID)
group by p.BioSample_ID, p.assembly_ID, p.genus, p.species
"""
    )

    print(" > Adding data from genotype")
    con.execute(
        """
INSERT INTO assembly
SELECT DISTINCT 
    g.BioSample_ID, 
    g.assembly_ID, 
    g.genus, 
    g.species,
    ANY_VALUE(COALESCE(g.organism, p.organism)) as organism, 
    ANY_VALUE(COALESCE(g.isolate, p.isolate)) as isolate,
    ANY_VALUE(g.taxon_id) as taxon_id,
    IF(ANY_VALUE(p.BioSample_ID) is null, false, true) as phenotype, 
    IF(ANY_VALUE(g.BioSample_ID) is null, false, true) as genotype
FROM uniq_geno_ass g
LEFT JOIN assembly p on (p.BioSample_ID = g.BioSample_ID and p.assembly_ID = g.assembly_ID)
WHERE p.BioSample_ID IS NULL
group by g.BioSample_ID, g.assembly_ID, g.genus, g.species
"""
    )

    columns = ["BioSample_ID", "genus", "species", "organism", "phenotype", "genotype"]
    for col in columns:
        print(f" > Setting column {col} as NOT NULL")
        con.execute(f"ALTER TABLE assembly ALTER COLUMN {col} SET NOT NULL")
    rows = con.execute("SELECT COUNT(*) FROM assembly").fetchone()[0]
    print(f"Created the assembly table with {rows} row(s)")
    con.commit()


def write_to_disk(con, args):
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = ["phenotype", "genotype"]
    if args.write_assembly:
        tables.append("assembly")
    print("Writing fixed tables to disk")
    for t in tables:
        path = output_dir / f"{t}.parquet"
        print(f" > Writing the table {t} out to {path}")
        query = f"""
COPY
    (SELECT * FROM {t})
    TO '{path}'
    (FORMAT parquet, COMPRESSION zstd)
"""
        con.execute(query)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Apply post fixes to a AMR genotype and phenotype parquet files"
    )
    parser.add_argument(
        "--genotype",
        type=Path,
        required=True,
        help="Path or URL to the input genotype Parquet file.",
    )
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Path or URL to the input phenotype Parquet file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write final outputs to",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        help="Do not write to disk any results",
    )
    parser.add_argument(
        "--write-assembly",
        action=argparse.BooleanOptionalAction,
        help="Create and write the final joined assembly table. No longer done by default",
    )
    parser.add_argument(
        "--antibiotic-lookup",
        type=Path,
        required=True,
        help="CSV of additional antibiotic lookups. Not to be confused with the offline index of antibiotics (correct file is called fix-antibiotics.csv)",
    )
    parser.add_argument(
        "--filter-genomes",
        type=Path,
        required=False,
        help="File of Assembly IDs to remove from a genotype file",
    )
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    with duckdb.connect() as con:
        load_duckdb(con, args)
        update_phenotype(con)
        update_genotype(con)
        if args.filter_genomes:
            filter_genomes(con)
        if args.write_assembly:
            create_assembly(con)
        else:
            print("Skipping creating the assembly table")
        if not args.dry_run:
            write_to_disk(con, args)
        else:
            print(f"Not writing files to disk as --dry-run is on")
    print(f"✅ Script finished")


if __name__ == "__main__":
    main()
