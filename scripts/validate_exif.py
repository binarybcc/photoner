#!/usr/bin/env python3
"""
EXIF Validation Script
Validates that EXIF metadata is preserved between original and enhanced images.
"""

import sys
import argparse
from pathlib import Path
from PIL import Image
import piexif
from typing import Dict, Any, Tuple


def extract_exif(image_path: Path) -> Dict[str, Any]:
    """
    Extract EXIF data from image.

    Args:
        image_path: Path to image

    Returns:
        Dictionary of EXIF data
    """
    try:
        with Image.open(image_path) as img:
            if "exif" in img.info:
                exif_dict = piexif.load(img.info["exif"])
                return exif_dict
            else:
                return {}
    except Exception as e:
        print(f"Error extracting EXIF from {image_path}: {e}")
        return {}


def compare_exif(original_exif: Dict, enhanced_exif: Dict) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare EXIF data between original and enhanced images.

    Args:
        original_exif: EXIF from original image
        enhanced_exif: EXIF from enhanced image

    Returns:
        Tuple of (is_preserved, differences)
    """
    # Critical EXIF fields that must be preserved
    critical_fields = {
        "0th": [
            piexif.ImageIFD.Make,           # Camera manufacturer
            piexif.ImageIFD.Model,          # Camera model
            piexif.ImageIFD.Orientation,    # Image orientation
            piexif.ImageIFD.XResolution,    # X resolution
            piexif.ImageIFD.YResolution,    # Y resolution
            piexif.ImageIFD.Copyright,      # Copyright info
        ],
        "Exif": [
            piexif.ExifIFD.DateTimeOriginal,      # Original date/time
            piexif.ExifIFD.ExposureTime,          # Shutter speed
            piexif.ExifIFD.FNumber,               # Aperture
            piexif.ExifIFD.ISOSpeedRatings,       # ISO
            piexif.ExifIFD.FocalLength,           # Focal length
            piexif.ExifIFD.LensModel,             # Lens model
        ],
        "GPS": [
            piexif.GPSIFD.GPSLatitude,
            piexif.GPSIFD.GPSLongitude,
        ],
    }

    differences = {
        "missing_fields": [],
        "changed_fields": [],
        "present_fields": [],
    }

    is_preserved = True

    for ifd_name, field_ids in critical_fields.items():
        original_ifd = original_exif.get(ifd_name, {})
        enhanced_ifd = enhanced_exif.get(ifd_name, {})

        for field_id in field_ids:
            original_value = original_ifd.get(field_id)
            enhanced_value = enhanced_ifd.get(field_id)

            # Skip if field not in original
            if original_value is None:
                continue

            # Check if field is preserved
            if enhanced_value is None:
                differences["missing_fields"].append({
                    "ifd": ifd_name,
                    "field_id": field_id,
                    "original_value": original_value,
                })
                is_preserved = False
            elif original_value != enhanced_value:
                differences["changed_fields"].append({
                    "ifd": ifd_name,
                    "field_id": field_id,
                    "original_value": original_value,
                    "enhanced_value": enhanced_value,
                })
                is_preserved = False
            else:
                differences["present_fields"].append({
                    "ifd": ifd_name,
                    "field_id": field_id,
                })

    return is_preserved, differences


def validate_exif_preservation(original_path: Path, enhanced_path: Path, verbose: bool = False) -> bool:
    """
    Validate EXIF preservation between images.

    Args:
        original_path: Path to original image
        enhanced_path: Path to enhanced image
        verbose: Print detailed information

    Returns:
        True if EXIF is preserved, False otherwise
    """
    print(f"\n{'=' * 70}")
    print(f"EXIF Validation")
    print(f"{'=' * 70}")
    print(f"Original: {original_path}")
    print(f"Enhanced: {enhanced_path}")
    print(f"{'=' * 70}\n")

    # Check files exist
    if not original_path.exists():
        print(f"❌ Original file not found: {original_path}")
        return False

    if not enhanced_path.exists():
        print(f"❌ Enhanced file not found: {enhanced_path}")
        return False

    # Extract EXIF
    print("Extracting EXIF data...")
    original_exif = extract_exif(original_path)
    enhanced_exif = extract_exif(enhanced_path)

    if not original_exif:
        print("⚠️  Original image has no EXIF data")
        return True  # No EXIF to preserve

    if not enhanced_exif:
        print("❌ Enhanced image has no EXIF data (original had EXIF)")
        return False

    # Compare EXIF
    is_preserved, differences = compare_exif(original_exif, enhanced_exif)

    # Print results
    present_count = len(differences["present_fields"])
    missing_count = len(differences["missing_fields"])
    changed_count = len(differences["changed_fields"])

    print(f"✅ Preserved fields: {present_count}")
    print(f"❌ Missing fields: {missing_count}")
    print(f"⚠️  Changed fields: {changed_count}")

    if verbose:
        if differences["missing_fields"]:
            print("\nMissing fields:")
            for field in differences["missing_fields"]:
                print(f"  - {field['ifd']}/{field['field_id']}: {field['original_value']}")

        if differences["changed_fields"]:
            print("\nChanged fields:")
            for field in differences["changed_fields"]:
                print(f"  - {field['ifd']}/{field['field_id']}:")
                print(f"    Original: {field['original_value']}")
                print(f"    Enhanced: {field['enhanced_value']}")

    print(f"\n{'=' * 70}")
    if is_preserved:
        print("✅ EXIF VALIDATION PASSED - All critical metadata preserved")
    else:
        print("❌ EXIF VALIDATION FAILED - Some metadata was lost or changed")
    print(f"{'=' * 70}\n")

    return is_preserved


def main():
    """Command-line interface for EXIF validation."""
    parser = argparse.ArgumentParser(
        description="Validate EXIF preservation between original and enhanced images"
    )

    parser.add_argument(
        "--original",
        type=Path,
        required=True,
        help="Path to original image",
    )

    parser.add_argument(
        "--enhanced",
        type=Path,
        required=True,
        help="Path to enhanced image",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed field-by-field comparison",
    )

    args = parser.parse_args()

    try:
        success = validate_exif_preservation(
            args.original,
            args.enhanced,
            verbose=args.verbose
        )
        return 0 if success else 1

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
