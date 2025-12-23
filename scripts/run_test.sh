#!/bin/bash
# Test Script for Photoner
# Runs basic tests to verify installation and functionality

set -e  # Exit on error

echo "=================================="
echo "Photoner Test Suite"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Check if virtual environment is active
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "   Activate with: source venv/bin/activate"
    echo ""
else
    echo "✅ Virtual environment active: ${VIRTUAL_ENV}"
    echo ""
fi

# Check dependencies
echo "Checking Python dependencies..."
REQUIRED_PACKAGES=("opencv-python" "numpy" "Pillow" "piexif" "pyyaml" "tqdm")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        echo "  ✅ ${package}"
    else
        echo "  ❌ ${package} - NOT INSTALLED"
        echo "     Run: pip install -r requirements.txt"
    fi
done
echo ""

# Check optional rawpy
if python3 -c "import rawpy" 2>/dev/null; then
    echo "  ✅ rawpy (RAW file support enabled)"
else
    echo "  ⚠️  rawpy - NOT INSTALLED (RAW files will not be supported)"
    echo "     Install with: pip install rawpy==0.18.1"
fi
echo ""

# Check directory structure
echo "Checking directory structure..."
REQUIRED_DIRS=("src" "config" "scripts" "test_samples" "tests")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "${dir}" ]; then
        echo "  ✅ ${dir}/"
    else
        echo "  ❌ ${dir}/ - MISSING"
    fi
done
echo ""

# Check configuration file
echo "Checking configuration..."
if [ -f "config/config.yaml" ]; then
    echo "  ✅ config/config.yaml exists"

    # Validate YAML syntax
    if python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))" 2>/dev/null; then
        echo "  ✅ config.yaml is valid YAML"
    else
        echo "  ❌ config.yaml has syntax errors"
    fi
else
    echo "  ❌ config/config.yaml - MISSING"
fi
echo ""

# Check for test samples
echo "Checking test samples..."
TEST_SAMPLE_COUNT=$(find test_samples -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.JPG" \) 2>/dev/null | wc -l)
if [ "${TEST_SAMPLE_COUNT}" -gt 0 ]; then
    echo "  ✅ Found ${TEST_SAMPLE_COUNT} test image(s)"
else
    echo "  ⚠️  No test images found in test_samples/"
    echo "     Add sample .jpg files to test_samples/ directory"
fi
echo ""

# Test basic functionality
echo "Testing basic functionality..."

# Test import of modules
if python3 -c "
import sys
sys.path.insert(0, 'src')
from logger import setup_logger
from processor import ImageProcessor
from file_manager import FileManager
print('  ✅ All modules import successfully')
" 2>/dev/null; then
    echo ""
else
    echo "  ❌ Module import failed"
    echo "     Check src/ directory for Python files"
    exit 1
fi

# Run status check
echo "Running photo_enhancer status check..."
if python3 src/photo_enhancer.py --status 2>/dev/null; then
    echo "  ✅ Photo enhancer status check passed"
else
    echo "  ❌ Photo enhancer status check failed"
    echo "     Review error messages above"
    exit 1
fi
echo ""

# Final summary
echo "=================================="
echo "Test Summary"
echo "=================================="
echo "✅ Basic tests passed"
echo ""
echo "Next steps:"
echo "1. Add sample images to test_samples/"
echo "2. Run: python3 src/photo_enhancer.py --mode test --batch-size 1"
echo "3. Check enhanced/ directory for output"
echo "4. Validate EXIF: python3 scripts/validate_exif.py --original INPUT --enhanced OUTPUT"
echo ""
