"""Tests for date utilities."""

import pytest
from datetime import date, datetime
from glm_data_prep.utils.date_utils import (
    exposure_years,
    days_between,
    year_boundaries_for_range,
)


class TestExposureCalculation:
    """Test exposure year calculation."""

    def test_full_year_exposure(self):
        """Test full calendar year exposure."""
        start = date(2022, 1, 1)
        end = date(2022, 12, 31)
        exposure = exposure_years(start, end)
        assert abs(exposure - 1.0) < 0.01

    def test_half_year_exposure(self):
        """Test half-year exposure."""
        start = date(2022, 1, 1)
        end = date(2022, 6, 30)
        exposure = exposure_years(start, end)
        assert abs(exposure - 0.5) < 0.01

    def test_single_day_exposure(self):
        """Test single day exposure."""
        start = date(2022, 1, 1)
        end = date(2022, 1, 1)
        exposure = exposure_years(start, end)
        assert abs(exposure - (1.0 / 365.25)) < 0.001

    def test_days_between(self):
        """Test days between calculation."""
        start = date(2022, 1, 1)
        end = date(2022, 1, 31)
        days = days_between(start, end)
        assert days == 31


class TestYearBoundaries:
    """Test accident year splitting."""

    def test_single_year_policy(self):
        """Test policy within single calendar year."""
        start = date(2022, 3, 15)
        end = date(2022, 8, 20)
        segments = year_boundaries_for_range(start, end)
        assert len(segments) == 1
        assert segments[0][0] == start
        assert segments[0][1] == end
        assert segments[0][2] == 2022

    def test_multi_year_policy(self):
        """Test policy spanning multiple calendar years."""
        start = date(2021, 6, 1)
        end = date(2023, 6, 30)
        segments = year_boundaries_for_range(start, end)
        assert len(segments) == 3

        # First segment: Jun 1, 2021 to Dec 31, 2021
        assert segments[0][0] == date(2021, 6, 1)
        assert segments[0][1] == date(2021, 12, 31)
        assert segments[0][2] == 2021

        # Second segment: Jan 1, 2022 to Dec 31, 2022
        assert segments[1][0] == date(2022, 1, 1)
        assert segments[1][1] == date(2022, 12, 31)
        assert segments[1][2] == 2022

        # Third segment: Jan 1, 2023 to Jun 30, 2023
        assert segments[2][0] == date(2023, 1, 1)
        assert segments[2][1] == date(2023, 6, 30)
        assert segments[2][2] == 2023

    def test_year_boundary_policy(self):
        """Test policy exactly at year boundary."""
        start = date(2022, 1, 1)
        end = date(2022, 12, 31)
        segments = year_boundaries_for_range(start, end)
        assert len(segments) == 1
        assert segments[0][2] == 2022
