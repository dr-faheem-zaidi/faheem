"""Large loss thresholding and analysis."""

from typing import Optional, Dict, List, Tuple
import polars as pl
from glm_data_prep.utils.statistics import calculate_claim_statistics, mean_excess_function


class LargeLossProcessor:
    """Handle large loss thresholding and analysis."""

    def __init__(self):
        """Initialize large loss processor."""
        self.thresholds: Dict[str, Optional[float]] = {}  # claim_type -> threshold
        self.statistics: Dict[str, Dict] = {}  # claim_type -> statistics
        self.mef_results: Dict[str, Dict] = {}  # claim_type -> MEF

    def add_threshold(self, claim_type: str, threshold_amount: Optional[float] = None):
        """
        Add large loss threshold for claim type.

        Args:
            claim_type: Claim type identifier
            threshold_amount: Cap amount (None = no capping)
        """
        self.thresholds[claim_type] = threshold_amount

    def apply_thresholds(self, claims: pl.DataFrame) -> pl.DataFrame:
        """
        Apply large loss thresholds to claims.

        Args:
            claims: Claims1 dataframe

        Returns:
            DataFrame with capping applied
        """
        df = claims.clone()

        # Add columns for capped amounts and excess
        df = df.with_columns([
            pl.lit(0.0).alias("ClaimAmount_Capped"),
            pl.lit(0.0).alias("ClaimAmount_LL"),
        ])

        # Apply thresholds per claim type
        for claim_type, threshold in self.thresholds.items():
            mask = df["ClaimType"] == claim_type

            if threshold is not None:
                # Cap the claim
                capped = pl.when(mask & (df["ClaimAmount"] > threshold))
                    .then(pl.lit(threshold))
                    .otherwise(
                        pl.when(mask).then(df["ClaimAmount"]).otherwise(df["ClaimAmount_Capped"])
                    )
                    .alias("ClaimAmount_Capped")

                # Calculate excess
                excess = pl.when(mask & (df["ClaimAmount"] > threshold))
                    .then(df["ClaimAmount"] - threshold)
                    .otherwise(
                        pl.when(mask).then(pl.lit(0.0)).otherwise(df["ClaimAmount_LL"])
                    )
                    .alias("ClaimAmount_LL")

                df = df.with_columns([capped, excess])
            else:
                # No capping: capped = actual, excess = 0
                df = df.with_columns([
                    pl.when(mask)
                    .then(df["ClaimAmount"])
                    .otherwise(df["ClaimAmount_Capped"])
                    .alias("ClaimAmount_Capped"),
                    pl.when(mask)
                    .then(pl.lit(0.0))
                    .otherwise(df["ClaimAmount_LL"])
                    .alias("ClaimAmount_LL"),
                ])

        return df

    def analyze_claims_by_type(self, claims: pl.DataFrame) -> Dict[str, Dict]:
        """
        Calculate statistics for each claim type.

        Args:
            claims: Claims dataframe (before or after capping)

        Returns:
            Dictionary mapping claim_type to statistics
        """
        results = {}

        for claim_type in claims["ClaimType"].unique():
            type_claims = claims.filter(pl.col("ClaimType") == claim_type)
            claim_amounts = type_claims["ClaimAmount"]

            stats = calculate_claim_statistics(claim_amounts)

            # Calculate mean excess function
            mef = mean_excess_function(claim_amounts)

            results[claim_type] = {
                "count": int(len(type_claims)),
                "statistics": stats,
                "mean_excess_function": mef,
            }

            self.statistics[claim_type] = stats
            self.mef_results[claim_type] = mef

        return results

    def get_distribution_summary(
        self, claims: pl.DataFrame, claim_type: str, bins: int = 20
    ) -> Dict:
        """
        Get distribution summary before and after capping.

        Args:
            claims: Claims dataframe (should have ClaimAmount_Capped column)
            claim_type: Claim type to summarize
            bins: Number of histogram bins

        Returns:
            Dictionary with before/after distribution info
        """
        type_claims = claims.filter(pl.col("ClaimType") == claim_type)

        # Before capping
        before = type_claims["ClaimAmount"].drop_nulls().to_numpy()
        before_hist, before_edges = np.histogram(before, bins=bins)

        # After capping
        after = type_claims["ClaimAmount_Capped"].drop_nulls().to_numpy()
        after_hist, after_edges = np.histogram(after, bins=bins)

        return {
            "before_capping": {
                "histogram": before_hist.tolist(),
                "bin_edges": before_edges.tolist(),
                "mean": float(before.mean()) if len(before) > 0 else 0,
                "median": float(np.median(before)) if len(before) > 0 else 0,
            },
            "after_capping": {
                "histogram": after_hist.tolist(),
                "bin_edges": after_edges.tolist(),
                "mean": float(after.mean()) if len(after) > 0 else 0,
                "median": float(np.median(after)) if len(after) > 0 else 0,
            },
        }


import numpy as np
