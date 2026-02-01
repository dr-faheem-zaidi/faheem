"""Tests for premium data processing."""

import pytest
from datetime import date
from glm_data_prep.models.premium import PremiumProcessor


class TestPremiumProcessing:
    """Test premium data processing."""

    def test_basic_premium_processing(self, sample_premium_csv, study_dates):
        """Test basic premium processing."""
        processor = PremiumProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
            accident_year_split=False,
        )

        result, log = processor.process(
            file_path=sample_premium_csv,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            categorical_cols=["Region"],
            date_format="dmy",
        )

        # Should have processed some records
        assert len(result) > 0
        assert log.raw_count > 0
        assert log.final_count > 0

        # Check required columns
        assert "UID" in result.columns
        assert "Product" in result.columns
        assert "Exposure" in result.columns
        assert "EarnPremium" in result.columns
        assert "Period" in result.columns

    def test_premium_with_accident_year_split(self, sample_premium_csv, study_dates):
        """Test premium processing with accident year splitting."""
        processor = PremiumProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
            accident_year_split=True,
        )

        result, log = processor.process(
            file_path=sample_premium_csv,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            date_format="dmy",
        )

        # With AY split, we might get more records
        assert len(result) > 0
        assert "Period" in result.columns

        # Check that periods are present
        periods = result["Period"].unique().to_list()
        assert len(periods) > 0

    def test_exposure_calculation(self, sample_premium_csv, study_dates):
        """Test that exposure is calculated correctly."""
        processor = PremiumProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
            accident_year_split=False,
        )

        result, _ = processor.process(
            file_path=sample_premium_csv,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            date_format="dmy",
        )

        # All exposure values should be > 0
        assert (result["Exposure"] > 0).all()

        # Exposure should be <= 1 for partial years (within study period)
        assert (result["Exposure"] <= 1.1).all()

    def test_earned_premium_calculation(self, sample_premium_csv, study_dates):
        """Test earned premium calculation."""
        processor = PremiumProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
            accident_year_split=False,
        )

        result, _ = processor.process(
            file_path=sample_premium_csv,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            date_format="dmy",
        )

        # Earned premium should be <= original premium
        premium_col = result["PremiumAmount"]
        earned_col = result["EarnPremium"]

        for prem, earned in zip(premium_col, earned_col):
            assert earned <= prem + 0.01  # Allow small rounding error

    def test_validation_log(self, sample_premium_csv, study_dates):
        """Test validation logging."""
        processor = PremiumProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
        )

        _, log = processor.process(
            file_path=sample_premium_csv,
            uid_col="UID",
            product_col="Product",
            policy_start_col="PolicyStart",
            policy_end_col="PolicyEnd",
            premium_col="Premium",
            date_format="dmy",
        )

        summary = log.summary()
        assert "raw_count" in summary
        assert "final_count" in summary
        assert "records_removed" in summary
        assert "events" in summary

        # Raw count should match CSV records
        assert summary["raw_count"] == 3
