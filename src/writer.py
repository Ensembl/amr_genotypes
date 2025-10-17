from enum import Enum
from typing import List
from csv import DictWriter
import logging
import pyarrow as pa
import pyarrow.parquet as pq

from .utils import open_file
from .config import parquet


class Formats(Enum):
    TSV = "tsv"
    CSV = "csv"
    PARQUET = "parquet"

    def dialect(self) -> str:
        """Return the dialect string for csv.DictWriter based on the format enum.

        Raises:
            ValueError: Does not support parquet format

        Returns:
            str: The dialect string for csv.DictWriter
        """
        if self == Formats.PARQUET:
            raise ValueError("Parquet format not supported for csv.DictWriter")
        if self == Formats.TSV:
            return "excel-tab"
        return "excel"


class StreamingAmrWriter:
    log = logging.getLogger(__name__)

    def __init__(
        self, filename: str, columns: List[str], format: Formats = Formats.TSV
    ):
        """Initalises the writer object with the given filename, columns, and format.

        Args:
            filename (str): File to write the data to. If the file exists it will be overwritten.
            columns (List[str]): Columns to write as the header of the file
            format (Formats): Define the format to write. Defaults to Formats.TSV.
        """
        self.filename = filename
        self.format = format
        self.columns = columns
        self._first_write = False
        self._fh = None
        self._writer = None
        self._schema = None

    def __enter__(self):
        if not self._writer:
            self._open()
        return self

    def _open(self):
        # We still delay on enter because we need data to infer a schema
        # before we write
        if self.format == Formats.PARQUET:
            pass
        # CSV we are okay to init
        else:
            self._fh = open_file(self.filename, mode="wt")
            self._writer = DictWriter(
                self._fh, fieldnames=self.columns, dialect=self.format.dialect()
            )
            self._writer.writeheader()

    # No matter what we clos
    def __exit__(self, exc_type, exc_value, traceback):
        if self._fh:
            self._fh.close()
        if exc_type:
            print(f"Exception occurred: {exc_value}")

    def write_data(self, data=List[dict]) -> None:
        """Writes the given data dictionary to the output file. Any mismatch
        between the columns provided at initialisation and the keys in the data
        dictionary will result in the code failing.

        Args:
            data (Dict[str,any]): A list of dictionaries to write to a file
        """
        if self.format == Formats.PARQUET:
            self._write_parquet(data)
        else:
            self._write_csv(data)

    def _write_parquet(self, data) -> None:
        if not self._first_write:
            first_table = pa.Table.from_pylist(data)
            writer = pq.ParquetWriter(
                self.filename,
                first_table.schema,
                compression=parquet["compression"],
                compression_level=parquet["compression_level"],
            )
            self._writer = writer
            self._fh = writer
            self._schema = first_table.schema
            self._first_write = True
            self._writer.write_table(first_table)
        else:
            table = pa.Table.from_pylist(data, self._schema)
            self._writer.write_table(table)

    def _write_csv(self, data) -> None:
        if not self._writer:
            self._open()
        for row in data:
            self._writer.writerow(row)

    def close(self):
        self._fh.close()
