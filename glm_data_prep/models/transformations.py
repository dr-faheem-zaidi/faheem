"""Variable transformations - grouping and binning."""

from typing import Dict, List, Optional
import polars as pl


class VariableTransformer:
    """Transform categorical and numerical variables."""

    def __init__(self):
        """Initialize transformer."""
        self.categorical_mappings = {}
        self.numerical_bins = {}

    def add_categorical_mapping(
        self,
        variable: str,
        mapping: Dict[str, List[str]],
        handle_unmapped: str = "Other",
    ):
        """
        Add categorical variable grouping.

        Args:
            variable: Variable name
            mapping: Dict mapping new_label -> list of old_values
            handle_unmapped: Label for unmapped values ('Other' or skip)
        """
        self.categorical_mappings[variable] = {
            "mapping": mapping,
            "handle_unmapped": handle_unmapped,
        }

    def add_numerical_binning(
        self,
        variable: str,
        bins: List[float],
        labels: List[str],
    ):
        """
        Add numerical variable binning.

        Args:
            variable: Variable name
            bins: Bin edges (must be sorted)
            labels: Labels for each bin (len = len(bins) - 1)
        """
        if len(labels) != len(bins) - 1:
            raise ValueError(
                f"Number of labels ({len(labels)}) must be one less than bins ({len(bins)})"
            )
        self.numerical_bins[variable] = {
            "bins": bins,
            "labels": labels,
        }

    def apply_transformations(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Apply all transformations to dataframe.

        Args:
            df: Input dataframe

        Returns:
            Transformed dataframe
        """
        result = df.clone()

        # Apply categorical groupings
        for var, config in self.categorical_mappings.items():
            if var in result.columns:
                result = self._apply_categorical_grouping(
                    result, var, config["mapping"], config["handle_unmapped"]
                )

        # Apply numerical binning
        for var, config in self.numerical_bins.items():
            if var in result.columns:
                result = self._apply_numerical_binning(
                    result, var, config["bins"], config["labels"]
                )

        return result

    def _apply_categorical_grouping(
        self,
        df: pl.DataFrame,
        variable: str,
        mapping: Dict[str, List[str]],
        handle_unmapped: str = "Other",
    ) -> pl.DataFrame:
        """
        Apply categorical grouping to variable.

        Args:
            df: Input dataframe
            variable: Variable name
            mapping: Dict mapping new_label -> list of old_values
            handle_unmapped: Label for unmapped values

        Returns:
            Dataframe with new grouped column
        """
        new_col_name = f"{variable}_Grouped"

        # Create mapping from old value to new label
        value_to_label = {}
        for new_label, old_values in mapping.items():
            for old_val in old_values:
                value_to_label[old_val] = new_label

        # Create new column with grouped values
        def map_value(val):
            return value_to_label.get(val, handle_unmapped)

        result = df.with_columns(
            pl.col(variable)
            .map_elements(map_value, return_dtype=pl.Utf8)
            .alias(new_col_name)
        )

        return result

    def _apply_numerical_binning(
        self,
        df: pl.DataFrame,
        variable: str,
        bins: List[float],
        labels: List[str],
    ) -> pl.DataFrame:
        """
        Apply numerical binning to variable.

        Args:
            df: Input dataframe
            variable: Variable name
            bins: Bin edges (sorted)
            labels: Labels for each bin

        Returns:
            Dataframe with new binned column
        """
        new_col_name = f"{variable}_Binned"

        def bin_value(val):
            if val is None:
                return None
            # Find which bin value falls into
            for i, (lower, upper) in enumerate(zip(bins[:-1], bins[1:])):
                if i == len(bins) - 2:  # Last bin is inclusive on right
                    if lower <= val <= upper:
                        return labels[i]
                else:
                    if lower <= val < upper:
                        return labels[i]
            # Value outside all bins
            return None

        result = df.with_columns(
            pl.col(variable)
            .map_elements(bin_value, return_dtype=pl.Utf8)
            .alias(new_col_name)
        )

        return result

    def get_transformation_summary(self) -> Dict:
        """Get summary of applied transformations."""
        return {
            "categorical_groupings": list(self.categorical_mappings.keys()),
            "numerical_binnings": list(self.numerical_bins.keys()),
        }
