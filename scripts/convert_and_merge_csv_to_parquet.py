#!/usr/bin/env python3

# Add src as a package
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from pathlib import Path
import pyarrow.csv as pv
import pyarrow as pa
import pyarrow.parquet as pq
import logging
from src.schema import load_schema_from_config
from src.config import parquet
import shutil

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def convert_csv_to_parquet(
    input_dir: Path, output_dir: Path, pattern: str, schema: pa.Schema
):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(input_dir.glob(pattern))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {input_dir} matching pattern '{pattern}'"
        )

    log.info(
        f"Found {len(csv_files)} files matching '{pattern}'. Converting to Parquet..."
    )
    convert_opts = pv.ConvertOptions(
        column_types=schema,
        null_values=["", "null", "None", "N/A"],
        true_values=["True", "true", "yes"],
        false_values=["False", "false", "no"],
        strings_can_be_null=True,
    )
    read_opts = pv.ReadOptions(use_threads=True)

    parquet_files = []
    for csv_file in csv_files:
        reader = pv.open_csv(
            csv_file, read_options=read_opts, convert_options=convert_opts
        )
        writer = None
        parquet_path = output_dir / f"{csv_file.stem}.parquet"
        try:
            batch_number = 0
            for batch in reader:
                batch_number += 1
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(
                        parquet_path,
                        schema=table.schema,
                        compression=parquet["compression"],
                        compression_level=parquet["compression_level"],
                    )
                writer.write_table(table)
            if writer is not None:
                parquet_files.append(parquet_path)
                log.info(f"Converted {csv_file.name} → {parquet_path.name}")
            else:
                log.warning(f"CSV file {csv_file.name} contained no rows.")
        finally:
            if writer is not None:
                writer.close()

    return parquet_files


def merge_parquet_files(parquet_files, merged_file: Path):
    log.info(f"Merging {len(parquet_files)} Parquet files into {merged_file}...")
    tables = [pq.read_table(p) for p in parquet_files]
    combined_table = pa.concat_tables(tables, promote_options="default")
    combined_table = combined_table.combine_chunks()
    pq.write_table(
        combined_table,
        merged_file,
        compression=parquet["compression"],
        compression_level=parquet["compression_level"],
    )
    log.info(f"Merged Parquet file saved to: {merged_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV files matching a pattern to Parquet and merge. Will create intermediate parquet files in the specified directory"
    )
    parser.add_argument(
        "--input_dir",
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing the CSV files.",
    )
    parser.add_argument(
        "--output_dir",
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to store the generated Parquet files.",
    )
    parser.add_argument(
        "--merged_file",
        "--merged-file",
        type=Path,
        required=True,
        help="Path (including filename) for the merged Parquet file.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.csv",
        help="Glob pattern to match CSV files (default: '*.csv').",
    )
    parser.add_argument(
        "--schema_file",
        "--schema-file",
        type=Path,
        required=True,
        help="Path to YAML or JSON schema file.",
    )

    args = parser.parse_args()
    schema = load_schema_from_config(args.schema_file)
    parquet_files = convert_csv_to_parquet(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        pattern=args.pattern,
        schema=schema,
    )
    if len(parquet_files) > 1:
        log.info("Merging files")
        merge_parquet_files(parquet_files, args.merged_file)
    else:
        log.info("Only one Parquet file generated. No merge needed")
        if parquet_files[0].samefile(args.merged_file):
            log.info(
                f"The generated Parquet file is already at the desired merged location: {args.merged_file}"
            )
        else:
            log.info(f"Copying {parquet_files[0]} to {args.merged_file}")
            shutil.copyfile(parquet_files[0], args.merged_file)


if __name__ == "__main__":
    main()
