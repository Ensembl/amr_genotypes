#!/usr/bin/env python3
"""
join_parquet.py

Script to merge two Parquet datasets (local or HTTPS) using DuckDB and configurable via:
  - Command-line arguments
  - OR a YAML / JSON config file (using --config)

Example 1: Command-line usage
-----------------------------
python join_parquet.py \
    --left data_left.parquet \
    --right https://example.com/data_right.parquet \
    --output merged.parquet \
    --join-type INNER \
    --join-keys BioSample_ID,assembly_ID,antibiotic_ontology \
    --left-cols BioSample_ID,assembly_ID,antibiotic_ontology \
    --right-cols resistance_level

Example 2: YAML config file
---------------------------
config.yaml
------------
left: "data_left.parquet"
right: "data_right.parquet"
output: "merged.parquet"
join_type: "INNER"
join_keys: ["BioSample_ID", "assembly_ID", "antibiotic_ontology"]
left_cols: ["BioSample_ID", "assembly_ID", "antibiotic_ontology"]
right_cols: ["resistance_level"]

Run:
    python join_parquet.py --config config.yaml
"""

import argparse
import json
from pathlib import Path
import duckdb
import pyarrow.parquet as pq

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_config_file(path):
    """Load configuration from YAML or JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("Please install pyyaml to read YAML configs.")
            return yaml.safe_load(f)
        elif path.suffix.lower() == ".json":
            return json.load(f)
        else:
            raise ValueError("Config file must be .yaml, .yml, or .json")


def merge_parquet_duckdb(cfg):
    """Perform the merge using DuckDB."""
    con = duckdb.connect(database=":memory:")

    left = cfg["left"]
    right = cfg["right"]
    output = cfg["output"]
    join_type = cfg.get("join_type", "INNER").upper()
    join_keys = cfg["join_keys"]
    left_cols = cfg["left_cols"]
    right_cols = cfg["right_cols"]
    conditions = cfg["conditions"] if "conditions" in cfg else []

    # Build join condition and select list
    join_condition = " AND ".join([f"l.{k} = r.{k}" for k in join_keys])
    select_keys = ", ".join([f"l.{k}" for k in join_keys])

    left_nonkeys = [c for c in left_cols if c not in join_keys]
    right_nonkeys = [c for c in right_cols if c not in join_keys]

    select_cols = ", ".join(
        [select_keys]
        + [f"l.{c}" for c in left_nonkeys]
        + [f"r.{c}" for c in right_nonkeys]
    )

    where_condition = ""
    if conditions:
        where_condition = "WHERE 1=1"
        for cond in conditions:
            left_key = cond["left_key"]
            condition = cond["condition"]
            where_condition += f" AND l.{left_key} {condition}"

    query = f"""
        SELECT {select_cols}
        FROM read_parquet('{left}') AS l
        {join_type} JOIN read_parquet('{right}') AS r
        ON {join_condition}
        {where_condition}
    """

    print(f"Running {join_type} JOIN on {join_keys}")
    result_reader = con.execute(query).arrow()
    result_table = result_reader.read_all()
    pq.write_table(result_table, output)
    print(f"✅ Merge complete → {output} ({len(result_table)} rows)")


def main():
    parser = argparse.ArgumentParser(
        description="Merge two Parquet files using DuckDB."
    )
    parser.add_argument("--config", help="Path to YAML or JSON config file")
    parser.add_argument("--left", help="Left parquet file or URL")
    parser.add_argument("--right", help="Right parquet file or URL")
    parser.add_argument("--output", help="Output parquet file path")
    parser.add_argument("--join-type", choices=["INNER", "LEFT", "RIGHT", "FULL"])
    parser.add_argument("--join-keys", help="Comma-separated join keys")
    parser.add_argument("--left-cols", help="Comma-separated list of left columns")
    parser.add_argument("--right-cols", help="Comma-separated list of right columns")

    args = parser.parse_args()

    # Load config from file or args
    if args.config:
        cfg = load_config_file(args.config)
    else:
        required = [args.left, args.right, args.output, args.left_cols, args.right_cols]
        if any(v is None for v in required):
            parser.error(
                "Either provide --config or all --left/--right/--output/--*-cols arguments."
            )
        cfg = {
            "left": args.left,
            "right": args.right,
            "output": args.output,
            "join_type": args.join_type or "INNER",
            "join_keys": (
                [c.strip() for c in args.join_keys.split(",")]
                if args.join_keys
                else ["BioSample_ID", "assembly_ID", "antibiotic_ontology"]
            ),
            "left_cols": [c.strip() for c in args.left_cols.split(",")],
            "right_cols": [c.strip() for c in args.right_cols.split(",")],
        }

    merge_parquet_duckdb(cfg)


if __name__ == "__main__":
    main()
