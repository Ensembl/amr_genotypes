# Genotype data generation

Genomes from the Comprehensive Assessment of Bacterial-Based AMR prediction from Genotypes (CABBAGE) were annotated with mettannotator providing exhaustive annotation of prokaryotic genomes. AMRFinderPlus and UniFire (the UniProt Functional annotation Inference Rule Engine) are executed on these annotations to provide predictions of AMR.

## Methodology

### Parsing of results

GFF and AMRFinderPlus' output is taken and parsed using our Python tool. We select records related to the class `AMR` and exclude those annotated as `STRESS` or `VIRULENCE`. Records which are supported by a hidden Markov model (HMM) have their accession noted.

## Normalisation

### Antibiotic lookup

Antibiotic records are taken from the `class` and `subclass` output from AMRFinderPlus. Where these output are the same, we indicate this is an annotation at the level of a class of antimicrobial compound. Where they differ we assume this will refer to a specific compound. Where we have records where the `class` is set to a value such as `AMINOGLYCOSIDE` and `subclass` is set to `SPECTINOMYCIN/STREPTOMYCIN` we interpret this as two separate calls on AMR and represent it as two records in our resource.

Each compound is queried against the Ontology Lookup Service first aganinst the Antibiotic Resistance Ontology (ARO) and then against Chemical Entities of Biological Interest (ChEBI) should no record be found. ARO queries are restricted to all children of **ARO:1000003 antibiotic molecule**. ChEBI queries are similar restricted to all children of **CHEBI:33281 antimicrobial agent**. Should no record be found we omit any details.

### Archive identifiers

We ensure records are linked to the following archives

- `assembly_ID`: Genome Collection Accession (GCA) made available from the European Nucleotide Archive and National Center for Biotechnology Information and the International Nucleotide Sequence Database Collection (INSDC)
- `BioSample_ID`: BioSample identifier available from EMBL-EBI and Genbank. BioSample is linked to a genotype record via the GCA and retrieved via the European Bioinformatic Institute's European Bioinformatics Institute's (EMBL-EBI) web API.
- `taxon_id`: Node identifier for the genome in the taxonomic tree

## Additional data information

### Protein identifiers

Protein identifiers are based on the GCA for a genome and autoincremented number starting at `00001`. Identifiers are consistent and unique within a genome.

## References and resources

CABBAGE project: <https://www.pandemicpact.org/grants/P33524>
mettannotator: <https://github.com/EBI-Metagenomics/mettannotator>
AMRFinderPlus: <https://www.ncbi.nlm.nih.gov/pathogens/antimicrobial-resistance/AMRFinder/>
UniFire: <https://gitlab.ebi.ac.uk/uniprot-public/unifire>
ARO: <https://www.ebi.ac.uk/ols4/ontologies/aro>
ChEBI: <https://www.ebi.ac.uk/chebi/>
