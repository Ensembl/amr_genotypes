# Changelog

All notable changes to `amr_genotypes` are documented in this file.

This project follows [Semantic Versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`), independent of the data portal's own `year_month`
release naming. The mapping between the two is tracked in `RELEASES.md`


# v2.0.0

## ⚠️ Breaking changes

- **Evidence columns replaced.** `evidence_accession`, `evidence_type`, `evidence_link`, and `evidence_description` have been removed from both `genotype.schema.json` and `phenotype_genotype_merged.schema.json`. They are replaced with a richer, AMRFinderPlus-derived set:
  - `amrfinderplus_method`
  - `reference_accession`
  - `reference_name`
  - `reference_sequence_coverage` (decimal)
  - `reference_sequence_identity` (decimal)
  - `HMM_evidence_accession`
  - `HMM_evidence_link`
  - `HMM_evidence_description`

  Any downstream code or queries selecting the old column names will break. Update column references before consuming output produced by this version.

- **New mandatory CLI input: `--annotation-metadata`.** `parse_amr.py` (and `scripts/generate_sbatch.py`, which generates the sbatch jobs that call it) now require a `--annotation-metadata` path pointing to a CSV with columns `assembly_ID, annotation_tool_version, annotation_tool_mode`. Every assembly being processed must have a corresponding row in this file, or the run raises `ValueError` and stops rather than writing partial/incomplete records. Existing invocations that don't pass this flag will fail immediately at argument parsing.

## Added

- **`annotation_tool_version` / `annotation_tool_mode` columns**, sourced from the new annotation metadata CSV (not from GFF attributes) and populated on every output record.
- **Singularity/Apptainer support in `generate_sbatch.py`** via a new `--use-container <path>` flag. When set, generated sbatch scripts invoke each job as `singularity run <image> python3 ...` instead of calling `python3` directly. See the updated "Running inside a Singularity/Apptainer container" section in `PROCESSING.md`.
- **`decimal128` schema type support** in `src/schema.py`, used for the new `reference_sequence_coverage` / `reference_sequence_identity` fields.

## Fixed

- **Ontology lookup precision** (`src/lookup.py`): antibiotic-to-ontology matching now prefers an exact match on the term label, then an exact match against the term's listed exact synonyms, and only falls back to the ontology search API's top-ranked result if neither matches. This avoids picking an entry that merely mentions the drug name in free-text description over a term that's actually an exact match.
- **`post_fixes.py`**: the antibiotic-name backfill query now also matches rows where `antibiotic_name IS NULL`, not just empty string, so previously-missed NULL rows get corrected too.

## Notes for this release

- Only `genotype.schema.json` and `phenotype_genotype_merged.schema.json` change shape — `assembly` output is unaffected.
- If you maintain scripts, notebooks, or DuckDB queries against prior `v1.0.0` output, they will need updating for both the renamed evidence columns and the new mandatory CLI argument before switching to this version.

# v1.0.0

Baseline release: existing code as it stood prior to the changes above.
