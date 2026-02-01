# GLM Data Preparation Tool

A high-performance tool for preparing insurance premium and claims data for Generalized Linear Model (GLM) analysis.

## Features

- **Premium Processing**: Calculate exposures, handle policy cutting, accident year splitting
- **Claims Processing**: Validate and filter claims to study period
- **Large Loss Thresholding**: Cap claims and analyze excess losses
- **Data Consolidation**: Join premium and claims data, identify orphans
- **Variable Transformations**: Categorical grouping and numerical binning
- **Statistical Analysis**:
  - One-way analysis (Frequency, Severity, Burning Cost)
  - Two-way analysis with pivot tables and interaction plots
  - GLM modeling with interaction analysis
  - Deviance reduction analysis and Gini coefficients

## Technology Stack

- **Backend**: Python 3.9+ with Polars (Rust-backed data processing)
- **GLM**: glum (40x faster than statsmodels) and statsmodels
- **API**: FastAPI for high-performance REST endpoints
- **Frontend**: React + TypeScript (planned)

## Performance

- Handles millions of records efficiently
- Polars provides 10-100x speed improvement over pandas
- glum package for optimized GLM fitting

## Installation

```bash
pip install -e .
```

## Usage

### Start API Server

```bash
python -m glm_data_prep.api
```

### Python API

```python
from glm_data_prep import PremiumProcessor, ClaimsProcessor

# Process premium data
processor = PremiumProcessor(
    study_start="2022-01-01",
    study_end="2024-12-31",
    premium_type="Amount",
    accident_year_split=True
)
premium_df = processor.process("premium.csv", date_format="dmy")

# Process claims
claims_processor = ClaimsProcessor(
    study_start="2022-01-01",
    study_end="2024-12-31"
)
claims_df = claims_processor.process("claims.csv", date_format="dmy")
```

## Project Structure

```
glm-data-prep/
├── glm_data_prep/
│   ├── __init__.py
│   ├── api.py                    # FastAPI application
│   ├── models/
│   │   ├── __init__.py
│   │   ├── premium.py            # Premium processing
│   │   ├── claims.py             # Claims processing
│   │   ├── consolidation.py      # Data consolidation
│   │   ├── transformations.py    # Variable transformations
│   │   └── analysis.py           # Statistical analysis
│   ├── glm/
│   │   ├── __init__.py
│   │   ├── fitting.py            # GLM fitting logic
│   │   ├── diagnostics.py        # Model diagnostics
│   │   └── interaction.py        # Interaction analysis
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── date_utils.py         # Date parsing utilities
│   │   ├── validation.py         # Data validation
│   │   └── statistics.py         # Statistical utilities
│   └── schemas.py                # Pydantic models for API
├── tests/
│   ├── __init__.py
│   ├── test_premium.py
│   ├── test_claims.py
│   ├── test_consolidation.py
│   └── test_glm.py
├── pyproject.toml
└── README.md
```

## Documentation

See `/docs` folder for detailed specifications and examples.
