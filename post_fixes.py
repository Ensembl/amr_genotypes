#!/usr/bin/env python3

import argparse
from pathlib import Path
import duckdb


def load_duckdb(con, args) -> None:
    print(f"Loading parquet with {args.genotype} and {args.phenotype}")
    con.execute(
        "create table genotype as select * from read_parquet(?)", [str(args.genotype)]
    )
    con.execute(
        "create table phenotype as select * from read_parquet(?)", [str(args.phenotype)]
    )
    con.execute(
        "create table fix_antibiotics as select * from read_csv(?)", [str(args.antibiotic_lookup)]
    )
    antib_fix = con.execute("Select count(*) from fix_antibiotics").fetchone()[0]
    print(f"Found {antib_fix} entries to use for fixing antibiotic naming")


species_names_override = [
    ["Salmonella enterica", "Salmonella enterica subsp. enterica serovar Kentucky"],
    ["Salmonella enterica", "Salmonella enterica subsp. enterica serovar Hadar"],
]
genotype_column_renames = [
    ["strain", "isolate"],
    ["antibioticAbbreviation", "antibiotic_abbreviation"],
    ["antibioticName", "antibiotic_name"],
]


def update_genotype(con) -> None:
    print("Updating genotype species names from phenotype")
    query = """
UPDATE genotype 
SET species = phenotype.species 
FROM phenotype 
WHERE genotype.BioSample_ID = phenotype.BioSample_ID and genotype.assembly_ID = phenotype.assembly_ID;
"""
    con.execute(query)
    for overrides in species_names_override:
        print(f"Applying specific override for {overrides[1]}")
        con.execute("UPDATE genotype SET species =? WHERE species=?", overrides)

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

    print("Fixing missing antibiotics")
    con.execute("""
UPDATE genotype
SET antibioticName = a.label, antibiotic_ontology = replace(a.id, ':', '_'), antibiotic_ontology_link = a.ontology_link
FROM fix_antibiotics a
WHERE genotype.subclass = a.subclass and antibioticName = ''
""")

    print("Creating quick lookup table")
    con.execute("CREATE TABLE antibiotic_abbreviation AS SELECT DISTINCT antibiotic_ontology, antibiotic_abbreviation FROM PHENOTYPE")
    
    print(
        "Updating genotype with known antibioticAbbreviation from phenotype antibiotic_ontology"
    )
    update_antib = """
UPDATE genotype
SET antibioticAbbreviation = IF(aa.antibiotic_abbreviation IS NULL, '', aa.antibiotic_abbreviation)
FROM antibiotic_abbreviation aa
WHERE genotype.antibiotic_ontology = aa.antibiotic_ontology
AND genotype.antibioticAbbreviation = ''
AND genotype.antibiotic_ontology != ''
"""
    con.execute(update_antib)

    for cols in genotype_column_renames:
        print(f"Changing column from genotype.{cols[0]} to genotype.{cols[1]}")
        con.execute(f"ALTER TABLE genotype RENAME {cols[0]} TO {cols[1]}")
    
    con.commit()

def update_phenotype(con) -> None:
    print(f"Updating known BioSample_ID data error in phenotype table")
    affected_ids = [["SAMEA1028830", "8830"]]
    for ids in affected_ids:
        query = "UPDATE phenotype SET BioSample_ID = ? WHERE BioSample_ID = ?"
        con.execute(query, ids)
    con.commit()


def create_assembly(con) -> None:
    print(f"Creating assembly table from phenotype and genotype tables")
    query = """
CREATE TABLE assembly AS 
SELECT DISTINCT 
    p.BioSample_ID, 
    p.assembly_ID, 
    p.genus, 
    p.species, 
    IF(g.organism is null, p.organism, g.organism) as organism, 
    g.isolate,
    g.taxon_id, IF(p.BioSample_ID is null, false, true) as phenotype, 
    IF(g.BioSample_ID is null, false, true) as genotype
FROM phenotype p
LEFT JOIN genotype g on (p.BioSample_ID = g.BioSample_ID and p.assembly_ID = g.assembly_ID)
    """
    con.execute(query)
    columns = ["BioSample_ID", "genus", "species", "organism", "phenotype", "genotype"]
    for col in columns:
        con.execute(f"ALTER TABLE assembly ALTER COLUMN {col} SET NOT NULL")
    rows = con.execute("SELECT COUNT(*) FROM assembly").fetchone()[0]
    print(f"Created the assembly table with {rows} row(s)")
    con.commit()


def write_to_disk(con, args):
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = ["phenotype", "genotype", "assembly"]
    for t in tables:
        path = output_dir / f"{t}.parquet"
        print(f"Writing the table {t} out to {path}")
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
        "--antibiotic-lookup",
        type=Path,
        required=True,
        help="CSV of additional antibiotic lookups",
    )
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    with duckdb.connect() as con:
        load_duckdb(con, args)
        update_phenotype(con)
        update_genotype(con)
        create_assembly(con)
        if not args.dry_run:
            write_to_disk(con, args)
        else:
            print(f"Not writing files to disk as --dry-run is on")
    print(f"✅ Script finished")


if __name__ == "__main__":
    main()
