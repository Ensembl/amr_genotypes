# Introduction

The AMR (antimicrobial resistance) Portal is a collaboration between EMBL-EBI research and service teams alongisde Imperial College, London to deliver a new way to access and explore AMR phenotype and genotype annotations through a user-friendly interface. Data within the portal is taken from the MRC project CABBAGE (Comprehensive Assessment of Bacterial-Based AMR prediction from Genotypes) and represents the largest public AMR dataset in a reconciled, uniform format. AMR represents a major growing concern to public health predicted to cause over 2M deaths per year by 2050, with the Global South facing a disproportionate burden of AMR. It increases the risk of untreatable bacteiral infections whilst increasing the chance of complications from essential medical procdures from childbirth to transplants.

## CABBAGE

The Comprehensive Assessment of Bacterial-Based Antimicrobial resistance prediction from GEnotypes (CABBAGE) collects and curates all publicly available data containing both NGS information and AMR information, transforming it into a standard format. During a pilot project researchers collected more than three times as much data as is currently available from the single largest public database. The group's aim is to automate its normalisation processes so that the results of future studies can be directly incorporated into EMBL-EBI resources, and work with stakeholders such as the World Health Organisation to facilitate the adoption of our standards. It is due to the uniformity of these data that the EMBL-EBI teams have been able to create the portal.

## AMR Phenotypes

CABBAGE has catalogued an immensive collection of antibiograms in a standardised format which has been processed by the EMBL-EBI teams to a single consistent large data format. This includes linkage to the [Antibiotic Resistance Ontology (ARO)](https://github.com/arpcard/aro) ontology or [ChEBI (Chemical Entities of Biological Interest) resource](https://www.ebi.ac.uk/chebi/). As part of this work we are brokering these normalised antibiograms back to BioSamples.

## AMR Genotypes

AMR Genotypes are predictions of AMR resistance from computational methods. All annotated genomes have been processed using the mettannotator workflow from EMBL-EBI's MGnify team and generates an exhaustive annotation of prokaryotic genomes using existing tools. Two such tools are [AMRFinderPlus](https://www.ncbi.nlm.nih.gov/pathogens/antimicrobial-resistance/AMRFinder/) from NCBI and [UniProt's UniFire functional annotation system](https://gitlab.ebi.ac.uk/uniprot-public/unifire). Both of which are capable of _in silico_ predictions of resistance based on computational evidence and similarity.

Results from these tools are normalised according to the same rules as our phenotype data.

## EMBL-EBI

The AMR portal is a collaboration between the following EMBL-EBI teams:

- European Nucleotide Archive
- Genomics Technology Infrastructure
- Lees Research
- Microbiome Informatics
- Protein Function Development
- Protein Sequence Resources
- Samples, Phenotypes, and Ontologies

## Future goals

This project represents phase one of our efforts. Future developments may include

- The ability to cross link between our phenotype and genotype data sets
- Expanding AMR profiles to those from isolate genomes in culture collections
- Expanding AMR profiles from text mining the literature
- Submission flows allowing third parties to submit antibiograms and for these data to flow into this portal
- Further standardisation of the antibiogram formats
- Display of isolate genomes in the Ensembl resource including integration of AMR functional annotation
