import pytest

from src.processor import Processor


@pytest.mark.parametrize(
    "file,expected",
    [
        ("GCA_002905295.1_annotations.gff.gz", "GCA_002905295.1"),
        ("GCA_002905295.1_annotations.gff", "GCA_002905295.1"),
        ("GCA_002905295_annotations.gff.gz", "GCA_002905295"),
        ("GCA_002905295_annotations.gff", "GCA_002905295"),
        ("ERZ25456556_annotations.gff.gz", "ERZ25456556"),
        ("ERZ25456556_annotations.gff", "ERZ25456556"),
    ],
)
def test_gca_parsing(file, expected):
    parsed = Processor.gff_path_to_assembly(file)
    assert parsed == expected
