"""GLM model diagnostics and evaluation."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats


class GLMDiagnostics:
    """Calculate diagnostic statistics for GLM models."""

    @staticmethod
    def calculate_gini(
        actual: np.ndarray, predicted: np.ndarray, exposure: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate Gini coefficient for model discrimination.

        Args:
            actual: Actual values (claims, claim counts)
            predicted: Predicted values from model
            exposure: Optional exposure weights

        Returns:
            Gini coefficient (0-1, higher = better discrimination)
        """
        if exposure is not None:
            # Use exposure-weighted rates
            pred_rate = predicted / (exposure + 1e-10)
        else:
            pred_rate = predicted

        # Sort by predicted rate
        sort_idx = np.argsort(pred_rate)
        actual_sorted = actual[sort_idx]
        exposure_sorted = exposure[sort_idx] if exposure is not None else np.ones_like(actual)

        # Cumulative percentages
        cum_exposure = np.cumsum(exposure_sorted) / np.sum(exposure_sorted)
        cum_actual = np.cumsum(actual_sorted) / np.sum(actual_sorted)

        # Area under Lorenz curve (trapezoidal rule)
        auc = np.trapz(cum_actual, cum_exposure)

        # Gini = 2 * AUC - 1 (for symmetric curve around diagonal)
        gini = 2 * auc - 1

        return float(abs(gini))

    @staticmethod
    def calculate_deviance_by_factor(
        data: pd.DataFrame,
        response_var: str,
        factor_var: str,
        formula: str,
        family: str,
        coefficients: Dict[str, float],
        offset: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        Calculate contribution to deviance by factor level.

        Args:
            data: Full dataset
            response_var: Response variable
            factor_var: Factor variable to stratify by
            formula: Model formula
            family: Distribution family
            coefficients: Fitted coefficients
            offset: Offset

        Returns:
            Dictionary mapping factor_level -> deviance_reduction
        """
        import statsmodels.api as sm

        deviance_by_level = {}

        for level in data[factor_var].unique():
            subset = data[data[factor_var] == level]
            y = subset[response_var].values.astype(float)

            # Build design matrix
            X = sm.add_constant(
                subset[
                    [
                        var.strip()
                        for var in formula.split("+")
                        if var.strip() and var.strip() != "1"
                    ]
                ]
            )

            # Get predictions
            eta = X @ np.array([coefficients.get(col, 0) for col in X.columns])
            if offset is not None:
                offset_subset = offset[data[factor_var] == level]
                eta = eta + offset_subset

            mu = np.exp(eta)

            # Calculate deviance
            if family == "poisson":
                deviance = 2 * np.sum(
                    np.where(y > 0, y * np.log(y / (mu + 1e-10)), 0) - (y - mu)
                )
            elif family == "gamma":
                deviance = 2 * np.sum(-np.log(y / (mu + 1e-10)) + (y - mu) / (mu + 1e-10))
            else:
                deviance = 0

            deviance_by_level[str(level)] = float(deviance)

        return deviance_by_level

    @staticmethod
    def calculate_interaction_effect_plot_data(
        data: pd.DataFrame,
        response_var: str,
        var1: str,
        var2: str,
        family: str,
        coefficients: Dict[str, float],
        offset: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Get data for interaction effect plot.

        Args:
            data: Dataset
            response_var: Response variable
            var1: Primary variable (X-axis)
            var2: Secondary variable (lines)
            family: Distribution family
            coefficients: Fitted coefficients
            offset: Offset

        Returns:
            Dictionary with plot data
        """
        import statsmodels.api as sm

        plot_data = {}

        for var2_level in data[var2].unique():
            var2_data = []
            var1_levels = []

            for var1_level in sorted(data[var1].unique()):
                subset = data[
                    (data[var1] == var1_level) & (data[var2] == var2_level)
                ]

                if len(subset) == 0:
                    continue

                y = subset[response_var].values.astype(float)

                # Build design matrix for prediction
                X = sm.add_constant(
                    subset[
                        [
                            var.strip()
                            for var in f"{var1} + {var2}".split("+")
                            if var.strip() and var.strip() != "1"
                        ]
                    ]
                )

                # Get predicted value
                eta = X.iloc[0].values @ np.array(
                    [coefficients.get(col, 0) for col in X.columns]
                )
                if offset is not None:
                    offset_val = offset[data[(data[var1] == var1_level) & (data[var2] == var2_level)].index]
                    if len(offset_val) > 0:
                        eta = eta + offset_val.iloc[0]

                mu = np.exp(eta)

                var1_levels.append(str(var1_level))
                var2_data.append(float(mu))

            plot_data[str(var2_level)] = {
                "x_values": var1_levels,
                "y_values": var2_data,
            }

        return {
            "x_axis": var1,
            "line_axis": var2,
            "data": plot_data,
            "metric": "predicted_rate",
        }

    @staticmethod
    def calculate_vif(X: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate Variance Inflation Factor for multicollinearity check.

        Args:
            X: Design matrix

        Returns:
            Dictionary mapping variable -> VIF
        """
        from statsmodels.stats.outliers_influence import variance_inflation_factor

        vif_data = pd.DataFrame()
        vif_data["variable"] = X.columns
        vif_data["VIF"] = [
            variance_inflation_factor(X.values, i) for i in range(X.shape[1])
        ]

        return dict(zip(vif_data["variable"], vif_data["VIF"]))

    @staticmethod
    def check_separation(
        y: np.ndarray, mu: np.ndarray, threshold: float = 0.99
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check for quasi-complete separation in the data.

        Args:
            y: Actual values
            mu: Predicted values
            threshold: Threshold for separation detection

        Returns:
            Tuple of (has_separation, details)
        """
        # Check for cells with all 0s or all events
        zero_pred = np.sum(mu == 0)
        one_pred = np.sum(mu >= threshold)
        total = len(mu)

        has_separation = (zero_pred > 0 and np.sum(y[mu == 0]) > 0) or (
            one_pred > 0 and np.sum(y[mu >= threshold]) < np.sum(y[mu >= threshold])
        )

        return (
            has_separation,
            {
                "zero_probability_predictions": int(zero_pred),
                "near_one_probability_predictions": int(one_pred),
                "has_events_in_zero_cell": bool(zero_pred > 0 and np.sum(y[mu == 0]) > 0),
            },
        )

    @staticmethod
    def check_overdispersion(
        y: np.ndarray, mu: np.ndarray, family: str = "poisson"
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Check for overdispersion (phi >> 1).

        Args:
            y: Actual values
            mu: Predicted values
            family: Distribution family

        Returns:
            Tuple of (dispersion_parameter, details)
        """
        if family == "poisson":
            # Pearson's chi-square divided by residual df
            residuals = (y - mu) / np.sqrt(mu + 1e-10)
            chi_square = np.sum(residuals**2)
            df = len(y) - 1  # Rough approximation
            phi = chi_square / df

        elif family == "gamma":
            # Shape parameter estimate
            residuals = (y - mu) / mu
            phi = np.sum(residuals**2) / (len(y) - 1)
        else:
            phi = 1.0

        return float(phi), {
            "phi": float(phi),
            "recommendation": "Quasi-Poisson or NB" if phi > 1.5 else "Poisson OK",
        }
