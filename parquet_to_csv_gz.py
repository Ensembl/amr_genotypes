#!/usr/bin/env python3
import sys
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as csv


def parquet_to_csv(input_path: str, output_path: str):
    """Convert a Parquet file to CSV, gzipping if output ends with .gz."""
    table = pq.read_table(input_path)
    if output_path.endswith(".gz"):
        with pa.OSFile(output_path, "wb") as f:
            with pa.CompressedOutputStream(f, "gzip") as gz:
                csv.write_csv(table, gz)
    else:
        with pa.OSFile(output_path, "wb") as f:
            csv.write_csv(table, f)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.parquet> [output.csv[.gz]]")
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        # Default output name
        output_path = input_path.replace(".parquet", ".csv")

    parquet_to_csv(input_path, output_path)
    print(f"✅ Wrote CSV to: {output_path}")


if __name__ == "__main__":
    main()
