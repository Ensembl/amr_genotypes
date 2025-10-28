import pytest
from src.utils import bin_from_range_extended


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (0, 128000, 9362),  # single 128k bin = 4681 + 4096 + 512 + 64 + 8 + 1 + 0
        (
            128000,
            256000,
            5266,
        ),  # spans two 128k bins -> next level up = 4681 + 4096 + 512 + 64 + 8 + 1 + 1
        (0, 1000000, 5266),  # same bin level (1M) = 4681 + 512 + 64 + 8 + 1 + 0
        (0, 8000000, 4754),  # 8M bin level = 4681 + 64 + 8 + 1 + 0
        (0, 64000000, 4690),  # 64M bin level = 4681  + 8 + 1 + 0
        (0, 512000000, 4682),  # 512M bin level = 4681 + 1 + 0
        (0, 1000000000, 4681),  # top-level bin = 4681 + 0 + 0
    ],
)
def test_known_bins(start, end, expected):
    """Test known ranges against expected UCSC extended bin assignments."""
    result = bin_from_range_extended(start, end)
    assert result == expected, f"Expected {expected}, got {result}"


def test_single_base():
    """Single-base region should be valid and use the finest bin level."""
    result = bin_from_range_extended(1000, 1001)
    assert isinstance(result, int)
    assert result >= 4681


def test_zero_length_raises():
    """Zero or negative length should raise ValueError."""
    with pytest.raises(ValueError):
        bin_from_range_extended(100, 100)
    with pytest.raises(ValueError):
        bin_from_range_extended(200, 100)


def test_negative_start_raises():
    """Negative start coordinate should raise."""
    with pytest.raises(ValueError):
        bin_from_range_extended(-1, 100)


def test_adjacent_ranges_get_different_bins():
    """Adjacent fine bins can belong to different binning levels."""
    bin1 = bin_from_range_extended(0, 128000)
    bin2 = bin_from_range_extended(128000, 256000)
    assert bin2 != bin1
    assert bin2 < bin1  # promoted to higher level (smaller bin ID)


def test_large_range_collapses_to_top_bin():
    """Huge range should map to top-level bin only."""
    top_bin = bin_from_range_extended(0, 2_000_000_000)
    smaller_bin = bin_from_range_extended(0, 1000)
    assert top_bin < smaller_bin  # higher-level bins have smaller bin numbers
