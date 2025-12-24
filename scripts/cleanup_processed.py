#!/usr/bin/env python3
"""
Cleanup Processed Originals
Safely delete originals that have been successfully enhanced and moved to /processed folders.
"""

import sys
import argparse
from pathlib import Path
import yaml
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from record_keeper import RecordKeeper
from logger import setup_logger


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup processed original files (you have Glacier backups)"
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("./config/config.yaml"),
        help="Path to configuration file"
    )

    parser.add_argument(
        "--older-than-days",
        type=int,
        default=30,
        help="Only delete files processed more than N days ago"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (dangerous!)"
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
    print(f"Photoner Cleanup Utility")
    print(f"{'=' * 70}\n")

    # Create cleanup manifest
    print(f"Analyzing processed files (older than {args.older_than_days} days)...")
    manifest_path = record_keeper.create_cleanup_manifest(older_than_days=args.older_than_days)

    # Get candidates
    candidates = record_keeper.get_cleanup_candidates()

    # Filter by age
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=args.older_than_days)

    eligible = [
        c for c in candidates
        if datetime.fromisoformat(c['processed_date'].rstrip('Z')) < cutoff_date
    ]

    if not eligible:
        print("✓ No files eligible for cleanup")
        print()
        return 0

    total_size = sum(c['size_bytes'] for c in eligible)
    total_size_gb = total_size / (1024**3)

    print(f"\nReady for cleanup:")
    print(f"  Files: {len(eligible)}")
    print(f"  Total Size: {total_size_gb:.2f} GB")
    print(f"  Manifest: {manifest_path}")
    print()

    # Show sample
    print("Sample files (first 10):")
    for candidate in eligible[:10]:
        print(f"  {candidate['current_location']} ({candidate['size_mb']:.2f} MB)")
    if len(eligible) > 10:
        print(f"  ... and {len(eligible) - 10} more")
    print()

    # Dry run mode
    if args.dry_run:
        print("DRY RUN MODE - No files will be deleted")
        print()
        return 0

    # Confirmation
    if not args.confirm:
        print("⚠️  WARNING: This will permanently delete these files!")
        print("   You mentioned having Glacier backups, but please verify:")
        print()
        print("   1. Enhanced versions exist in /enhanced directory")
        print("   2. Originals are backed up in Glacier")
        print("   3. You're ready to free up space")
        print()

        response = input("Type 'DELETE' to proceed: ")
        if response != "DELETE":
            print("Cancelled.")
            return 0

    # Perform cleanup
    print("\nDeleting files...")

    deleted_count = 0
    freed_space = 0
    directories_cleaned = set()

    for candidate in eligible:
        file_path = Path(candidate['current_location'])

        try:
            if file_path.exists():
                freed_space += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                directories_cleaned.add(str(file_path.parent))

                if deleted_count % 100 == 0:
                    print(f"  Deleted {deleted_count}/{len(eligible)} files...")

        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")

    freed_space_gb = freed_space / (1024**3)

    print(f"\n✓ Cleanup complete!")
    print(f"  Deleted: {deleted_count} files")
    print(f"  Freed: {freed_space_gb:.2f} GB")
    print()

    # Record cleanup in database
    record_keeper.record_cleanup(
        files_deleted=deleted_count,
        space_freed_gb=freed_space_gb,
        directories=list(directories_cleaned),
        manifest_path=manifest_path
    )

    # Cleanup empty directories
    print("Cleaning up empty /processed directories...")
    for directory in directories_cleaned:
        dir_path = Path(directory)
        try:
            if dir_path.exists() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                print(f"  Removed empty directory: {dir_path}")
        except Exception as e:
            logger.debug(f"Could not remove directory {dir_path}: {e}")

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
