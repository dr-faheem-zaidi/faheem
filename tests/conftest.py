"""Shared test fixtures and utilities."""

import pytest
import tempfile
from datetime import date
from pathlib import Path
import polars as pl


@pytest.fixture
def sample_premium_csv():
    """Create sample premium CSV file."""
    df = pl.DataFrame({
        "UID": ["P001", "P002", "P003"],
        "Product": ["Motor", "Motor", "Fire"],
        "PolicyStart": ["01-01-2022", "15-03-2022", "01-06-2022"],
        "PolicyEnd": ["31-12-2022", "14-03-2023", "31-05-2023"],
        "Premium": [50000, 75000, 30000],
        "Region": ["North", "South", "East"],
    })

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(df.write_csv())
        path = f.name

    yield path

    # Cleanup
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def sample_claims_csv():
    """Create sample claims CSV file."""
    df = pl.DataFrame({
        "UID": ["P001", "P001", "P002", "P003"],
        "LossDate": ["15-06-2022", "20-11-2022", "01-01-2023", "15-02-2023"],
        "ClaimType": ["OD", "Fire", "OD", "Fire"],
        "ClaimAmount": [50000, 100000, 75000, 25000],
    })

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(df.write_csv())
        path = f.name

    yield path

    # Cleanup
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def study_dates():
    """Standard study period dates."""
    return {
        "start": date(2022, 1, 1),
        "end": date(2023, 12, 31),
    }
