"""Claims data processing."""

from datetime import date
from typing import Optional, Tuple
import polars as pl
from glm_data_prep.utils.date_utils import parse_date_column
from glm_data_prep.utils.validation import ValidationLog, validate_numeric_column


class ClaimsProcessor:
    """Process claims data for GLM analysis."""

    def __init__(self, study_start: date, study_end: date):
        """
        Initialize claims processor.

        Args:
            study_start: Study period start date
            study_end: Study period end date
        """
        self.study_start = study_start
        self.study_end = study_end
        self.validation_log = ValidationLog()

    def process(
        self,
        file_path: str,
        uid_col: str,
        loss_date_col: str,
        claim_type_col: str,
        claim_amount_col: str,
        date_format: str = "dmy",
    ) -> Tuple[pl.DataFrame, ValidationLog]:
        """
        Process claims data.

        Args:
            file_path: Path to claims CSV file
            uid_col: UID column name
            loss_date_col: Loss date column name
            claim_type_col: Claim type column name
            claim_amount_col: Claim amount column name
            date_format: Date format ('dmy' or 'ymd')

        Returns:
            Tuple of (Claims1 DataFrame, ValidationLog)
        """
        # Read CSV
        df = pl.read_csv(file_path)
        self.validation_log.set_raw_count(len(df))

        # Select relevant columns
        cols_to_keep = [uid_col, loss_date_col, claim_type_col, claim_amount_col]
        df = df.select(cols_to_keep)

        # Parse loss dates
        df = df.with_columns(pl.col(loss_date_col).cast(pl.Utf8))
        loss_date_series, invalid_dates = parse_date_column(
            df[loss_date_col], date_format
        )

        if invalid_dates:
            self.validation_log.log_event(
                "date_parsing", len(invalid_dates), "Invalid loss date format"
            )

        df = df.with_columns(
            pl.lit(loss_date_series).alias("__loss_date")
        )

        # Remove rows with invalid dates
        df = df.filter(pl.col("__loss_date").is_not_null())

        # Validate claim amounts
        df, invalid_amounts = validate_numeric_column(df, claim_amount_col)
        if invalid_amounts:
            self.validation_log.log_event(
                "numeric_validation",
                len(invalid_amounts),
                f"Non-numeric {claim_amount_col}",
            )

        # Convert claim amount to numeric
        df = df.with_columns(pl.col(claim_amount_col).cast(pl.Float64))

        # Filter by study period
        initial_count = len(df)
        df = df.filter(
            (pl.col("__loss_date") >= self.study_start)
            & (pl.col("__loss_date") <= self.study_end)
        )

        removed_by_period = initial_count - len(df)
        if removed_by_period > 0:
            self.validation_log.log_event(
                "study_period", removed_by_period, "Outside study period"
            )

        # Assign period as year of loss date and drop old date column
        df = df.with_columns(
            pl.col("__loss_date").dt.year().alias("Period")
        ).drop(loss_date_col)

        # Rename columns
        claims1 = df.rename({
            uid_col: "UID",
            "__loss_date": "LossDate",
            claim_type_col: "ClaimType",
            claim_amount_col: "ClaimAmount",
        }).select([
            "UID",
            "LossDate",
            "ClaimType",
            "ClaimAmount",
            "Period",
        ])

        self.validation_log.set_final_count(len(claims1))

        return claims1, self.validation_log
