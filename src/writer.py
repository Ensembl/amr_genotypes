from enum import Enum
from typing import Dict, List
from csv import DictWriter
import logging


class AmrWriter:

    log = logging.getLogger(__name__)

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
            if self == AmrWriter.Formats.PARQUET:
                raise ValueError("Parquet format not supported for csv.DictWriter")
            if self == AmrWriter.Formats.TSV:
                return "excel-tab"
            return "excel"

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

    def write_data(self, data=Dict[str, any]) -> None:
        """Writes the given data dictionary to the output file. Any mismatch
        between the columns provided at initialisation and the keys in the data
        dictionary will result in the code failing.

        Args:
            data (Dict[str,any]): A list of dictionaries to write to a file
        """
        if self.format == AmrWriter.Formats.PARQUET:
            import pandas as pd

            df = pd.DataFrame(data, columns=self.columns)
            df.to_parquet(self.filename, index=False)
            return
        else:
            with open(self.filename, "wt") as out:
                writer = DictWriter(
                    out, fieldnames=self.columns, dialect=self.format.dialect()
                )
                writer.writeheader()
                writer.writerows(data)

    def close(self):
        pass
