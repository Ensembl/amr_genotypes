# Methods

## Antibiotic lookup

Each compound is queried against the Ontology Lookup Service first aganinst the [Antibiotic Resistance Ontology (ARO)][ARO] and then against [Chemical Entities of Biological Interest (ChEBI)][ChEBI] should no record be found. ARO queries are restricted to all children of **[ARO:1000003 antibiotic molecule][aroantib]**. ChEBI queries are similar restricted to all children of **[CHEBI:33281 antimicrobial agent][chebiantib]**. Should no record be found we omit any details.

## Phenotype data generation

Data sets of literature containing values for minimum inhibitory concentrations were curated by the Comprehensive Assessment of Bacterial-Based AMR prediction from Genotypes (CABBAGE) project based at Imperial College London. These data were further harmonised by the Samples, Phenotypes, and Ontologies Team at EMBL-EBI to provide normalisation including:

- Antibiotic names and ontological terminology
- Accessions linking to BioSamples and ENA
- Controlled vocabulary for term restricted fields
- Column naming conventions

Where possible original CABBAGE data has been retained. In addition to this normalisation these records will be brokered back to BioSamples ensuring further persistence of these data beyond the portal.

## Genotype data generation

Genomes from the Comprehensive Assessment of Bacterial-Based AMR prediction from Genotypes (CABBAGE) were annotated with mettannotator providing exhaustive annotation of prokaryotic genomes. AMRFinderPlus and UniFire (the UniProt Functional annotation Inference Rule Engine) are executed on these annotations to provide predictions of AMR.

### Annotation using mettannotator

[mettannotator][mettannotator] is a bioinformatics pipeline that generates an exhaustive annotation of prokaryotic genomes using existing tools. The output is a GFF file that integrates the results of all pipeline components. Results of each individual tool are also provided. Version `3.12.8` of [AMRFinder[AMRFinderPlus]] was used alongside database version `3.12 2024-01-31.1`. Version `2023.4` of [UniFire][UniFire] was used. [v1.4.0 of mettannotator][mettannotatortag] was used by this protal.

### Parsing of results

GFF and AMRFinderPlus' output is taken and parsed using our Python tool. We select records related to the class `AMR` and exclude those annotated as `STRESS` or `VIRULENCE`. Records which are supported by a hidden Markov model (HMM) have their accession noted.

### Normalisation

#### Additional antibiotic processing

Antibiotic records are taken from the `class` and `subclass` output from AMRFinderPlus. Where these output are the same, we indicate this is an annotation at the level of a class of antimicrobial compound. Where they differ we assume this will refer to a specific compound. Where we have records where the `class` is set to a value such as `AMINOGLYCOSIDE` and `subclass` is set to `SPECTINOMYCIN/STREPTOMYCIN` we interpret this as two separate calls on AMR and represent it as two records in our resource. We then use the previously described algorithm to retrieve the ontological term.

#### Archive identifiers

We ensure records are linked to the following archives

- `assembly_ID`: Genome Collection Accession (GCA) or Third Party Annotation (ERZ) made available from the European Nucleotide Archive and National Center for Biotechnology Information and the International Nucleotide Sequence Database Collection (INSDC)
- `BioSample_ID`: BioSample identifier available from EMBL-EBI and Genbank. BioSample is linked to a genotype record via the GCA and retrieved via the European Bioinformatic Institute's European Bioinformatics Institute's (EMBL-EBI) web API.
- `taxon_id`: Node identifier for the genome in the taxonomic tree

## Additional data information

### Protein identifiers

Protein identifiers are based on the GCA for a genome and autoincremented number starting at `00001`. Identifiers are consistent and unique within a genome.

## References and resources

[mettannotator]: <https://github.com/EBI-Metagenomics/mettannotator>
[mettannotatortag]: <https://github.com/EBI-Metagenomics/mettannotator/releases/tag/v1.4.0>
[AMRFinderPlus]: <https://www.ncbi.nlm.nih.gov/pathogens/antimicrobial-resistance/AMRFinder/>
[UniFire]: <https://gitlab.ebi.ac.uk/uniprot-public/unifire>
[ARO]: <https://www.ebi.ac.uk/ols4/ontologies/aro>
[ChEBI]: <https://www.ebi.ac.uk/chebi/>
[aroantib]: <https://www.ebi.ac.uk/ols4/ontologies/aro/classes/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FARO_1000003>
[chebiantib]: <https://www.ebi.ac.uk/ols4/ontologies/chebi/classes/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FCHEBI_33281>
