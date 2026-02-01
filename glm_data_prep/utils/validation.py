"""Data validation utilities."""

from typing import Any, Optional
import polars as pl


class ValidationLog:
    """Track data validation events."""

    def __init__(self):
        self.events = []
        self.raw_count = 0
        self.final_count = 0

    def set_raw_count(self, count: int):
        """Set initial record count."""
        self.raw_count = count

    def set_final_count(self, count: int):
        """Set final record count."""
        self.final_count = count

    def log_event(self, event_type: str, count: int, description: str):
        """Log a validation event."""
        self.events.append(
            {"type": event_type, "count": count, "description": description}
        )

    def summary(self) -> dict:
        """Get validation summary."""
        return {
            "raw_count": self.raw_count,
            "final_count": self.final_count,
            "records_removed": self.raw_count - self.final_count,
            "events": self.events,
        }

    def __repr__(self):
        lines = [
            f"Validation Summary",
            f"  Raw count: {self.raw_count:,}",
            f"  Final count: {self.final_count:,}",
            f"  Records removed: {self.raw_count - self.final_count:,}",
            "",
            "Details:",
        ]
        for event in self.events:
            lines.append(
                f"  - {event['description']}: {event['count']:,} records"
            )
        return "\n".join(lines)


def is_numeric(value: Any) -> bool:
    """Check if value is numeric."""
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_column_exists(df: pl.DataFrame, col_name: str) -> bool:
    """Check if column exists in dataframe."""
    return col_name in df.columns


def validate_numeric_column(
    df: pl.DataFrame, col_name: str
) -> tuple[pl.DataFrame, list[int]]:
    """
    Validate and filter numeric column.

    Returns:
        Tuple of (filtered_df, removed_row_indices)
    """
    if col_name not in df.columns:
        raise ValueError(f"Column '{col_name}' not found")

    # Create boolean mask for valid numeric values
    col = df[col_name]
    valid_mask = col.is_not_null()

    if col.dtype == pl.String:
        # Try to parse string to numeric
        valid_indices = []
        for i, val in enumerate(col):
            if is_numeric(val):
                valid_indices.append(i)
        valid_mask = pl.Series(
            [i in valid_indices for i in range(len(df))], dtype=pl.Boolean
        )
    elif col.dtype not in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]:
        # Try to cast to numeric
        try:
            col.cast(pl.Float64)
        except Exception:
            valid_mask = pl.Series([False] * len(df), dtype=pl.Boolean)

    removed_indices = [i for i, v in enumerate(valid_mask) if not v]
    filtered_df = df.filter(valid_mask)

    return filtered_df, removed_indices
