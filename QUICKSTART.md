# Quick Start Guide - GLM Data Preparation Tool

## 5-Minute Setup

### 1. Install
```bash
pip install -e .
```

### 2. Check Installation
```bash
glm-data-prep --help
```

## Common Tasks

### Process Premium Data
```bash
glm-data-prep process-premium \
  --premium-file data/premium.csv \
  --study-start 2022-01-01 \
  --study-end 2024-12-31 \
  --uid-col PolicyID \
  --product-col Product \
  --policy-start-col StartDate \
  --policy-end-col EndDate \
  --premium-col GrossPremium
```

### Process Claims Data
```bash
glm-data-prep process-claims \
  --claims-file data/claims.csv \
  --study-start 2022-01-01 \
  --study-end 2024-12-31 \
  --uid-col PolicyID \
  --loss-date-col AccidentDate \
  --claim-type-col PerilType \
  --claim-amount-col PaidAmount
```

### Start API Server
```bash
glm-data-prep api --port 8000
```

Then navigate to: http://localhost:8000/docs

## Data Format

### Premium CSV (Required Columns)
```
PolicyID,Product,StartDate,EndDate,GrossPremium
P001,Motor,01-01-2022,31-12-2022,50000
P002,Fire,15-06-2022,14-06-2023,75000
```

### Claims CSV (Required Columns)
```
PolicyID,AccidentDate,PerilType,PaidAmount
P001,15-06-2022,OD,50000
P002,20-11-2022,Fire,100000
```

## Python Example

```python
from datetime import date
from glm_data_prep import PremiumProcessor, ClaimsProcessor

# Process premium
premium_proc = PremiumProcessor(
    study_start=date(2022, 1, 1),
    study_end=date(2024, 12, 31),
    accident_year_split=True
)
premium1, log = premium_proc.process(
    file_path="premium.csv",
    uid_col="PolicyID",
    product_col="Product",
    policy_start_col="StartDate",
    policy_end_col="EndDate",
    premium_col="GrossPremium"
)

print(f"Processed {len(premium1)} policy periods")
print(log)
```

## Output

### Premium1 Dataset
Columns: `UID`, `Product`, `PremiumAmount`, `Exposure`, `EarnPremium`, `Period`

- **Exposure**: Fraction of policy year in study period
- **EarnPremium**: Premium allocated to study period

### Claims1 Dataset
Columns: `UID`, `LossDate`, `ClaimType`, `ClaimAmount`, `Period`

- All claims within study period
- Period = Year of loss date

## API Quick Reference

```bash
# Configure study period
curl -X POST http://localhost:8000/api/config/study-period \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2022-01-01",
    "end_date": "2024-12-31",
    "premium_type": "Amount",
    "accident_year_split": true
  }'

# Check status
curl http://localhost:8000/api/status

# View API docs
# Open: http://localhost:8000/docs
```

## Troubleshooting

### Issue: Date parsing fails
**Solution**: Ensure dates match the specified format (default: dmy)
```bash
--date-format dmy    # 01-01-2022
--date-format ymd    # 2022-01-01
```

### Issue: Premium counts don't match
**Reason**: May be higher if `--accident-year-split` is enabled (policies split by year)

### Issue: Claims missing
**Reason**: May be filtered by study period. Check dates are within range.

## Next Steps

1. **Read IMPLEMENTATION.md** for complete feature list
2. **Check examples/** folder for sample data
3. **Run tests** with `pytest` to verify installation
4. **Build React UI** using FastAPI endpoints

## Get Help

- Full docs: See `README.md` and `IMPLEMENTATION.md`
- API docs: Run server and visit `/docs`
- Report issues: Create GitHub issue with error logs

## Performance Tips

- Use Polars for 10-100x speed improvement over pandas
- Large datasets (>1M records)? Use study period sub-ranges
- GLM fitting is 40x faster than statsmodels (uses glum)
- All data operations are parallelized where possible
