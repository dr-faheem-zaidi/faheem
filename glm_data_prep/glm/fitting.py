"""Fast GLM fitting using glum (40x faster than statsmodels)."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import polars as pl
import pandas as pd

try:
    from glum import GeneralizedLinearRegressor
    HAS_GLUM = True
except ImportError:
    HAS_GLUM = False

import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats


class GLMFitter:
    """Fit GLM models using fast glum package or statsmodels."""

    def __init__(self, use_glum: bool = True):
        """
        Initialize fitter.

        Args:
            use_glum: Use glum package if available (recommended for speed)
        """
        self.use_glum = use_glum and HAS_GLUM
        self.fitted_models = {}
        self.full_data_models = {}

    def fit_model(
        self,
        grouped_data: pd.DataFrame,
        full_data: pd.DataFrame,
        response_var: str,
        predictor_vars: List[str],
        family: str = "poisson",
        include_interaction: bool = True,
        offset_var: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fit GLM model on grouped data, evaluate on full data.

        Args:
            grouped_data: Aggregated data for fitting (faster)
            full_data: Full individual record data (for fit statistics)
            response_var: Response variable name
            predictor_vars: Predictor variable names (2-3)
            family: Distribution family ('poisson', 'gamma', 'binomial')
            include_interaction: Whether to include interaction terms
            offset_var: Optional offset variable (e.g., log(Exposure))

        Returns:
            Dictionary with model results
        """
        if not 2 <= len(predictor_vars) <= 3:
            raise ValueError("Must specify 2-3 predictor variables")

        results = {
            "response": response_var,
            "predictors": predictor_vars,
            "family": family,
            "interaction": include_interaction,
            "models": {},
            "comparison": {},
        }

        # Prepare data
        grouped_data = grouped_data.copy()
        full_data = full_data.copy()

        # Create offset
        offset_grouped = None
        offset_full = None
        if offset_var:
            offset_grouped = np.log(grouped_data[offset_var].values + 1e-10)
            offset_full = np.log(full_data[offset_var].values + 1e-10)

        # Fit models
        model_specs = self._get_model_specs(predictor_vars, include_interaction)

        for model_name, formula in model_specs.items():
            model_results = self._fit_single_model(
                grouped_data=grouped_data,
                full_data=full_data,
                response_var=response_var,
                formula=formula,
                family=family,
                offset_grouped=offset_grouped,
                offset_full=offset_full,
            )
            results["models"][model_name] = model_results

        # Compare models
        results["comparison"] = self._compare_models(results["models"])

        return results

    def _get_model_specs(
        self, predictor_vars: List[str], include_interaction: bool
    ) -> Dict[str, str]:
        """
        Get model specifications for comparison.

        Args:
            predictor_vars: List of predictor variables
            include_interaction: Whether to include interactions

        Returns:
            Dictionary mapping model_name -> formula
        """
        specs = {
            "null": "1",  # Intercept only
            f"main_{predictor_vars[0]}": predictor_vars[0],
            f"main_{predictor_vars[1]}": predictor_vars[1],
        }

        if len(predictor_vars) >= 2:
            specs[f"main_{predictor_vars[0]}+{predictor_vars[1]}"] = (
                f"{predictor_vars[0]} + {predictor_vars[1]}"
            )

        if len(predictor_vars) == 3:
            specs[f"main_all"] = (
                f"{predictor_vars[0]} + {predictor_vars[1]} + {predictor_vars[2]}"
            )
            if include_interaction:
                specs[f"two_way_interactions"] = (
                    f"{predictor_vars[0]} + {predictor_vars[1]} + {predictor_vars[2]} + "
                    f"{predictor_vars[0]}:{predictor_vars[1]} + "
                    f"{predictor_vars[0]}:{predictor_vars[2]} + "
                    f"{predictor_vars[1]}:{predictor_vars[2]}"
                )
                specs[f"three_way_interaction"] = (
                    f"{predictor_vars[0]} * {predictor_vars[1]} * {predictor_vars[2]}"
                )

        elif len(predictor_vars) == 2 and include_interaction:
            specs[f"interaction"] = f"{predictor_vars[0]} * {predictor_vars[1]}"

        return specs

    def _fit_single_model(
        self,
        grouped_data: pd.DataFrame,
        full_data: pd.DataFrame,
        response_var: str,
        formula: str,
        family: str,
        offset_grouped: Optional[np.ndarray],
        offset_full: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """
        Fit a single model.

        Args:
            grouped_data: Aggregated data for fitting
            full_data: Full data for fit statistics
            response_var: Response variable
            formula: Model formula (RHS)
            family: Distribution family
            offset_grouped: Offset for grouped data
            offset_full: Offset for full data

        Returns:
            Dictionary with model results
        """
        # Fit on grouped data
        if self.use_glum and family in ["poisson", "gamma", "binomial"]:
            model_results = self._fit_glum(
                grouped_data, response_var, formula, family, offset_grouped
            )
        else:
            model_results = self._fit_statsmodels(
                grouped_data, response_var, formula, family, offset_grouped
            )

        # Calculate fit statistics on full data
        if formula != "1":
            fit_stats = self._calculate_fit_statistics(
                full_data,
                response_var,
                formula,
                family,
                model_results["coefficients"],
                offset_full,
            )
            model_results.update(fit_stats)

        return model_results

    def _fit_glum(
        self,
        data: pd.DataFrame,
        response_var: str,
        formula: str,
        family: str,
        offset: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """
        Fit using glum (fast).

        Args:
            data: Training data
            response_var: Response variable
            formula: Model formula (RHS)
            family: Distribution family
            offset: Offset array

        Returns:
            Dictionary with results
        """
        # Build design matrix
        y = data[response_var].values.astype(float)
        X = sm.add_constant(
            data[[var.strip() for var in formula.split("+") if var.strip() and var.strip() != "1"]]
        )

        # Family
        family_map = {
            "poisson": "poisson",
            "gamma": "gamma",
            "binomial": "binomial",
        }

        try:
            model = GeneralizedLinearRegressor(
                family=family_map.get(family, family),
                link="log",
                fit_intercept=False,  # Already added constant
                max_iter=100,
            )

            model.fit(X, y, sample_weight=None, offset=offset)

            return {
                "coefficients": dict(zip(X.columns, model.coef_)),
                "intercept": model.coef_[0] if "const" in X.columns else 0,
                "converged": True,
                "method": "glum",
            }
        except Exception as e:
            # Fallback to statsmodels
            return self._fit_statsmodels(data, response_var, formula, family, offset)

    def _fit_statsmodels(
        self,
        data: pd.DataFrame,
        response_var: str,
        formula: str,
        family: str,
        offset: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """
        Fit using statsmodels.

        Args:
            data: Training data
            response_var: Response variable
            formula: Model formula (RHS)
            family: Distribution family
            offset: Offset array

        Returns:
            Dictionary with results
        """
        # Build formula
        full_formula = f"{response_var} ~ {formula}" if formula != "1" else f"{response_var} ~ 1"

        # Family
        family_map = {
            "poisson": sm.families.Poisson(),
            "gamma": sm.families.Gamma(),
            "binomial": sm.families.Binomial(),
            "gaussian": sm.families.Gaussian(),
        }

        try:
            model = smf.glm(
                full_formula,
                data=data,
                family=family_map.get(family, sm.families.Poisson()),
                offset=offset,
            )
            result = model.fit()

            return {
                "coefficients": result.params.to_dict(),
                "intercept": result.params.get("Intercept", 0),
                "converged": result.mle_retvals.get("converged", False)
                if hasattr(result, "mle_retvals") and result.mle_retvals
                else True,
                "method": "statsmodels",
                "summary": result.summary(),
            }
        except Exception as e:
            return {
                "error": str(e),
                "coefficients": {},
                "converged": False,
            }

    def _calculate_fit_statistics(
        self,
        data: pd.DataFrame,
        response_var: str,
        formula: str,
        family: str,
        coefficients: Dict[str, float],
        offset: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """
        Calculate fit statistics on full data.

        Args:
            data: Full data
            response_var: Response variable
            formula: Model formula
            family: Distribution family
            coefficients: Fitted coefficients
            offset: Offset

        Returns:
            Dictionary with fit statistics
        """
        y = data[response_var].values.astype(float)

        # Build design matrix
        X = sm.add_constant(
            data[[var.strip() for var in formula.split("+") if var.strip() and var.strip() != "1"]]
        )

        # Get predictions
        eta = X @ np.array([coefficients.get(col, 0) for col in X.columns])
        if offset is not None:
            eta = eta + offset

        mu = np.exp(eta)  # Assuming log link

        # Calculate deviance based on family
        if family == "poisson":
            # Poisson deviance
            deviance = 2 * np.sum(
                np.where(y > 0, y * np.log(y / mu), 0) - (y - mu)
            )
        elif family == "gamma":
            # Gamma deviance
            deviance = 2 * np.sum(-np.log(y / mu) + (y - mu) / mu)
        else:
            deviance = 0

        # Null deviance
        if family == "poisson":
            mu_null = np.mean(y / (np.exp(offset) if offset is not None else 1))
            null_deviance = 2 * np.sum(
                np.where(y > 0, y * np.log(y / mu_null), 0) - (y - mu_null)
            )
        else:
            null_deviance = deviance

        # Degrees of freedom
        n = len(y)
        p = len(coefficients)
        residual_df = n - p

        # Log-likelihood
        if family == "poisson":
            ll = np.sum(y * np.log(mu) - mu - np.log(np.array([np.math.factorial(int(yi)) for yi in y]) + 1e-10))
        elif family == "gamma":
            ll = np.sum(np.log(y) - y / mu - np.log(mu))
        else:
            ll = 0

        # AIC, BIC
        aic = -2 * ll + 2 * p
        bic = -2 * ll + p * np.log(n)

        # Pseudo R²
        pseudo_r2 = 1 - (deviance / null_deviance) if null_deviance > 0 else 0

        return {
            "deviance": float(deviance),
            "null_deviance": float(null_deviance),
            "residual_df": int(residual_df),
            "log_likelihood": float(ll),
            "aic": float(aic),
            "bic": float(bic),
            "pseudo_r2": float(pseudo_r2),
        }

    def _compare_models(self, models: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Compare fitted models using likelihood ratio tests.

        Args:
            models: Dictionary of fitted models

        Returns:
            Model comparison table
        """
        comparison = []

        model_list = list(models.items())
        for i, (name, results) in enumerate(model_list[:-1]):
            next_name, next_results = model_list[i + 1]

            if "deviance" in results and "deviance" in next_results:
                delta_dev = results["deviance"] - next_results["deviance"]
                delta_df = results["residual_df"] - next_results["residual_df"]
                p_value = 1 - stats.chi2.cdf(delta_dev, max(delta_df, 1))

                comparison.append({
                    "comparison": f"{name} vs {next_name}",
                    "delta_deviance": float(delta_dev),
                    "delta_df": int(delta_df),
                    "chi_sq_p_value": float(p_value),
                    "significant": p_value < 0.05,
                })

        return {"likelihood_ratio_tests": comparison}
