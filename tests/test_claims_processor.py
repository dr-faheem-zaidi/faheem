"""Tests for claims data processing."""

import pytest
from datetime import date
from glm_data_prep.models.claims import ClaimsProcessor


class TestClaimsProcessing:
    """Test claims data processing."""

    def test_basic_claims_processing(self, sample_claims_csv, study_dates):
        """Test basic claims processing."""
        processor = ClaimsProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
        )

        result, log = processor.process(
            file_path=sample_claims_csv,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        # Should have processed some records
        assert len(result) > 0
        assert log.raw_count > 0

        # Check required columns
        assert "UID" in result.columns
        assert "LossDate" in result.columns
        assert "ClaimType" in result.columns
        assert "ClaimAmount" in result.columns
        assert "Period" in result.columns

    def test_claims_within_study_period(self, sample_claims_csv, study_dates):
        """Test that claims outside study period are filtered."""
        processor = ClaimsProcessor(
            study_start=date(2023, 1, 1),
            study_end=date(2023, 12, 31),
        )

        result, _ = processor.process(
            file_path=sample_claims_csv,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        # All claims should be in 2023
        periods = result["Period"].unique().to_list()
        assert all(p == 2023 for p in periods)

    def test_period_assignment(self, sample_claims_csv, study_dates):
        """Test that periods are correctly assigned from loss date."""
        processor = ClaimsProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
        )

        result, _ = processor.process(
            file_path=sample_claims_csv,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        # Check that periods match loss dates
        for row in result.iter_rows(named=True):
            loss_year = row["LossDate"].year
            assert row["Period"] == loss_year

    def test_claim_amount_validity(self, sample_claims_csv, study_dates):
        """Test that claim amounts are numeric."""
        processor = ClaimsProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
        )

        result, _ = processor.process(
            file_path=sample_claims_csv,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        # All claim amounts should be positive
        assert (result["ClaimAmount"] > 0).all()

    def test_validation_log(self, sample_claims_csv, study_dates):
        """Test validation logging for claims."""
        processor = ClaimsProcessor(
            study_start=study_dates["start"],
            study_end=study_dates["end"],
        )

        _, log = processor.process(
            file_path=sample_claims_csv,
            uid_col="UID",
            loss_date_col="LossDate",
            claim_type_col="ClaimType",
            claim_amount_col="ClaimAmount",
            date_format="dmy",
        )

        summary = log.summary()
        assert "raw_count" in summary
        assert "final_count" in summary

        # Raw count should match CSV records
        assert summary["raw_count"] == 4
