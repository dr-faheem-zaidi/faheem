"""GLM Data Preparation Tool for Insurance Actuarial Analysis."""

__version__ = "0.1.0"

from glm_data_prep.models.premium import PremiumProcessor
from glm_data_prep.models.claims import ClaimsProcessor

__all__ = [
    "PremiumProcessor",
    "ClaimsProcessor",
]
