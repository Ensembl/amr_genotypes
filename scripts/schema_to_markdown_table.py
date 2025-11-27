#!/usr/bin/env python3

# Add src as a package
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path
from src.schema import load_schema_from_config, schema_to_markdown_table


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <schema.json>")
        sys.exit(1)

    json_path = sys.argv[1]
    schema = load_schema_from_config(Path(json_path))
    markdown_table = schema_to_markdown_table(schema)
    print(markdown_table)


if __name__ == "__main__":
    main()
