# Photoner - Automated Newspaper Photo Enhancement System

Automated photo enhancement pipeline for UpstateToday.com running on Synology DS1522+ NAS.

## Overview

Photoner automatically processes incoming newspaper photographs and enhances thousands of archived images using OpenCV-based enhancement algorithms. The system runs unattended, preserving original files and EXIF metadata while preparing photos for online sale.

## Key Features

- **Automated Processing**: Handles 8x daily uploads and overnight archive processing
- **Safe Operations**: Never modifies originals, atomic file operations, EXIF preservation
- **Conservative Enhancement**: CLAHE, white balance, sharpening, noise reduction
- **Resource Aware**: Optimized for 2GB RAM, batch processing, crash recovery
- **Quality Control**: Spot-checking, validation, detailed logging

## Project Structure

```
photoner/
├── src/                    # Source code
│   ├── photo_enhancer.py  # Main orchestrator
│   ├── processor.py       # Enhancement engine
│   ├── file_manager.py    # File operations
│   └── logger.py          # Logging system
├── config/                # Configuration files
│   └── config.yaml        # Main configuration
├── scripts/               # Utility scripts
├── tests/                 # Unit and integration tests
├── docs/                  # Additional documentation
├── test_samples/          # Sample images for testing
└── requirements.txt       # Python dependencies
```

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Testing

```bash
# Test on sample images
python src/photo_enhancer.py --mode test --batch-size 10 --input ./test_samples/

# Validate EXIF preservation
python scripts/validate_exif.py --original ./input.jpg --enhanced ./output.jpg
```

## Target Deployment

This system is designed to run on:
- **Hardware**: Synology DS1522+ NAS
- **OS**: DSM 7.x
- **CPU**: Intel Celeron J4125 (quad-core)
- **RAM**: 2GB (no upgrade)
- **Storage**: 25TB

## Documentation

- **CLAUDE.md**: Comprehensive implementation guidance
- **newspaper_photo_enhancement_PRD.md**: Full product requirements document
- **docs/**: Additional documentation (TODO)

## Technology Stack

- Python 3.8+
- OpenCV 4.8.1.78 (image processing)
- rawpy 0.18.1 (RAW file handling)
- Pillow 10.1.0 (additional image ops)
- piexif 1.1.3 (EXIF preservation)

## License

(TODO: Add license)

## Contact

UpstateToday.com Photo Enhancement Pipeline
