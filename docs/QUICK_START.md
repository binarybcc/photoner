# Quick Start Guide

Get up and running with Photoner in 10 minutes.

## Installation

### 1. Clone or Download

```bash
git clone https://github.com/binarybcc/photoner.git
cd photoner
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Verify installation:

```bash
./scripts/run_test.sh
```

## Quick Test

### 1. Add Test Images

Put a few JPEG images in `test_samples/incoming/`:

```bash
mkdir -p test_samples/incoming
cp ~/Pictures/sample*.jpg test_samples/incoming/
```

### 2. Run Processing

```bash
python src/photo_enhancer.py --mode test --batch-size 5
```

### 3. Check Output

Enhanced images are in `enhanced/incoming/` with `_enhanced.jpg` suffix.

### 4. Validate EXIF

```bash
python scripts/validate_exif.py \
    --original test_samples/incoming/sample.jpg \
    --enhanced enhanced/incoming/sample_enhanced.jpg
```

## Configuration

Edit `config/config.yaml` to tune enhancement:

```yaml
enhancement:
  profile: conservative  # or aggressive

  clahe:
    clip_limit: 2.5  # 2.0-3.5, higher = more contrast

  saturation:
    boost_factor: 1.15  # 1.0-1.3, higher = more vibrant

  sharpening:
    amount: 0.7  # 0.5-1.0, higher = sharper
```

## Command Reference

```bash
# Test mode (processes test_samples/)
python src/photo_enhancer.py --mode test --batch-size 10

# Process incoming photos
python src/photo_enhancer.py --mode incoming --batch-size 500

# Process archive
python src/photo_enhancer.py --mode archive --batch-size 3000

# Use aggressive profile
python src/photo_enhancer.py --mode test --profile aggressive

# Custom config file
python src/photo_enhancer.py --config my_config.yaml --mode test

# Check system status
python src/photo_enhancer.py --status

# Override input directory
python src/photo_enhancer.py --mode test --input /path/to/photos
```

## Monitoring

```bash
# Watch logs in real-time
tail -f logs/processing.log

# View errors only
tail -f logs/errors.log
```

## Troubleshooting

**"No images to process"**
- Check `test_samples/incoming/` has .jpg files
- Run `ls -la test_samples/incoming/`

**"Failed to load image"**
- Verify files are valid JPEG images
- Try opening in image viewer

**"Module not found"**
- Activate virtual environment: `source venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

**Out of memory**
- Reduce `max_batch_size` in config
- Reduce `processing_threads` to 1

## Next Steps

1. ✅ Test on sample images
2. ✅ Validate EXIF preservation
3. ✅ Tune enhancement parameters to your preference
4. For production deployment → See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## Example Workflow

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Add test images
cp ~/Pictures/*.jpg test_samples/incoming/

# 3. Process
python src/photo_enhancer.py --mode test --batch-size 10

# 4. Review results
open enhanced/incoming/  # macOS
# or: xdg-open enhanced/incoming/  # Linux

# 5. Validate one image
python scripts/validate_exif.py \
    --original test_samples/incoming/photo1.jpg \
    --enhanced enhanced/incoming/photo1_enhanced.jpg \
    --verbose

# 6. If satisfied, process more
python src/photo_enhancer.py --mode test --batch-size 100
```

## Getting Help

- **Documentation:** See `docs/` directory
- **Issues:** https://github.com/binarybcc/photoner/issues
- **PRD:** `newspaper_photo_enhancement_PRD.md` (full requirements)
- **Implementation Guide:** `CLAUDE.md` (for developers)
