#!/usr/bin/env python3

import argparse
from pathlib import Path
import duckdb
from src.lookup import Lookup


def load_duckdb(con, args) -> None:
    print(f"Loading parquet with {args.genotype} and {args.phenotype}")
    con.execute(
        "create table genotype as select * from read_parquet(?)", [str(args.genotype)]
    )
    con.execute(
        "create table phenotype as select * from read_parquet(?)", [str(args.phenotype)]
    )


def generate_unique_antibiotics(con) -> None:
    print("Generating unique antibiotics from genotype and phenotype")
    con.execute(
        """
CREATE TABLE antibiotics AS 
SELECT DISTINCT * FROM (
    SELECT DISTINCT 
        antibiotic_name, 
        antibiotic_ontology, 
        concat('http://purl.obolibrary.org/obo/', antibiotic_ontology) as iri,
        '' AS antibiotic_group_term,
        '' AS antibiotic_group_label
    FROM phenotype 
    WHERE antibiotic_ontology IS NOT NULL
    UNION 
    SELECT DISTINCT 
        antibiotic_name, 
        antibiotic_ontology, 
        concat('http://purl.obolibrary.org/obo/', antibiotic_ontology) as iri,
        '' AS antibiotic_group_term,
        '' AS antibiotic_group_label
    FROM genotype 
    WHERE antibiotic_ontology IS NOT NULL
)
"""
    )


def find_groups(con) -> None:
    print("Finding antibiotic groups from ontology IRIs")
    unique = con.execute(
        """SELECT antibiotic_name, antibiotic_ontology, iri FROM antibiotics"""
    ).fetchall()
    for row in unique:
        antibiotic_name = row[0]
        antibiotic_ontology = row[1]
        iri = row[2]
        print(f"  > Processing {antibiotic_name} with IRI {iri}")
        lookup = Lookup()
        group_info = lookup.antibiotic_iri_to_group(iri, ontology="aro")
        if group_info:
            print(f"    >> Found group info: {group_info["label"]}")
            con.execute(
                """
UPDATE antibiotics
SET antibiotic_group_term = ?, antibiotic_group_label = ?
WHERE antibiotic_ontology = ?""",
                [group_info["short_form"], group_info["label"], antibiotic_ontology],
            )


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate antibiotic groups based on ontology searches"
    )
    parser.add_argument(
        "--genotype",
        type=Path,
        required=True,
        help="Input genotype parquet file",
    )
    parser.add_argument(
        "--phenotype",
        type=Path,
        required=True,
        help="Input phenotype parquet file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output lookup",
    )
    return parser.parse_args()


def main():
    args = arg_parser()
    with duckdb.connect() as con:
        load_duckdb(con, args)
        generate_unique_antibiotics(con)
        find_groups(con)
        con.commit()
        print(f"Writing output to {args.output}")
        con.execute(
            f"""
COPY (
    SELECT * FROM antibiotics
    ) 
TO '{str(args.output)}' (FORMAT csv)
"""
        )


if __name__ == "__main__":
    main()
