# Schemas

## Phenotype Schema

| Field | Type | Description |
| :--- | :--- | :--- |
|`BioSample_ID`| `VARCHAR` | The unique identifier for the biological sample (e.g. SAMEA1028830)|
|`assembly_ID`| `VARCHAR` | The unique accession number for the genome assembly (e.g. GCA_001096525.1) |
|`collection_year`| `INTEGER` | The year the sample was collected|
|`ISO_country_code`| `VARCHAR` | The 3-letter ISO country code where the sample was collected (e.g. THA for Thailand)|
|`host`| `VARCHAR` | The organism the sample was isolated from (e.g. Homo sapiens)|
|`host_age`| `VARCHAR` | The age of the host (empty/NULL in the sample data, but should be a string to allow for various formats or NULLs)|
|`host_sex`| `VARCHAR` | The sex of the host (empty/NULL in the sample data)|
|`INSDC_secondary_accession` | `VARCHAR` | The secondary accession number in the International Nucleotide Sequence Database Collaboration (INSDC)|
|`isolate`| `VARCHAR` | A unique identifier for the specific isolate (e.g. SMRU2695)|
|`isolation_source`| `VARCHAR` | The specific anatomical source or environment the isolate came from (e.g. nasopharynx)|
|`isolation_source_category`| `VARCHAR` | The general category of the isolation source (e.g. respiratory tract)|
|`lat_lon`| `VARCHAR` | Geographic coordinates (latitude and longitude)|
|`genus`| `VARCHAR` | The genus of the organism (e.g. Streptococcus)|
|`organism`| `VARCHAR` | The full name of the organism (e.g. Streptococcus pneumoniae)|
|`pubmed_id`| `INTEGER` | The PubMed ID of the publication associated with the data|
|`Updated_phenotype_CLSI`| `VARCHAR` | The updated antimicrobial susceptibility testing (AST) phenotype based on CLSI standards (empty/NULL in the sample data)|
|`Updated_phenotype_EUCAST`| `VARCHAR` | The updated AST phenotype based on EUCAST standards (empty/NULL in the sample data)|
|`used_ECOFF`| `VARCHAR` | Indicates if the Epidemiological Cut-Off (ECOFF) was used (empty/NULL in the sample data)|
|`testing_standard_year`| `VARCHAR` | The year of the testing standard used (empty/NULL in the sample data)|
|`antibioticName` | `VARCHAR` | The name of the antibiotic tested (e.g. beta-lactams, trimethoprim-sulfamethoxazole)|
|`astStandard`| `VARCHAR` | The standard or guideline used for Antimicrobial Susceptibility Testing (e.g. CLSI, EUCAST)|
|`laboratoryTypingMethod`| `VARCHAR` | The method used to test the antibiotic sensitivity (e.g. disk diffusion, E-test)|
|`measurement`| `FLOAT` | The raw measurement value, typically MIC or zone size (e.g. 2, 1, 0.5) `FLOAT` is used for non-integer numeric values|
|`measurementSign`| `VARCHAR` | The sign indicating the nature of the measurement (e.g. '==' for exact value, or '>', '<')|
|`measurementUnits`| `VARCHAR` | The units for the measurement (e.g. mg/l)|
|`platform`| `VARCHAR` | The platform used for analysis (empty/NULL in the sample data)|
|`resistancePhenotype`| `VARCHAR` | The final result of the interpretation (e.g. susceptible, non-susceptible, resistant)|
|`species`| `VARCHAR` | The species of the organism (e.g. Streptococcus pneumoniae)|
|`antibioticAbbreviation`| `VARCHAR` | A common abbreviation for the antibiotic (e.g. SXT)|
|`antibioticOntology`| `VARCHAR` | An ontology ID for the antibiotic (e.g. ARO_3004024)|

## Genotype Schema

|      Field      |    Type    | Description |
|--------------------------|------------|-------------|
|`BioSample_ID`| `VARCHAR` | The unique identifier for the biological sample (e.g., SAMEA1028830) |
|`assembly_ID`| `VARCHAR` | The unique accession number for the genome assembly (e.g., GCA_001096525.1) |
| `region`                   | `VARCHAR` | Name of a genomic region |
| `region_start`             | `INTEGER`      | Start of the annotated gene |
| `region_end`               | `INTEGER`      | End of the annotated gene |
| `strand`                   | `VARCHAR` | Strand you find the gene on. Can be "+" indicating positive strand or "-" for negative strand |
| `bin`                      | `INTEGER`      | UCSC binning index used to reduce search space for features. See [UCSC's wiki](https://genomewiki.ucsc.edu/index.php/Bin_indexing_system) for further details |
| `id`                       | `VARCHAR` | Identifier of the gene |
| `taxon_id`                 | `INTEGER`      | NCBI Taxonomy identifier of the orgainsm |
|`genus`| `VARCHAR` | The genus of the organism (e.g., Streptococcus) |
| `scientific_name`          | `VARCHAR` | Scientific name of the organism |
|`organism`| `VARCHAR` | The full name of the organism (e.g., Streptococcus pneumoniae) |
| `strain`                   | `VARCHAR` | Strain information|
| `gene_symbol`              | `VARCHAR` | Locus tag identifier |
| `amr_element_symbol`       | `VARCHAR` | AMRFinderPlus symbol including additional point mutation information if available |
| `element_type`             | `VARCHAR` | Broad catagory of AMR element. Normally set to `AMR` |
| `element_subtype`          | `VARCHAR` | Subtype of AMR element. Normally set to `AMR` |
| `class`                    | `VARCHAR` | Overall class of AMR compound as given by AMRFinderPlus. Normally a broad representation of antibiotics |
| `subclass`                 | `VARCHAR` | Specific antibiotic compound as given by AMRFinderPlus. Can also be set to the same as class |
| `antibioticName` | `VARCHAR` | Normalised name of the antibiotic tested (e.g., beta-lactams, trimethoprim-sulfamethoxazole)|
|`antibioticOntology`| `VARCHAR` | An ontology ID for the antibiotic (e.g., ARO_3004024)|
| `antibiotic_ontology_link` | `VARCHAR` | URL for linking to an external resource for the antibiotic compount |
| `evidence_accession`       | `VARCHAR` | Accession for the evidence model used for the assertion |
| `evidence_type`            | `VARCHAR` | Type of model. Normally a hidden Markov model and set to `HMM` |
| `evidence_link`            | `VARCHAR` | Link to target database |
| `evidence_description`     | `VARCHAR` | Description provided of the annotation by AMRFinderPlus |
