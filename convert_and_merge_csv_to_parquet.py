#!/usr/bin/env python3
"""
convert_and_merge_csv_to_parquet.py

Converts a set of CSV files (matching a given pattern) with the same structure
into individual Parquet files, then merges them into a single Parquet file.

Usage:
    python convert_and_merge_csv_to_parquet.py \
        --input_dir ./csv_files \
        --output_dir ./parquet_files \
        --merged_file ./merged_output.parquet \
        --pattern "data_*.csv"
"""

import argparse
from pathlib import Path
import pyarrow.csv as pv
import pyarrow as pa
import pyarrow.parquet as pq
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def convert_csv_to_parquet(input_dir: Path, output_dir: Path, pattern: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(input_dir.glob(pattern))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir} matching pattern '{pattern}'")

    log.info(f"Found {len(csv_files)} files matching '{pattern}'. Converting to Parquet...")

    parquet_files = []
    for csv_file in csv_files:
        table = pv.read_csv(csv_file)
        parquet_path = output_dir / f"{csv_file.stem}.parquet"
        pq.write_table(table, parquet_path)
        parquet_files.append(parquet_path)
        log.info(f"Converted {csv_file.name} -> {parquet_path.name}")

    return parquet_files


def merge_parquet_files(parquet_files, merged_file: Path):
    log.info(f"Merging {len(parquet_files)} Parquet files into {merged_file}...")
    tables = [pq.read_table(p) for p in parquet_files]
    combined_table = pa.concat_tables(tables, promote=True)
    combined_table = combined_table.combine_chunks()
    pq.write_table(combined_table, merged_file)
    log.info(f"Merged Parquet file saved to: {merged_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV files matching a pattern to Parquet and merge."
    )
    parser.add_argument(
        "--input_dir",
        type=Path,
        required=True,
        help="Directory containing the CSV files."
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        required=True,
        help="Directory to store the generated Parquet files."
    )
    parser.add_argument(
        "--merged_file",
        type=Path,
        required=True,
        help="Path (including filename) for the merged Parquet file."
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.csv",
        help="Glob pattern to match CSV files (default: '*.csv')."
    )

    args = parser.parse_args()

    parquet_files = convert_csv_to_parquet(args.input_dir, args.output_dir, args.pattern)
    merge_parquet_files(parquet_files, args.merged_file)


if __name__ == "__main__":
    main()
