"""Statistical utilities for analysis."""

from typing import Optional, Dict, List
import polars as pl
import numpy as np


def calculate_percentiles(series: pl.Series, percentiles: List[float]) -> Dict[float, float]:
    """Calculate percentiles for a series."""
    result = {}
    data = series.drop_nulls().to_numpy()
    if len(data) == 0:
        return {p: 0 for p in percentiles}

    for p in percentiles:
        result[p] = float(np.percentile(data, p))
    return result


def calculate_claim_statistics(claims: pl.Series) -> Dict:
    """Calculate comprehensive statistics for claims."""
    data = claims.drop_nulls().to_numpy()

    if len(data) == 0:
        return {
            "count": 0,
            "mean": 0,
            "median": 0,
            "mode": 0,
            "std_dev": 0,
            "min": 0,
            "max": 0,
        }

    percentiles = [10, 20, 30, 40, 50, 60, 70, 80, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 99.5, 99.9]
    percentile_values = calculate_percentiles(claims, percentiles)

    from scipy import stats
    mode_result = stats.mode(data, keepdims=True)

    return {
        "count": int(len(data)),
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "mode": float(mode_result.mode[0]) if len(mode_result.mode) > 0 else 0,
        "std_dev": float(np.std(data)),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "percentiles": percentile_values,
    }


def mean_excess_function(claims: pl.Series, thresholds: Optional[List[float]] = None) -> Dict[float, float]:
    """
    Calculate mean excess function E[X - u | X > u].

    Args:
        claims: Series of claim amounts
        thresholds: Thresholds to evaluate. If None, use percentiles.

    Returns:
        Dictionary mapping threshold to mean excess
    """
    data = claims.drop_nulls().to_numpy()
    data = data[data > 0]  # Only positive claims

    if len(data) == 0:
        return {}

    if thresholds is None:
        thresholds = np.percentile(data, [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99])

    result = {}
    for u in thresholds:
        excess = data[data > u]
        if len(excess) > 0:
            result[float(u)] = float(np.mean(excess - u))
        else:
            result[float(u)] = 0

    return result
