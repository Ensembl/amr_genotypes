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
