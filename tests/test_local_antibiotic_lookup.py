import pytest
from pathlib import Path
from src.lookup import LocalAntibioticLookup


@pytest.fixture
def test_config():
    return Path(__file__).resolve().parent / "test_data" / "antibiotics.csv"


def test_local_antibiotic_lookup(test_config):
    lookup = LocalAntibioticLookup(path=test_config)
    result = lookup.convert_antibiotic("KANAMYCIN")
    assert result is not None
    assert result["id"] == "ARO:0000049"
    assert result["label"] == "kanamycin A"
    assert result["abbreviation"] == "KAN"

    result = lookup.convert_antibiotic("KANAMYCIN A")
    assert result is not None
    assert result["id"] == "ARO:0000049"
    assert result["label"] == "kanamycin A"
    assert result["abbreviation"] == "KAN"
