# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Photoner** - Automated Newspaper Photo Enhancement System for UpstateToday.com

This is a Python-based automated photo enhancement pipeline designed to run unattended on a Synology DS1522+ NAS. The system processes incoming newspaper photographs (8x daily) and enhances thousands of archived images during off-hours, preparing them for online sale via Cloudspot.io.

**Key Constraints:**
- Target hardware: Synology DS1522+ (Intel Celeron J4125, 2GB RAM, 25TB storage)
- Must preserve original files and EXIF metadata at all costs
- Conservative resource usage (70-90% CPU max, <1.8GB RAM)
- Zero manual intervention once configured
- Network-local processing only (no cloud dependencies)

## Architecture

### Component Structure (Planned)

The system follows a modular architecture:

```
photo_enhancer.py       # Main orchestrator - manages scheduling and pipeline
processor.py            # OpenCV-based enhancement engine + RAW handling
file_manager.py         # Directory scanning, validation, safe file operations
logger.py               # Structured logging, error tracking, metrics
config.yaml             # All tunable parameters and directory paths
```

### Processing Pipeline Flow

1. **Discovery** - Scan directories for unprocessed images, build queue
2. **Pre-Processing** - Validate files, read EXIF, check for duplicates
3. **Enhancement** - Apply OpenCV algorithms (CLAHE, white balance, sharpening, etc.)
4. **Output** - Save to separate directory, preserve EXIF, log results
5. **Post-Processing** - Update logs, move originals, generate statistics

### Directory Structure (Target NAS)

```
/volume1/photos/
├── incoming/                    # New uploads (8x daily)
│   └── processed/
├── archive/                     # Legacy newspaper photos
│   └── processed/
├── enhanced/                    # All output (NEVER modify originals)
│   ├── incoming/[date]/
│   └── archive/[year]/[month]/
├── originals_backup/           # Optional safety copy
└── logs/                       # Processing logs and reports
```

## Critical Implementation Rules

### 1. Data Safety (Non-Negotiable)

- **NEVER modify original files in place** - always write to separate output directory
- **Always preserve EXIF metadata** - photographer credits, dates, camera settings, GPS, copyright
- Use atomic file operations (write to temp, then move)
- Check disk space before processing (abort if <10GB free)
- Verify write success before marking as processed

### 2. Enhancement Algorithm Strategy

**Default Profile: Conservative**
- CLAHE (Contrast Limited Adaptive Histogram Equalization): clip_limit=2.5, tile_grid=8x8
- Auto white balance (gray world assumption)
- Brightness/exposure correction (histogram-based, avoid clipping)
- Subtle saturation boost (+15%)
- Unsharp mask sharpening (radius=1.5, amount=0.7)
- Conditional noise reduction (only if EXIF ISO >800)

**Key Philosophy:** Subtle improvements that match photographer style, not extreme transformations.

### 3. Resource Management

- Process in batches (incoming: 500/run, archive: 2000-5000/night)
- Conservative threading (2 threads max due to 2GB RAM)
- Monitor memory per-image (200-400MB typical)
- Implement crash recovery (resume from last successful image)
- Graceful error handling (log, skip, continue - never crash entire batch)

### 4. Quality Control

- Every 100th image flagged for manual spot-check
- Log images with extreme adjustments for review
- Validate output file integrity (not corrupted, resolution matches input)
- Generate side-by-side comparison HTML reports

## Development Commands

### Initial Setup (Synology NAS)

```bash
# SSH into NAS
ssh admin@nas-hostname

# Create virtual environment
python3 -m venv /volume1/photos/venv
source /volume1/photos/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directory structure
mkdir -p /volume1/photos/{incoming,archive,enhanced,logs,originals_backup}
```

### Testing

```bash
# Test on small sample
python photo_enhancer.py --mode test --batch-size 10 --input ./test_samples/

# Process with specific profile
python photo_enhancer.py --profile aggressive --input /volume1/photos/archive/2018/

# Validate EXIF preservation
python scripts/validate_exif.py --original ./input.jpg --enhanced ./output.jpg

# Check memory usage during processing
python photo_enhancer.py --profile memory-test --batch-size 50
```

### Production Operations

```bash
# Process incoming photos (scheduled every 2 hours)
python photo_enhancer.py --mode incoming --max-runtime 120m

# Process archive (scheduled nightly 11pm-6am)
python photo_enhancer.py --mode archive --max-runtime 420m

# Re-process specific directory with different profile
python photo_enhancer.py --reprocess --input /volume1/photos/archive/2015/ --profile aggressive

# Generate processing report
python scripts/generate_report.py --period daily
```

### Monitoring & Debugging

```bash
# Tail processing logs
tail -f /volume1/photos/logs/processing.log

# Check error rate
grep "ERROR" /volume1/photos/logs/processing.log | wc -l

# View recent processing stats
python scripts/stats.py --last 24h

# Validate queue status
python photo_enhancer.py --status
```

## Configuration Management

All tunable parameters live in `config.yaml`:

- **Enhancement profiles** - conservative/aggressive/custom presets
- **Processing schedules** - incoming vs archive timing
- **Resource limits** - batch sizes, thread counts, memory caps
- **Quality settings** - JPEG quality (default: 95%), spot-check frequency
- **Directory paths** - all input/output locations

**Key Parameters to Tune:**
- `enhancement.clahe.clip_limit` - Controls contrast strength (2.0-3.5)
- `enhancement.saturation_boost` - Color vibrancy (1.0-1.3)
- `processing.max_batch_size` - Memory vs throughput tradeoff
- `schedule.archive.daily_target` - Archive processing pace

## Technology Stack

**Core Dependencies:**
- `opencv-python` 4.8.1.78 - Image processing engine
- `rawpy` 0.18.1 - RAW file decoding (CR2, NEF, ARW, DNG)
- `Pillow` 10.1.0 - Additional image operations
- `piexif` 1.1.3 - EXIF metadata preservation
- `numpy` 1.24.3 - Array operations (OpenCV dependency)
- `pyyaml` 6.0.1 - Configuration parsing
- `tqdm` 4.66.1 - Progress bars (optional)

**Target Environment:**
- Python 3.8+ (Synology DSM 7.x)
- No GPU acceleration (CPU-only processing)
- No external API dependencies (fully local)

## Implementation Phases (PRD Section 7.1)

**Phase 1: Core Processor**
- Basic enhancement pipeline with OpenCV
- EXIF preservation validation
- Test on 10-20 sample images

**Phase 2: File Management**
- Directory scanning and queue building
- Safe file operations (atomic writes)
- Duplicate detection

**Phase 3: Logging & Monitoring**
- Structured logging (JSON format)
- Error tracking and daily reports
- Performance metrics

**Phase 4: Scheduling & Automation**
- Synology Task Scheduler integration
- Incoming photo monitoring (2-hour intervals)
- Archive processing (nightly 11pm-6am)

**Phase 5: Production Deployment**
- Test batch (1,000 images)
- Quality review and parameter tuning
- Full production launch

## Error Handling Strategy

**Common Scenarios:**
- **Corrupted files** - Log, skip, flag for manual review
- **Unsupported formats** - Log, skip, optionally attempt conversion
- **Insufficient disk space** - Pre-flight check, abort batch, send alert
- **Memory errors** - Reduce batch size automatically, process large files individually
- **EXIF failures** - Process without EXIF, log warning, save enhanced image anyway

**Recovery Mechanisms:**
- Maintain processing state file (resume from crash)
- Retry failed images once before logging error
- Duplicate prevention (check output exists, compare timestamps)
- Bad output detection (verify file size >0, image opens, dimensions match)

## Performance Expectations

**Processing Speed (Estimated):**
- JPEG (4000x3000): 2-5 seconds per image
- RAW (6000x4000): 8-15 seconds per image
- Throughput: 720-1,800 JPEG/hour, 240-450 RAW/hour

**Target Error Rate:** <5% (log for review, not blocking)

**Completion Goals:**
- Incoming photos: Within 2 hours of upload
- Archive processing: 30 days for entire backlog (3,000 images/night)

## Code Style Conventions

When implementing this system:

1. **Use descriptive variable names** - `enhanced_image` not `img2`, `exif_data` not `ex`
2. **Comprehensive error handling** - Wrap all file I/O and image processing in try/except
3. **Extensive logging** - Log start/end of each stage, all errors, performance metrics
4. **Type hints** - Use Python type annotations for function signatures
5. **Docstrings** - Google-style docstrings for all functions and classes
6. **Configuration over hardcoding** - All magic numbers go in config.yaml
7. **Idempotent operations** - Safe to re-run processing on same images (check if already processed)

## Future Enhancements (Post-MVP)

- Machine learning model trained on photographer-adjusted images
- Web interface for monitoring and manual overrides
- GPU acceleration (if NAS upgraded)
- Direct API integration with Cloudspot.io
- Automatic watermarking before upload
- Facial recognition for subject indexing

## Reference Documentation

**Full PRD:** `newspaper_photo_enhancement_PRD.md` (comprehensive requirements, architecture, and acceptance criteria)

**Key PRD Sections:**
- Section 4: Enhancement Algorithms (detailed OpenCV operations)
- Section 6: Data Safety & Quality Assurance (critical rules)
- Section 10: Error Handling & Edge Cases (recovery mechanisms)
- Appendix A/B: Sample log formats (JSON structure)

**External Resources:**
- OpenCV docs: https://docs.opencv.org/
- rawpy docs: https://letmaik.github.io/rawpy/
- piexif docs: https://piexif.readthedocs.io/
- Synology Task Scheduler: https://kb.synology.com/
