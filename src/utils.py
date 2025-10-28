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


_binFirstShift = 17
_binNextShift = 3
_binOffsetOldToExtended = 4681

# Bin offsets for extended binning
binOffsetsExtended = [
    4096 + 512 + 64 + 8 + 1,
    512 + 64 + 8 + 1,
    64 + 8 + 1,
    8 + 1,
    1,
    0,
]


def bin_from_range_extended(start: int, end: int) -> int:
    """
    Given start,end in chromosome coordinates, assign a bin.

    There's a bin for each:
        - 128k segment
        - 1M segment
        - 8M segment
        - 64M segment
        - 512M segment
        - one top-level bin for up to 4Gb

    Parameters
    ----------
    start : int
        Start coordinate (0-based)
    end : int
        End coordinate (non-inclusive)

    Returns
    -------
    int
        The bin index.

    Raises
    ------
    ValueError
        If start or end are out of range.
    """
    if start < 0 or end <= start:
        raise ValueError(f"Invalid range: start={start}, end={end}")

    start_bin = start >> _binFirstShift
    end_bin = (end - 1) >> _binFirstShift
    for offset in binOffsetsExtended:
        if start_bin == end_bin:
            return _binOffsetOldToExtended + offset + start_bin
        start_bin >>= _binNextShift
        end_bin >>= _binNextShift

    raise ValueError(f"start {start}, end {end} out of range in findBin (max is ~2Gb)")
