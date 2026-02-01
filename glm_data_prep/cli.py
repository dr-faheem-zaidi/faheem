"""Command-line interface for GLM Data Preparation Tool."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from glm_data_prep.models.premium import PremiumProcessor
from glm_data_prep.models.claims import ClaimsProcessor
from glm_data_prep.models.large_loss import LargeLossProcessor
from glm_data_prep.models.consolidation import DataConsolidator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GLM Data Preparation Tool for Insurance Actuarial Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process premium data
  glm-data-prep process-premium \\
    --premium-file data/premium.csv \\
    --study-start 2022-01-01 \\
    --study-end 2024-12-31 \\
    --uid-col PolicyID \\
    --product-col Product

  # Process claims data
  glm-data-prep process-claims \\
    --claims-file data/claims.csv \\
    --study-start 2022-01-01 \\
    --study-end 2024-12-31
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Premium processing command
    premium_parser = subparsers.add_parser(
        "process-premium", help="Process premium data"
    )
    premium_parser.add_argument(
        "--premium-file", required=True, help="Path to premium CSV file"
    )
    premium_parser.add_argument(
        "--study-start", required=True, help="Study start date (YYYY-MM-DD)"
    )
    premium_parser.add_argument(
        "--study-end", required=True, help="Study end date (YYYY-MM-DD)"
    )
    premium_parser.add_argument("--uid-col", default="UID", help="UID column name")
    premium_parser.add_argument(
        "--product-col", default="Product", help="Product column name"
    )
    premium_parser.add_argument(
        "--policy-start-col", default="PolicyStart", help="Policy start date column"
    )
    premium_parser.add_argument(
        "--policy-end-col", default="PolicyEnd", help="Policy end date column"
    )
    premium_parser.add_argument(
        "--premium-col", default="Premium", help="Premium amount column"
    )
    premium_parser.add_argument(
        "--date-format", default="dmy", choices=["dmy", "ymd"], help="Date format"
    )
    premium_parser.add_argument(
        "--accident-year-split",
        action="store_true",
        help="Split by accident year",
    )
    premium_parser.add_argument(
        "--output", help="Output CSV file path"
    )

    # Claims processing command
    claims_parser = subparsers.add_parser("process-claims", help="Process claims data")
    claims_parser.add_argument(
        "--claims-file", required=True, help="Path to claims CSV file"
    )
    claims_parser.add_argument(
        "--study-start", required=True, help="Study start date (YYYY-MM-DD)"
    )
    claims_parser.add_argument(
        "--study-end", required=True, help="Study end date (YYYY-MM-DD)"
    )
    claims_parser.add_argument("--uid-col", default="UID", help="UID column name")
    claims_parser.add_argument(
        "--loss-date-col", default="LossDate", help="Loss date column"
    )
    claims_parser.add_argument(
        "--claim-type-col", default="ClaimType", help="Claim type column"
    )
    claims_parser.add_argument(
        "--claim-amount-col", default="ClaimAmount", help="Claim amount column"
    )
    claims_parser.add_argument(
        "--date-format", default="dmy", choices=["dmy", "ymd"], help="Date format"
    )
    claims_parser.add_argument(
        "--output", help="Output CSV file path"
    )

    # API server command
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.add_argument(
        "--host", default="0.0.0.0", help="API server host"
    )
    api_parser.add_argument(
        "--port", type=int, default=8000, help="API server port"
    )

    args = parser.parse_args()

    if args.command == "process-premium":
        process_premium(args)
    elif args.command == "process-claims":
        process_claims(args)
    elif args.command == "api":
        start_api_server(args)
    else:
        parser.print_help()
        sys.exit(1)


def process_premium(args):
    """Process premium data."""
    try:
        study_start = datetime.strptime(args.study_start, "%Y-%m-%d").date()
        study_end = datetime.strptime(args.study_end, "%Y-%m-%d").date()

        print(f"Processing premium data from {args.premium_file}...")
        print(f"Study period: {study_start} to {study_end}")

        processor = PremiumProcessor(
            study_start=study_start,
            study_end=study_end,
            accident_year_split=args.accident_year_split,
        )

        premium1, log = processor.process(
            file_path=args.premium_file,
            uid_col=args.uid_col,
            product_col=args.product_col,
            policy_start_col=args.policy_start_col,
            policy_end_col=args.policy_end_col,
            premium_col=args.premium_col,
            date_format=args.date_format,
        )

        print(log)
        print(f"\nProcessed {len(premium1)} policy periods")

        if args.output:
            premium1.write_csv(args.output)
            print(f"Results saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def process_claims(args):
    """Process claims data."""
    try:
        study_start = datetime.strptime(args.study_start, "%Y-%m-%d").date()
        study_end = datetime.strptime(args.study_end, "%Y-%m-%d").date()

        print(f"Processing claims data from {args.claims_file}...")
        print(f"Study period: {study_start} to {study_end}")

        processor = ClaimsProcessor(
            study_start=study_start,
            study_end=study_end,
        )

        claims1, log = processor.process(
            file_path=args.claims_file,
            uid_col=args.uid_col,
            loss_date_col=args.loss_date_col,
            claim_type_col=args.claim_type_col,
            claim_amount_col=args.claim_amount_col,
            date_format=args.date_format,
        )

        print(log)
        print(f"\nProcessed {len(claims1)} claims")

        if args.output:
            claims1.write_csv(args.output)
            print(f"Results saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def start_api_server(args):
    """Start FastAPI server."""
    import uvicorn
    from glm_data_prep.api import app

    print(f"Starting API server on {args.host}:{args.port}")
    print("Available endpoints:")
    print("  POST /api/config/study-period - Configure study period")
    print("  POST /api/data/premium/upload - Upload premium data")
    print("  POST /api/data/claims/upload - Upload claims data")
    print("  POST /api/analysis/consolidate - Consolidate data")
    print("  POST /api/analysis/one-way - One-way analysis")
    print("  POST /api/analysis/two-way - Two-way analysis")
    print("  POST /api/glm/fit - Fit GLM model")
    print("  GET /api/status - Check status")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
