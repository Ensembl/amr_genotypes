import gzip
import bz2
import lzma
import brotli
import json
from pathlib import Path
from typing import Any


def open_file(file_path: str | Path, mode: str = "rt"):
    """Opens a file path which can be compressed or uncompressed

    Supports the following extensions and algorithms:

    * .gz - gzip
    * .bz2 - gz2
    * .xz - lzma
    * .br - brotli

    """
    file = Path(file_path)
    if file.suffix == ".gz":
        return gzip.open(file, mode)
    elif file.suffix == ".bz2":
        return bz2.open(file, mode)
    elif file.suffix == ".xz":
        return lzma.open(file, mode)
    elif file.suffix == ".br":
        return brotli.open(file, mode)
    return open(file, mode)


def slurp_file(file_path: str | Path, mode: str = "rt") -> str:
    """Slurp all data into a string from a filepath. Supports all compression modes defined in open_file()"""
    if not file_path.exists():
        raise FileNotFoundError(f"Specified file not found: {file_path}")
    with open_file(file_path=file_path, mode=mode) as fh:
        data = fh.read()
        return data


def slurp_json(file_path: str | Path, mode: str = "rt") -> Any:
    with open_file(file_path=file_path, mode=mode) as fh:
        return json.load(fh)
