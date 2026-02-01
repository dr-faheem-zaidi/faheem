"""Premium data processing."""

from datetime import date, datetime
from typing import Optional, Tuple
import polars as pl
from glm_data_prep.utils.date_utils import parse_date_column, exposure_years, year_boundaries_for_range
from glm_data_prep.utils.validation import ValidationLog, validate_numeric_column


class PremiumProcessor:
    """Process premium data for GLM analysis."""

    def __init__(
        self,
        study_start: date,
        study_end: date,
        premium_type: str = "Amount",
        accident_year_split: bool = True,
    ):
        """
        Initialize premium processor.

        Args:
            study_start: Study period start date
            study_end: Study period end date
            premium_type: 'Amount' or '% SI'
            accident_year_split: Whether to split policies by accident year
        """
        self.study_start = study_start
        self.study_end = study_end
        self.premium_type = premium_type
        self.accident_year_split = accident_year_split
        self.validation_log = ValidationLog()

    def process(
        self,
        file_path: str,
        uid_col: str,
        product_col: str,
        policy_start_col: str,
        policy_end_col: str,
        premium_col: str,
        sum_insured_col: Optional[str] = None,
        categorical_cols: Optional[list[str]] = None,
        numerical_cols: Optional[list[str]] = None,
        date_format: str = "dmy",
    ) -> Tuple[pl.DataFrame, ValidationLog]:
        """
        Process premium data.

        Args:
            file_path: Path to premium CSV file
            uid_col: UID column name
            product_col: Product column name
            policy_start_col: Policy start date column
            policy_end_col: Policy end date column
            premium_col: Premium amount column
            sum_insured_col: Sum Insured column (if Premium Type = % SI)
            categorical_cols: List of categorical variable columns
            numerical_cols: List of numerical variable columns
            date_format: Date format ('dmy' or 'ymd')

        Returns:
            Tuple of (Premium1 DataFrame, ValidationLog)
        """
        categorical_cols = categorical_cols or []
        numerical_cols = numerical_cols or []

        # Read CSV
        df = pl.read_csv(file_path)
        self.validation_log.set_raw_count(len(df))

        # Select relevant columns
        cols_to_keep = [
            uid_col,
            product_col,
            policy_start_col,
            policy_end_col,
            premium_col,
        ]
        if sum_insured_col:
            cols_to_keep.append(sum_insured_col)
        cols_to_keep.extend(categorical_cols)
        cols_to_keep.extend(numerical_cols)

        df = df.select(cols_to_keep)

        # Parse dates
        df = df.with_columns(
            pl.col(policy_start_col).cast(pl.Utf8),
            pl.col(policy_end_col).cast(pl.Utf8),
        )

        policy_start_series, invalid_start = parse_date_column(
            df[policy_start_col], date_format
        )
        policy_end_series, invalid_end = parse_date_column(
            df[policy_end_col], date_format
        )

        invalid_indices = set(invalid_start) | set(invalid_end)
        if invalid_indices:
            self.validation_log.log_event(
                "date_parsing", len(invalid_indices), "Invalid date format"
            )

        df = df.with_columns(
            pl.lit(policy_start_series).alias("__policy_start"),
            pl.lit(policy_end_series).alias("__policy_end"),
        )

        # Remove rows with invalid dates
        df = df.filter(
            pl.col("__policy_start").is_not_null() & pl.col("__policy_end").is_not_null()
        )

        # Validate policy end >= policy start
        df = df.with_columns(
            (pl.col("__policy_end") >= pl.col("__policy_start")).alias("__valid_dates")
        )
        invalid_date_ranges = (~df["__valid_dates"]).sum()
        if invalid_date_ranges > 0:
            self.validation_log.log_event(
                "date_range", int(invalid_date_ranges), "Policy end < policy start"
            )
        df = df.filter(pl.col("__valid_dates"))

        # Validate premium amounts
        df, invalid_premium = validate_numeric_column(df, premium_col)
        if invalid_premium:
            self.validation_log.log_event(
                "numeric_validation", len(invalid_premium), f"Non-numeric {premium_col}"
            )

        # Convert premium to numeric
        df = df.with_columns(pl.col(premium_col).cast(pl.Float64))

        # Filter by study period
        df = df.filter(
            (pl.col("__policy_end") >= self.study_start)
            & (pl.col("__policy_start") <= self.study_end)
        )

        study_period_removed = self.validation_log.raw_count - len(df) - sum(
            e["count"] for e in self.validation_log.events
        )
        if study_period_removed > 0:
            self.validation_log.log_event(
                "study_period", study_period_removed, "Outside study period"
            )

        # Calculate base exposure (full policy period)
        df = df.with_columns(
            pl.col("__policy_end")
            .sub(pl.col("__policy_start"))
            .map_elements(lambda x: x.days + 1, return_dtype=pl.Int32)
            .truediv(365.25)
            .alias("__base_exposure")
        )

        # Apply study period cutting and calculate earned exposure
        df = df.with_columns(
            pl.col("__policy_start")
            .map_elements(
                lambda x: max(x, self.study_start),
                return_dtype=pl.Date,
            )
            .alias("__effective_start"),
            pl.col("__policy_end")
            .map_elements(
                lambda x: min(x, self.study_end),
                return_dtype=pl.Date,
            )
            .alias("__effective_end"),
        )

        df = df.with_columns(
            pl.col("__effective_end")
            .sub(pl.col("__effective_start"))
            .map_elements(lambda x: x.days + 1, return_dtype=pl.Int32)
            .truediv(365.25)
            .alias("Exposure")
        )

        # Calculate earned premium
        df = df.with_columns(
            (pl.col(premium_col) * pl.col("Exposure") / pl.col("__base_exposure"))
            .alias("EarnPremium")
        )

        # Handle accident year splitting
        if self.accident_year_split:
            df = self._split_by_accident_year(df)
        else:
            # Assign period as year of effective start
            df = df.with_columns(
                pl.col("__effective_start")
                .map_elements(lambda x: x.year, return_dtype=pl.Int32)
                .alias("Period")
            )

        # Rename premium column and drop temporary columns
        df = df.rename({premium_col: "PremiumAmount"})
        if sum_insured_col:
            df = df.rename({sum_insured_col: "SumInsured"})

        # Select final columns
        final_cols = [
            uid_col,
            product_col,
            "PremiumAmount",
            "Exposure",
            "EarnPremium",
            "Period",
        ]
        if sum_insured_col:
            final_cols.append("SumInsured")
        final_cols.extend(categorical_cols)
        final_cols.extend(numerical_cols)

        premium1 = df.select(
            [col for col in final_cols if col in df.columns]
        ).rename({
            uid_col: "UID",
            product_col: "Product",
        })

        self.validation_log.set_final_count(len(premium1))

        return premium1, self.validation_log

    def _split_by_accident_year(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Split policies by accident year boundaries.

        Returns dataframe with one row per policy-period segment.
        """
        rows = []

        for row in df.iter_rows(named=True):
            start = row["__effective_start"]
            end = row["__effective_end"]
            segments = year_boundaries_for_range(start, end)

            for seg_start, seg_end, year in segments:
                seg_exposure = (seg_end - seg_start).days + 1
                seg_exposure /= 365.25

                seg_earned_premium = (
                    row["EarnPremium"]
                    * seg_exposure
                    / row["Exposure"]
                )

                new_row = dict(row)
                new_row["__effective_start"] = seg_start
                new_row["__effective_end"] = seg_end
                new_row["Exposure"] = seg_exposure
                new_row["EarnPremium"] = seg_earned_premium
                new_row["Period"] = year
                rows.append(new_row)

        # Convert back to dataframe
        if rows:
            return pl.DataFrame(rows)
        return df.with_columns(
            pl.col("__effective_start")
            .map_elements(lambda x: x.year, return_dtype=pl.Int32)
            .alias("Period")
        )
