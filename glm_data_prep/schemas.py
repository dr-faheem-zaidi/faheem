"""Pydantic schemas for API requests and responses."""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StudyPeriodConfig(BaseModel):
    """Study period configuration."""

    start_date: date = Field(..., description="Study start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Study end date (YYYY-MM-DD)")
    premium_type: str = Field(
        ..., description="Premium type: 'Amount' or '% SI'", pattern="^(Amount|% SI)$"
    )
    accident_year_split: bool = Field(
        True, description="Whether to split by accident year"
    )


class ColumnMapping(BaseModel):
    """Column mapping for dataset."""

    uid: str = Field(..., description="Unique ID column name")
    date_format: str = Field(
        "dmy", description="Date format: 'dmy' or 'ymd'", pattern="^(dmy|ymd)$"
    )


class PremiumColumnMapping(ColumnMapping):
    """Premium dataset column mapping."""

    product: str = Field(..., description="Product column name")
    policy_start_date: str = Field(..., description="Policy start date column")
    policy_end_date: str = Field(..., description="Policy end date column")
    premium_amount: str = Field(..., description="Premium amount column")
    sum_insured: Optional[str] = Field(None, description="Sum Insured column (required if Premium Type = % SI)")
    categorical_variables: List[str] = Field(
        default_factory=list, description="Categorical rating factor columns"
    )
    numerical_variables: List[str] = Field(
        default_factory=list, description="Continuous variable columns"
    )


class ClaimsColumnMapping(ColumnMapping):
    """Claims dataset column mapping."""

    loss_date: str = Field(..., description="Loss date column name")
    claim_type: str = Field(..., description="Claim type column name")
    claim_amount: str = Field(..., description="Claim amount column name")


class ProcessingResponse(BaseModel):
    """Response for data processing."""

    success: bool
    record_count: int
    validation_log: Dict[str, Any]
    data_summary: Dict[str, Any]


class CategoricalGrouping(BaseModel):
    """Categorical grouping rule."""

    new_label: str = Field(..., description="New grouped label")
    old_values: List[str] = Field(..., description="Original values to group")


class NumericalBinning(BaseModel):
    """Numerical binning definition."""

    variable: str = Field(..., description="Variable name")
    bins: List[float] = Field(..., description="Bin edges (must be sorted)")
    labels: List[str] = Field(..., description="Labels for each bin")


class LargeLossThreshold(BaseModel):
    """Large loss threshold configuration."""

    claim_type: str = Field(..., description="Claim type to apply threshold to")
    products: List[str] = Field(..., description="Products this applies to")
    apply_threshold: bool = Field(..., description="Whether to apply capping")
    threshold_amount: Optional[float] = Field(
        None, description="Cap amount (required if apply_threshold=True)"
    )


class OneWayAnalysisRequest(BaseModel):
    """One-way analysis request."""

    claim_type: str = Field(..., description="Claim type to analyze")
    variable: str = Field(..., description="Variable to analyze")
    decimal_places: Optional[Dict[str, int]] = Field(
        None, description="Custom decimal places per metric"
    )


class TwoWayAnalysisRequest(BaseModel):
    """Two-way analysis request."""

    claim_type: str = Field(..., description="Claim type to analyze")
    variable_rows: str = Field(..., description="Variable for rows")
    variable_cols: str = Field(..., description="Variable for columns")
    metric: str = Field(
        ...,
        description="Metric to display",
        pattern="^(Exposure|ClaimCount|ClaimAmount|Frequency|Severity|BurningCost|SumInsured|BurningCostSI)$",
    )


class GLMSpecification(BaseModel):
    """GLM model specification."""

    claim_type: str = Field(..., description="Claim type to model")
    response_variable: str = Field(
        ...,
        description="Response variable",
        pattern="^(ClaimCount|ClaimAmount|PurePremium)$",
    )
    variables: List[str] = Field(
        ..., min_items=2, max_items=3, description="Variables for interaction (2-3)"
    )
    interaction_type: str = Field(
        "full", description="'main' for main effects only, 'full' for with interactions"
    )


class GLMResults(BaseModel):
    """GLM model results."""

    claim_type: str
    response_variable: str
    variables: List[str]
    model_comparison: Dict[str, Any]
    coefficients: Dict[str, Any]
    likelihood_ratio_test: Dict[str, Any]
    deviance_by_level: Dict[str, Any]
    gini_comparison: Dict[str, Any]
    success: bool
