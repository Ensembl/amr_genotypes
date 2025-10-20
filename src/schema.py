import pyarrow as pa
from typing import List
from pathlib import Path
from .utils import slurp_json

TYPE_MAP = {
    "string": pa.string(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
    "timestamp[ns]": pa.timestamp("ns"),
}


def load_schema_from_config(schema_file: Path) -> pa.Schema:
    blob = slurp_json(schema_file)
    schema = blob["schema"]
    return schema_from_list(schema)


def schema_from_list(schema: List[dict]) -> pa.Schema:
    fields = []
    for col in schema:
        col_type = TYPE_MAP.get(col["type"].lower())
        # Assume it is not nullable if not specified
        nullable = col.get("nullable", False)
        if col_type is None:
            raise ValueError(f"Unsupported data type: {col['type']}")
        fields.append(pa.field(col["name"], type=col_type, nullable=nullable))

    return pa.schema(fields)
