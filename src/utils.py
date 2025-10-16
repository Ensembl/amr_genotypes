import gzip
from pathlib import Path


def open_file(file_path: str | Path, mode: str = "rt"):
    """Opens a file path which can be compressed or uncompressed"""
    file = Path(file_path)
    if file.suffix == ".gz":
        return gzip.open(file, mode)
    return open(file, mode)


def slurp_file(file_path: str | Path, mode: str = "rt") -> str:
    """Slurp all data into a string from a filepath"""
    with open_file(file_path=file_path, mode=mode) as fh:
        data = fh.read()
        return data
