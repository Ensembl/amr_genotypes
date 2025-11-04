#!/usr/bin/env python3
"""
stream_parquet_merge.py

Merge multiple Parquet files into a single file
"""

import argparse
import os
import pyarrow.parquet as pq


def recursive_find_files(input_dir):
    # Find all parquet files in the input directory recursively
    parquet_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith(".parquet"):
                parquet_files.append(os.path.join(root, f))
    return parquet_files


def merge_parquet_files(
    output_file, files: list = [], input_dir: str = None, chunk_size=500_000
):
    if not files:
        files = recursive_find_files(input_dir=input_dir)
    # Open first file to get schema
    first_file = files[0]
    pq_file = pq.ParquetFile(first_file)
    schema = pq_file.schema_arrow
    compression = pq_file.metadata.row_group(0).column(0).compression
    print(f"Using schema from {first_file} and compression '{compression}'")

    writer = pq.ParquetWriter(
        output_file, schema, compression=compression, use_dictionary=True
    )

    # Process files sequentially
    for file in files:
        print(f"  > Processing {file}")
        reader = pq.ParquetFile(file)
        for rg_index in range(reader.num_row_groups):
            row_group = reader.read_row_group(rg_index)
            for i in range(0, row_group.num_rows, chunk_size):
                writer.write_table(row_group.slice(i, chunk_size))

    writer.close()
    print(
        f"Merged {len(files)} files into {output_file} using compression '{compression}'"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Stream-merge a list of Parquet files into one, preserving compression."
    )
    parser.add_argument("--files", nargs="+", help="List of Parquet files to merge", required=False)
    parser.add_argument(
        "--input_dir", help="Directory to scan. Not used if you have specified --files", required=False
    )
    parser.add_argument("--output_file", help="Output Parquet file path")
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=500_000,
        help="Rows per row group (default 500k)",
    )

    args = parser.parse_args()
    merge_parquet_files(
        args.output_file,
        files=args.files,
        input_dir=args.input_dir,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
