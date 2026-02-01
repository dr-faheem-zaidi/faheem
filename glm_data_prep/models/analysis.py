"""Statistical analysis - one-way, two-way, and aggregation."""

from typing import Dict, List, Optional, Tuple, Any
import polars as pl
import numpy as np


class AnalysisDatasetBuilder:
    """Build aggregated analysis dataset."""

    def __init__(self):
        """Initialize builder."""
        self.analysis_data = None

    def build(
        self,
        consolidated: pl.DataFrame,
        grouping_variables: List[str],
        claim_type: str,
    ) -> pl.DataFrame:
        """
        Build analysis dataset by aggregating consolidated data.

        Args:
            consolidated: Consolidated premium-claims dataframe
            grouping_variables: List of categorical/binned variables to group by
            claim_type: Claim type to filter to

        Returns:
            Aggregated analysis dataframe
        """
        # Filter to claim type
        df = consolidated.filter(pl.col("ClaimType") == claim_type)

        # Group by all variables
        group_cols = grouping_variables
        if "ClaimType" not in group_cols:
            group_cols = group_cols + ["ClaimType"]

        aggregations = {
            "Exposure": "sum",
            "ClaimCount": "sum",
            "ClaimAmount_Capped": "sum",
            "ClaimAmount_LL": "sum",
        }

        # Add Sum Insured if present
        if "SumInsured" in df.columns:
            aggregations["SumInsured"] = "sum"

        self.analysis_data = df.group_by(group_cols).agg(
            [pl.col(col_name).sum().alias(col_name) for col_name in aggregations]
        )

        return self.analysis_data


class OneWayAnalyzer:
    """Perform one-way analysis."""

    def __init__(self, analysis_data: pl.DataFrame, premium_type: str = "Amount"):
        """
        Initialize analyzer.

        Args:
            analysis_data: Aggregated analysis dataset
            premium_type: 'Amount' or '% SI'
        """
        self.analysis_data = analysis_data
        self.premium_type = premium_type

    def analyze(self, variable: str) -> pl.DataFrame:
        """
        Perform one-way analysis on variable.

        Args:
            variable: Variable to analyze

        Returns:
            Analysis results dataframe
        """
        if variable not in self.analysis_data.columns:
            raise ValueError(f"Variable '{variable}' not found in analysis data")

        # Group by variable and aggregate
        results = self.analysis_data.group_by(variable).agg([
            pl.col("Exposure").sum(),
            pl.col("ClaimCount").sum(),
            pl.col("ClaimAmount_Capped").sum(),
        ])

        # Add derived metrics
        results = results.with_columns([
            (pl.col("ClaimCount") / pl.col("Exposure") * 100).alias("Frequency_%"),
            (
                pl.when(pl.col("ClaimCount") > 0)
                .then(pl.col("ClaimAmount_Capped") / pl.col("ClaimCount"))
                .otherwise(0)
                .alias("Severity")
            ),
            (pl.col("ClaimAmount_Capped") / pl.col("Exposure")).alias("BurningCost"),
        ])

        # Add Sum Insured metrics if present
        if "SumInsured" in self.analysis_data.columns:
            results = results.with_columns([
                pl.col("SumInsured").sum(),
                (pl.col("SumInsured") / pl.col("Exposure")).alias("AvgSumInsured"),
                (pl.col("ClaimAmount_Capped") / pl.col("SumInsured") * 100).alias("BurningCost_SI_%"),
            ])

        # Add totals row
        totals = results.select([
            pl.lit("TOTAL").alias(variable),
            pl.col("Exposure").sum(),
            pl.col("ClaimCount").sum(),
            pl.col("ClaimAmount_Capped").sum(),
        ])

        totals = totals.with_columns([
            (pl.col("ClaimCount") / pl.col("Exposure") * 100).alias("Frequency_%"),
            (
                pl.when(pl.col("ClaimCount") > 0)
                .then(pl.col("ClaimAmount_Capped") / pl.col("ClaimCount"))
                .otherwise(0)
                .alias("Severity")
            ),
            (pl.col("ClaimAmount_Capped") / pl.col("Exposure")).alias("BurningCost"),
        ])

        if "SumInsured" in results.columns:
            totals = totals.with_columns([
                pl.col("SumInsured").sum(),
                (pl.col("SumInsured") / pl.col("Exposure")).alias("AvgSumInsured"),
                (pl.col("ClaimAmount_Capped") / pl.col("SumInsured") * 100).alias("BurningCost_SI_%"),
            ])

        # Concatenate results with totals
        results = pl.concat([results, totals])

        return results.sort_by(variable, descending=True)


class TwoWayAnalyzer:
    """Perform two-way analysis with pivot tables."""

    def __init__(self, analysis_data: pl.DataFrame, premium_type: str = "Amount"):
        """
        Initialize analyzer.

        Args:
            analysis_data: Aggregated analysis dataset
            premium_type: 'Amount' or '% SI'
        """
        self.analysis_data = analysis_data
        self.premium_type = premium_type

    def analyze(
        self, variable_rows: str, variable_cols: str, metric: str
    ) -> pl.DataFrame:
        """
        Perform two-way analysis with pivot table.

        Args:
            variable_rows: Variable for rows
            variable_cols: Variable for columns
            metric: Metric to display

        Returns:
            Pivot table as dataframe
        """
        if variable_rows not in self.analysis_data.columns:
            raise ValueError(f"Row variable '{variable_rows}' not found")
        if variable_cols not in self.analysis_data.columns:
            raise ValueError(f"Column variable '{variable_cols}' not found")

        # Group by both variables
        pivot_data = self.analysis_data.group_by([variable_rows, variable_cols]).agg([
            pl.col("Exposure").sum(),
            pl.col("ClaimCount").sum(),
            pl.col("ClaimAmount_Capped").sum(),
        ])

        # Calculate metric for each cell
        if metric == "Exposure":
            pivot_data = pivot_data.select([variable_rows, variable_cols, "Exposure"])
            pivot_values = "Exposure"
        elif metric == "ClaimCount":
            pivot_data = pivot_data.select([variable_rows, variable_cols, "ClaimCount"])
            pivot_values = "ClaimCount"
        elif metric == "ClaimAmount":
            pivot_data = pivot_data.select([variable_rows, variable_cols, "ClaimAmount_Capped"])
            pivot_values = "ClaimAmount_Capped"
        elif metric == "Frequency":
            pivot_data = pivot_data.with_columns(
                (pl.col("ClaimCount") / pl.col("Exposure") * 100).alias("Frequency")
            )
            pivot_data = pivot_data.select([variable_rows, variable_cols, "Frequency"])
            pivot_values = "Frequency"
        elif metric == "Severity":
            pivot_data = pivot_data.with_columns(
                (
                    pl.when(pl.col("ClaimCount") > 0)
                    .then(pl.col("ClaimAmount_Capped") / pl.col("ClaimCount"))
                    .otherwise(0)
                    .alias("Severity")
                )
            )
            pivot_data = pivot_data.select([variable_rows, variable_cols, "Severity"])
            pivot_values = "Severity"
        elif metric == "BurningCost":
            pivot_data = pivot_data.with_columns(
                (pl.col("ClaimAmount_Capped") / pl.col("Exposure")).alias("BurningCost")
            )
            pivot_data = pivot_data.select([variable_rows, variable_cols, "BurningCost"])
            pivot_values = "BurningCost"
        else:
            raise ValueError(f"Unknown metric: {metric}")

        # Pivot the data
        pivot_table = pivot_data.pivot(
            values=pivot_values,
            index=variable_rows,
            columns=variable_cols,
            aggregate_function="sum",
        )

        return pivot_table

    def get_interaction_plot_data(
        self, variable_rows: str, variable_cols: str
    ) -> Dict[str, Any]:
        """
        Get data for interaction effect plot.

        Args:
            variable_rows: Variable for X-axis
            variable_cols: Variable for lines (one per level)

        Returns:
            Dictionary with plot data
        """
        # Group and calculate burning cost
        data = self.analysis_data.group_by([variable_rows, variable_cols]).agg([
            pl.col("Exposure").sum(),
            pl.col("ClaimAmount_Capped").sum(),
        ])

        data = data.with_columns(
            (pl.col("ClaimAmount_Capped") / pl.col("Exposure")).alias("BurningCost")
        )

        # Pivot for plotting
        plot_data = {}
        for row_val in data[variable_rows].unique():
            subset = data.filter(pl.col(variable_rows) == row_val)
            plot_data[str(row_val)] = {
                col_val: bc
                for col_val, bc in zip(
                    subset[variable_cols],
                    subset["BurningCost"],
                )
            }

        return {
            "x_axis": variable_rows,
            "line_axis": variable_cols,
            "data": plot_data,
            "metric": "BurningCost",
        }
