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
# Clone repository
git clone https://github.com/binarybcc/photoner.git
cd photoner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run test suite
./scripts/run_test.sh
```

### Testing

```bash
# Add test images
cp ~/Pictures/sample*.jpg test_samples/incoming/

# Process test batch
python src/photo_enhancer.py --mode test --batch-size 5

# Check output
ls -lh enhanced/incoming/

# Validate EXIF preservation
python scripts/validate_exif.py \
    --original test_samples/incoming/sample.jpg \
    --enhanced enhanced/incoming/sample_enhanced.jpg
```

### Command Reference

```bash
# Test mode
python src/photo_enhancer.py --mode test --batch-size 10

# Process incoming photos (2 hours max)
python src/photo_enhancer.py --mode incoming --batch-size 500

# Process archive (overnight batch)
python src/photo_enhancer.py --mode archive --batch-size 3000

# Use aggressive enhancement profile
python src/photo_enhancer.py --mode test --profile aggressive

# Check system status
python src/photo_enhancer.py --status
```

## Target Deployment

This system is designed to run on:
- **Hardware**: Synology DS1522+ NAS
- **OS**: DSM 7.x
- **CPU**: Intel Celeron J4125 (quad-core)
- **RAM**: 2GB (no upgrade)
- **Storage**: 25TB

## Documentation

- **[QUICK_START.md](docs/QUICK_START.md)**: 10-minute getting started guide
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)**: Complete Synology NAS deployment guide
- **[SMART_SCHEDULING_SETUP.md](docs/SMART_SCHEDULING_SETUP.md)**: Intelligent scheduling for NAS-friendly operation
- **[RECORD_KEEPING.md](docs/RECORD_KEEPING.md)**: Logging, monitoring, and the /processed folder system
- **[CLAUDE.md](CLAUDE.md)**: Comprehensive implementation guidance for developers
- **[newspaper_photo_enhancement_PRD.md](newspaper_photo_enhancement_PRD.md)**: Full product requirements document

## Enhancement Pipeline

Photoner applies the following enhancement operations in sequence:

1. **CLAHE** - Contrast Limited Adaptive Histogram Equalization for local contrast
2. **White Balance** - Automatic color temperature correction using gray world assumption
3. **Brightness** - Histogram-based exposure adjustment
4. **Saturation** - Subtle vibrancy boost (15% by default)
5. **Noise Reduction** - Conditional (only for high ISO images >800)
6. **Sharpening** - Unsharp mask for subtle detail enhancement

All operations preserve original resolution and EXIF metadata

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
