#!/usr/bin/env python3

# Add src as a package
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from pathlib import Path
from src.schema import load_schema_from_config
import pyarrow.parquet as pq
import pyarrow.compute as pc


def main():
    parser = argparse.ArgumentParser(
        description="Generate a schema JSON file from a Parquet file (supports HTTP, S3, etc.)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path or URL to the input Parquet file.",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to the output Parquet file"
    )
    parser.add_argument("--schema", type=Path, required=True, help="Path to the schema")
    parser.add_argument(
        "--filter-null",
        type=str,
        required=False,
        help="Create a filter and remove any rows in the specified column which are null. Useful if you are trying to remove any bad rows",
    )
    args = parser.parse_args()

    print(f"Reading schema from: {args.schema}")
    schema = load_schema_from_config(args.schema)

    print(f"Reading parquet: {args.input}")
    table = pq.read_table(args.input)

    if args.filter_null:
        column_name = args.filter_null
        if column_name not in table.column_names:
            raise ValueError(f"Column '{column_name}' not found in Parquet file.")
        mask = pc.invert(pc.is_null(table[column_name]))
        print(f"Filtering rows where {column_name} is null")
        table = table.filter(mask)

    casted_table = table.cast(schema)
    pq.write_table(casted_table, args.output)
    print(f"✅ New Parquet file written: {args.output}")


if __name__ == "__main__":
    main()
