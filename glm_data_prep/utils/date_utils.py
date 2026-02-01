"""Date parsing and manipulation utilities."""

from datetime import datetime
from typing import Optional
import polars as pl
from dateutil.parser import parse as dateutil_parse


def parse_date_column(
    column: pl.Series, format: str = "dmy"
) -> tuple[pl.Series, list[int]]:
    """
    Parse date column with specified format.

    Args:
        column: Polars Series containing date strings
        format: Date format - 'dmy' or 'ymd'

    Returns:
        Tuple of (parsed_series, invalid_row_indices)
    """
    invalid_indices = []
    parsed_dates = []

    for idx, value in enumerate(column):
        if value is None or (isinstance(value, float) and value != value):  # NaN check
            invalid_indices.append(idx)
            parsed_dates.append(None)
            continue

        try:
            date_str = str(value).strip()
            if format == "dmy":
                parsed = datetime.strptime(date_str, "%d-%m-%Y")
            elif format == "ymd":
                parsed = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                raise ValueError(f"Unsupported format: {format}")
            parsed_dates.append(parsed.date())
        except (ValueError, AttributeError):
            invalid_indices.append(idx)
            parsed_dates.append(None)

    return pl.Series(column.name or "date", parsed_dates), invalid_indices


def days_between(start_date, end_date) -> int:
    """Calculate days between two dates (inclusive)."""
    return (end_date - start_date).days + 1


def exposure_years(start_date, end_date) -> float:
    """Calculate exposure in policy years."""
    return days_between(start_date, end_date) / 365.25


def year_boundaries_for_range(start_date, end_date) -> list[tuple]:
    """
    Split a date range into calendar year segments.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of (segment_start, segment_end, year) tuples
    """
    segments = []
    current_date = start_date
    current_year = start_date.year

    while current_date <= end_date:
        # Find the last day of current year
        year_end = datetime(current_year, 12, 31).date()
        segment_end = min(year_end, end_date)

        segments.append((current_date, segment_end, current_year))

        # Move to next year
        current_date = datetime(current_year + 1, 1, 1).date()
        current_year += 1

    return segments
