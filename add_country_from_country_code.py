#!/usr/bin/env python3

import argparse
from pathlib import Path
import duckdb

default_iso_code_column = "ISO_country_code"
default_country_column = "country"
table_name = "input"
country_codes_remote_csv = "https://raw.githubusercontent.com/datasets/country-codes/master/data/country-codes.csv"


def load_duckdb(con, args) -> None:
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")

    if ".csv" in args.input:
        print(f"Loading parquet {args.input}")
        con.execute(
            f"create table {table_name} as select * from read_csv(?, sample_size = -1)",
            [str(args.input)],
        )
    elif ".parquet" in args.input:
        print(f"Loading parquet {args.input}")
        con.execute(
            f"create table {table_name} as select * from read_parquet(?)",
            [str(args.input)],
        )
    else:
        raise ValueError(
            "Provided file does not end in .parquet or .csv or .csv.gz. Not sure how to load"
        )
    print(f"Loading country codes table")
    con.execute(
        "create table country_codes as select * from read_csv(?)",
        [str(args.country_codes)],
    )
    print(f"Loading UNSD table")
    con.execute(
        "create table unsd as select * from read_csv(?, delim = ';', header = true)",
        [str(args.unsd)],
    )
    print(f"Pre-compute names")
    con.execute("ALTER TABLE country_codes ADD COLUMN amr_name VARCHAR")
    con.execute(
        'UPDATE country_codes SET amr_name = coalesce("UNTERM English Short", "CLDR display name")'
    )
    # Remove anything in parentheses from the end of the country name
    con.execute(
        "UPDATE country_codes SET amr_name = regexp_replace(amr_name, '\\s\\(.+?\\)', '')"
    )
    # Remove asterisks and extra spaces
    con.execute(
        "UPDATE country_codes SET amr_name = regexp_replace(amr_name, '\\s\\*+', '')"
    )


def update(con, args) -> None:
    iso_code_column = args.iso_code_column
    print("Updating country names from country codes")
    con.execute(f"ALTER TABLE {table_name} ADD COLUMN country VARCHAR")  # amr_name
    con.execute(
        f"ALTER TABLE {table_name} ADD COLUMN geographical_region VARCHAR"
    )  # Region Name
    con.execute(
        f"ALTER TABLE {table_name} ADD COLUMN geographical_subregion VARCHAR"
    )  # Sub-region Name
    con.execute(
        f"""
UPDATE {table_name} SET
country = cc.amr_name
FROM country_codes cc
WHERE {table_name}.{iso_code_column} = cc."ISO3166-1-Alpha-3"
"""
    )
    con.execute(
        f"""
UPDATE {table_name} SET
geographical_region = un."Region Name",
geographical_subregion = un."Sub-region Name"
FROM unsd un
WHERE {table_name}.{iso_code_column} = un."ISO-alpha3 Code"
"""
    )
    con.commit()
    print(f"Finished updating country names in {table_name} table")

    print("Dropping unwanted columns")
    if args.drop_columns:
        for col in args.drop_columns:
            print(f"  >> Dropping column {col}")
            con.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col}")
    con.commit()


def write_to_disk(con, args):
    path = args.output
    print(f"Writing the table {table_name} out to {path}")
    if ".csv" in str(args.output):
        options = "FORMAT CSV"
    elif ".parquet" in str(args.output):
        options = "FORMAT parquet, COMPRESSION zstd"
    else:
        raise ValueError(
            f"Do not understand the format extension in the file {path}. Try .csv, .csv.gz or .parquet"
        )
    query = f"""
COPY
    (SELECT * FROM {table_name})
    TO '{path}'
    ({options})
"""
    con.execute(query)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Convert a parquet file's country codes to country names"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path or URL to the input Parquet or CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write final outputs to",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        help="Do not write to disk any results",
    )
    parser.add_argument(
        "--country-codes",
        type=str,
        required=False,
        default=country_codes_remote_csv,
        help="CSV of country codes to country names. Taken from https://github.com/datasets/country-codes. Can path directly to the raw CSV on GitHub.",
    )
    parser.add_argument(
        "--unsd",
        type=str,
        required=True,
        help="Secondary lookup of CSV of country codes to country names. Can be obtained from https://unstats.un.org/unsd/methodology/m49/overview/",
    )
    parser.add_argument(
        "--iso-code-column",
        type=str,
        required=False,
        default=default_iso_code_column,
        help="Column which contains the ISO country codes",
    )
    parser.add_argument(
        "--drop-columns",
        type=str,
        nargs="+",
        required=False,
        help="Columns to drop from the output file",
    )
    return parser


def main():
    parser = arg_parser()
    args = parser.parse_args()
    with duckdb.connect() as con:
        load_duckdb(con, args)
        update(con, args)
        if not args.dry_run:
            write_to_disk(con, args)
        else:
            print(f"Not writing files to disk as --dry-run is on")
    print(f"✅ Script finished")


if __name__ == "__main__":
    main()
