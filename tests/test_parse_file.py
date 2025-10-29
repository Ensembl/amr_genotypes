import pytest
from pathlib import Path
from src.processor import Processor
from src.lookup import Lookup, LocalAntibioticLookup


@pytest.fixture
def example_data_dir():
    return Path(__file__).resolve().parent / "test_data"


@pytest.fixture
def antibiotic_lookup_file():
    return Path(__file__).resolve().parent / "test_data" / "antibiotics.csv"


expected = {
    "BioSampleID": "SAMD00060955",
    "assembly_ID": "GCA_000091005.1",
    "species": "Escherichia coli O26:H11 str. 11368",
    "organism": "Escherichia coli O26:H11 str. 11368",
    "genus": "Escherichia",
}


@pytest.mark.vcr()
def test_parse_file(example_data_dir, antibiotic_lookup_file):
    lookup = Lookup()
    local_antibiotic_lookup = LocalAntibioticLookup(antibiotic_lookup_file)
    gff = example_data_dir / "GCA_000091005_annotations.gff"
    processor = Processor.default_processor(
        lookup=lookup,
        gff_path=gff,
        local_antibiotic_lookup=local_antibiotic_lookup,
    )
    output = processor.process()
    assert len(output) == 4
    f = output[-1]
    assert f.get("antibiotic_ontology") == "ARO_0000049"
    assert f.get("BioSample_ID") == "SAMD00060955"
    assert f.get("assembly_ID") == "GCA_000091005.1"
    assert f.get("species") == "Escherichia coli O26:H11 str. 11368"
    assert f.get("organism") == "Escherichia coli O26:H11 str. 11368"
    assert f.get("genus") == "Escherichia"
    assert f.get("region") == "AP010955.1"
    assert f.get("region_start") == 3706
    assert f.get("region_end") == 4521
    assert f.get("strand") == "+"
    assert f.get("class") == "AMINOGLYCOSIDE"
    assert f.get("subclass") == "KANAMYCIN"
    assert f.get("split_subclass") == "KANAMYCIN"
    assert f.get("antibiotic_name") == "kanamycin A"
    assert f.get("antibiotic_abbreviation") == "KAN"
    assert f.get("antibiotic_ontology") == "ARO_0000049"

    assert (
        f.get("antibiotic_ontology_link")
        == "https://www.ebi.ac.uk/ols4/ontologies/aro/classes/http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FARO_0000049"
    )
