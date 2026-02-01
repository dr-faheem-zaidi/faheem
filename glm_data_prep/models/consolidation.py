"""Data consolidation - joining premium and claims."""

from typing import Optional, Tuple, List
from datetime import date
import polars as pl


class DataConsolidator:
    """Consolidate premium and claims data."""

    def __init__(self, accident_year_split: bool = True):
        """
        Initialize consolidator.

        Args:
            accident_year_split: Whether data is split by accident year
        """
        self.accident_year_split = accident_year_split
        self.orphan_claims = None

    def consolidate(
        self,
        premium: pl.DataFrame,
        claims: pl.DataFrame,
        products: Optional[List[str]] = None,
        claim_type: Optional[str] = None,
    ) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """
        Consolidate premium and claims data.

        Args:
            premium: Premium1 dataframe
            claims: Claims1 dataframe (with large loss columns)
            products: Optional list of products to filter
            claim_type: Optional claim type to filter

        Returns:
            Tuple of (consolidated_df, orphan_claims_df)
        """
        # Filter premium by products if specified
        premium_filtered = premium
        if products:
            premium_filtered = premium.filter(pl.col("Product").is_in(products))

        # Filter claims by claim type if specified
        claims_filtered = claims
        if claim_type:
            claims_filtered = claims.filter(pl.col("ClaimType") == claim_type)

        # Aggregate claims
        if self.accident_year_split:
            # Group by UID and Period
            claims_agg = claims_filtered.group_by(["UID", "Period"]).agg([
                pl.count().alias("ClaimCount"),
                pl.col("ClaimAmount").sum().alias("ClaimAmount"),
                pl.col("ClaimAmount_Capped").sum().alias("ClaimAmount_Capped"),
                pl.col("ClaimAmount_LL").sum().alias("ClaimAmount_LL"),
            ])
        else:
            # Group by UID only
            claims_agg = claims_filtered.group_by("UID").agg([
                pl.count().alias("ClaimCount"),
                pl.col("ClaimAmount").sum().alias("ClaimAmount"),
                pl.col("ClaimAmount_Capped").sum().alias("ClaimAmount_Capped"),
                pl.col("ClaimAmount_LL").sum().alias("ClaimAmount_LL"),
            ])

        # Left join: premium <- claims
        if self.accident_year_split:
            consolidated = premium_filtered.join(
                claims_agg, on=["UID", "Period"], how="left"
            )
        else:
            consolidated = premium_filtered.join(
                claims_agg, on="UID", how="left"
            )

        # Fill nulls with 0 for claim counts/amounts
        consolidated = consolidated.with_columns([
            pl.col("ClaimCount").fill_null(0),
            pl.col("ClaimAmount").fill_null(0),
            pl.col("ClaimAmount_Capped").fill_null(0),
            pl.col("ClaimAmount_LL").fill_null(0),
        ])

        # Identify orphan claims
        self.orphan_claims = self._identify_orphans(
            claims_filtered, consolidated
        )

        return consolidated, self.orphan_claims

    def _identify_orphans(
        self, claims: pl.DataFrame, consolidated: pl.DataFrame
    ) -> pl.DataFrame:
        """
        Identify claims that cannot be matched to policies.

        Args:
            claims: Original claims dataframe
            consolidated: Consolidated dataframe

        Returns:
            DataFrame with orphan claims and reasons
        """
        # UIDs in consolidated data
        consolidated_uids = set(consolidated["UID"].unique().to_list())

        # Find orphans
        orphans = []

        for row in claims.iter_rows(named=True):
            uid = row["UID"]
            loss_date = row["LossDate"]

            reason = None

            # Check if UID exists in consolidated
            if uid not in consolidated_uids:
                reason = "Policy Not Found"
            else:
                # Check if loss date is within policy period
                # This would require the original policy dates
                # For now, just mark as matched if UID exists
                pass

            if reason:
                orphans.append({
                    "UID": uid,
                    "LossDate": loss_date,
                    "ClaimType": row["ClaimType"],
                    "ClaimAmount": row["ClaimAmount"],
                    "Period": row["Period"],
                    "OrphanReason": reason,
                })

        if orphans:
            return pl.DataFrame(orphans)
        else:
            # Return empty dataframe with correct schema
            return pl.DataFrame(
                {
                    "UID": [],
                    "LossDate": [],
                    "ClaimType": [],
                    "ClaimAmount": [],
                    "Period": [],
                    "OrphanReason": [],
                },
                schema={
                    "UID": pl.Utf8,
                    "LossDate": pl.Date,
                    "ClaimType": pl.Utf8,
                    "ClaimAmount": pl.Float64,
                    "Period": pl.Int32,
                    "OrphanReason": pl.Utf8,
                },
            )

    def get_orphan_summary(self) -> dict:
        """Get summary of orphan claims."""
        if self.orphan_claims is None:
            return {"total": 0, "by_reason": {}}

        total = len(self.orphan_claims)
        by_reason = (
            self.orphan_claims.group_by("OrphanReason")
            .agg(pl.count().alias("count"))
            .to_dicts()
        )

        return {
            "total": total,
            "by_reason": {r["OrphanReason"]: r["count"] for r in by_reason},
        }
