"""Tests for variable transformations."""

import pytest
import polars as pl
from glm_data_prep.models.transformations import VariableTransformer


class TestCategoricalGrouping:
    """Test categorical variable grouping."""

    def test_simple_grouping(self):
        """Test simple categorical grouping."""
        df = pl.DataFrame({
            "Region": ["North", "South", "East", "West", "North"],
            "Value": [100, 200, 300, 400, 500],
        })

        transformer = VariableTransformer()
        mapping = {
            "Group_1": ["North", "South"],
            "Group_2": ["East", "West"],
        }
        transformer.add_categorical_mapping("Region", mapping)

        result = transformer.apply_transformations(df)

        assert "Region_Grouped" in result.columns
        grouped = result["Region_Grouped"].to_list()
        assert grouped[0] == "Group_1"  # North
        assert grouped[1] == "Group_1"  # South
        assert grouped[2] == "Group_2"  # East
        assert grouped[3] == "Group_2"  # West

    def test_grouping_with_unmapped_values(self):
        """Test grouping with unmapped values."""
        df = pl.DataFrame({
            "Category": ["A", "B", "C", "D"],
            "Value": [1, 2, 3, 4],
        })

        transformer = VariableTransformer()
        mapping = {
            "Mapped": ["A", "B"],
        }
        transformer.add_categorical_mapping("Category", mapping, handle_unmapped="Other")

        result = transformer.apply_transformations(df)

        grouped = result["Category_Grouped"].to_list()
        assert grouped[0] == "Mapped"
        assert grouped[1] == "Mapped"
        assert grouped[2] == "Other"
        assert grouped[3] == "Other"


class TestNumericalBinning:
    """Test numerical variable binning."""

    def test_simple_binning(self):
        """Test simple numerical binning."""
        df = pl.DataFrame({
            "Age": [20, 30, 45, 55, 70],
            "Value": [100, 200, 300, 400, 500],
        })

        transformer = VariableTransformer()
        transformer.add_numerical_binning(
            "Age",
            bins=[0, 30, 50, 100],
            labels=["Young", "Middle", "Senior"],
        )

        result = transformer.apply_transformations(df)

        assert "Age_Binned" in result.columns
        binned = result["Age_Binned"].to_list()
        assert binned[0] == "Young"  # 20
        assert binned[1] == "Young"  # 30 (lower boundary inclusive)
        assert binned[2] == "Middle"  # 45
        assert binned[3] == "Middle"  # 55
        assert binned[4] == "Senior"  # 70

    def test_binning_with_boundary_values(self):
        """Test binning at exact boundaries."""
        df = pl.DataFrame({
            "Value": [0, 25, 50, 75, 100],
        })

        transformer = VariableTransformer()
        transformer.add_numerical_binning(
            "Value",
            bins=[0, 50, 100],
            labels=["Low", "High"],
        )

        result = transformer.apply_transformations(df)
        binned = result["Value_Binned"].to_list()

        assert binned[0] == "Low"  # 0
        assert binned[1] == "Low"  # 25
        assert binned[2] == "High"  # 50 (upper boundary inclusive for last bin)
        assert binned[3] == "High"  # 75
        assert binned[4] == "High"  # 100

    def test_binning_validation(self):
        """Test binning parameter validation."""
        transformer = VariableTransformer()

        with pytest.raises(ValueError):
            # Number of labels doesn't match bins-1
            transformer.add_numerical_binning(
                "Value",
                bins=[0, 50, 100],
                labels=["Low"],  # Should have 2 labels
            )


class TestMultipleTransformations:
    """Test applying multiple transformations together."""

    def test_combined_transformations(self):
        """Test applying categorical and numerical transformations."""
        df = pl.DataFrame({
            "Region": ["North", "South", "East"],
            "Age": [25, 45, 65],
            "Value": [100, 200, 300],
        })

        transformer = VariableTransformer()
        transformer.add_categorical_mapping(
            "Region",
            {"Zone_A": ["North", "South"], "Zone_B": ["East"]},
        )
        transformer.add_numerical_binning(
            "Age",
            bins=[0, 40, 100],
            labels=["Young", "Old"],
        )

        result = transformer.apply_transformations(df)

        assert "Region_Grouped" in result.columns
        assert "Age_Binned" in result.columns
        assert result["Region_Grouped"][0] == "Zone_A"
        assert result["Age_Binned"][0] == "Young"
