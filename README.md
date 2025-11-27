# AMR Genotypes parser

A tool for parsing GFFs and TSV files produced by [mettannotator](https://github.com/EBI-Metagenomics/mettannotator) from MGnify. Parses the mettannotator combined GFF file looking for CDS records and lookups up the complementary AMRFinderPlus TSV file for more in-depth results not transferred to the combined GFF file.

## Usage

### Setup

```bash
python -mvenv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running

```bash
python3 parse_amr.py --files path/to/gff.gff
```

Running with `--help` will print all commands available.

### More information

For more information about this step and subsequent consult </PROCESSING.md>

## Outputs

The program will create four output files

- `amr_genotype.csv` a CSV of all records found from parsing the specified GFF files
- `amr_genotype.parquet` parquet representation of the same data
- `assembly.csv` a CSV of all assemblies found and processed from parsing the specified GFF files
- `assembly.parquet` parquet representation of the same assembly data

## Data schemas

The library creates JSON formatted schemas which when processed by `src.schema.load_schema_from_config()` will convert into a pyarrow schema. The schema record has the following fields

- `name` : name of the column
- `type` : data type of the column. We support `string`, `int8`, `int16`, `int32`, `int64`, `float16`, `float32`, `float64`, `bool`, `timestamp[ns]` (supports `s`, `ms`, `us` and `ns`), `duration` (same units as before), `time32[s]` (`s` and `ms`), `time64` (`us` and `ns`), `uuid` and `binary`
- `nullable` : if the column can be nulled
- `description` : description of the field. Will be used to create the markdown table

## Additional tools

The `scripts` directory has a series of additional tools which can be used to further process

- `add_country_from_country_code.py` - For a given parquet file we will add country information from an ISO 3 letter code
- `apply_new_schema_to_parquet.py` - Apply a schema to an existing parquet file
- `convert_and_merge_csv_to_parquet.py` - Take a set of CSV files, convert to parquet and merge
- `generate_sbatch.py` - Generate a sbatch script which will split a list of files into job arrays of specified length for Slurm
- `generate_schema_from_parquet.py` - Take a parquet file and generate a schema JSON file
- `join_parquet.py` - Perform a SQL-like join between parquet data sets
- `lookup_quickly.py` - Lookup antibiotics quickly using the lookup library
- `parquet_to_csv_gz.py` - Convert parquet files to CSV. If you use a `.gz` extension it will compress
- `post_fixes.py` - Run a series of fixes on CABBAGE data. Should always be run until fixes are incorporated upstream
- `schema_to_markdown_table.py` - Take a schema JSON file and create a markdown formatted table
- `stream_merge_parquet.py` - Take multiple parquet files and merge them together

## External dependencies

This tool requires an internet connection to contact the following APIs

- ENA: <https://www.ebi.ac.uk/ena>
- BioSamples: <https://www.ebi.ac.uk/biosamples>
- OLS (Ontology Lookup Service): <https://www.ebi.ac.uk/ols4>

## Testing

There is minimal test suite available for ensuring some of the required parsing is correct.

## Example outputs

Example output files can be found in the `example_data` directory.

## Old code

The original version of this code is held in the `old_code` directory. It is no longer supported.
