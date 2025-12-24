#!/usr/bin/env python3
"""
Generate Processing Reports
Creates CSV exports, cleanup manifests, and statistics reports.
"""

import sys
import argparse
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from record_keeper import RecordKeeper
from logger import setup_logger


def main():
    parser = argparse.ArgumentParser(
        description="Generate processing reports and cleanup manifests"
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("./config/config.yaml"),
        help="Path to configuration file"
    )

    parser.add_argument(
        "--report-type",
        choices=["stats", "csv", "errors", "all"],
        default="stats",
        help="Type of report to generate"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to include in report"
    )

    args = parser.parse_args()

    # Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Setup logger
    logger = setup_logger(config)

    # Initialize record keeper
    record_keeper = RecordKeeper(config, logger)

    print(f"\n{'=' * 70}")
    print(f"Photoner Processing Reports")
    print(f"{'=' * 70}\n")

    # Generate requested reports
    if args.report_type in ["stats", "all"]:
        print(f"Processing Statistics (Last {args.days} days)")
        print("-" * 70)

        stats = record_keeper.get_processing_stats(args.days)

        print(f"Total Processed: {stats['total_processed']}")
        print(f"  ✓ Successful: {stats['successful']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  ○ Skipped: {stats['skipped']}")
        print(f"\nAverage Processing Time: {stats['avg_processing_time_sec']:.2f} seconds")
        print(f"\nOriginal Images Size: {stats['total_original_size_gb']:.2f} GB")
        print(f"Enhanced Images Size: {stats['total_enhanced_size_gb']:.2f} GB")

        if stats['successful'] > 0:
            error_rate = (stats['failed'] / (stats['successful'] + stats['failed'])) * 100
            print(f"Error Rate: {error_rate:.2f}%")

        print()

    if args.report_type in ["csv", "all"]:
        print(f"Exporting CSV Report (Last {args.days} days)")
        print("-" * 70)

        csv_path = record_keeper.export_to_csv(days=args.days)
        print(f"✓ CSV exported to: {csv_path}")
        print()

    if args.report_type in ["errors", "all"]:
        print(f"Error Summary (Last {args.days} days)")
        print("-" * 70)

        errors = record_keeper.get_error_summary(args.days)

        if errors:
            for error in errors[:10]:  # Top 10 errors
                print(f"✗ {error['error']}")
                print(f"  Count: {error['count']} occurrences")
                print(f"  Last seen: {error['last_seen']}")
                print()
        else:
            print("✓ No errors found!")
            print()

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
