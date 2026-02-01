"""Tests for validation utilities."""

import pytest
import polars as pl
from glm_data_prep.utils.validation import ValidationLog, is_numeric


class TestValidationLog:
    """Test validation logging."""

    def test_validation_log_creation(self):
        """Test creating validation log."""
        log = ValidationLog()
        assert log.raw_count == 0
        assert log.final_count == 0
        assert len(log.events) == 0

    def test_validation_log_events(self):
        """Test logging events."""
        log = ValidationLog()
        log.set_raw_count(1000)
        log.log_event("date_parsing", 50, "Invalid dates")
        log.set_final_count(950)

        summary = log.summary()
        assert summary["raw_count"] == 1000
        assert summary["final_count"] == 950
        assert summary["records_removed"] == 50
        assert len(summary["events"]) == 1

    def test_validation_log_summary_string(self):
        """Test string representation of validation log."""
        log = ValidationLog()
        log.set_raw_count(1000)
        log.log_event("date_parsing", 50, "Invalid dates")
        log.log_event("numeric_validation", 10, "Non-numeric premium")
        log.set_final_count(940)

        summary_str = str(log)
        assert "Validation Summary" in summary_str
        assert "1,000" in summary_str
        assert "940" in summary_str


class TestNumericValidation:
    """Test numeric validation."""

    def test_is_numeric_valid(self):
        """Test numeric validation with valid values."""
        assert is_numeric(100) is True
        assert is_numeric(100.5) is True
        assert is_numeric("100") is True
        assert is_numeric("100.5") is True

    def test_is_numeric_invalid(self):
        """Test numeric validation with invalid values."""
        assert is_numeric("abc") is False
        assert is_numeric(None) is False
        assert is_numeric(float("nan")) is False

    def test_is_numeric_edge_cases(self):
        """Test numeric validation edge cases."""
        assert is_numeric(0) is True
        assert is_numeric(0.0) is True
        assert is_numeric(-100) is True
        assert is_numeric(-100.5) is True
        assert is_numeric("") is False
