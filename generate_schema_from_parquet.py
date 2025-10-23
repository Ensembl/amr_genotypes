#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import pyarrow.parquet as pq
import fsspec
from src.utils import open_file


def open_parquet_table(path_or_url: str):
    with fsspec.open(path_or_url, mode="rb") as f:
        return pq.read_table(f)


def schema_to_dict(schema):
    return {
        "schema": [
            {"name": f.name, "type": str(f.type), "nullable": f.nullable}
            for f in schema
        ]
    }


def write_schema(schema_dict, output_file: Path):
    with open_file(file_path=output_file, mode="wt") as f:
        json.dump(schema_dict, f, indent=2)
    print(f"✅ Schema written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a schema JSON file from a Parquet file (supports HTTP, S3, etc.)."
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Path or URL to the Parquet file."
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Output JSON schema file."
    )
    args = parser.parse_args()

    print(f"Reading schema from: {args.input}")
    table = open_parquet_table(args.input)

    schema_dict = schema_to_dict(table.schema)

    print("Detected schema:")
    for field in table.schema:
        print(f"  - {field.name}: {field.type} (Nullable: {field.nullable})")

    write_schema(schema_dict, args.output)


if __name__ == "__main__":
    main()
