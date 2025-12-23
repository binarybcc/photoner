# Deployment Guide for Synology NAS

Complete guide for deploying Photoner on a Synology DS1522+ NAS running DSM 7.x.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Installing Dependencies](#installing-dependencies)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Scheduling Automated Tasks](#scheduling-automated-tasks)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Synology Packages

Install these via **Package Center**:

1. **Python 3.9** or **Python 3.10**
2. **Git** (optional, for version control)
3. **Text Editor** (optional, for editing config files)

### System Requirements

- **Synology DS1522+** (or compatible model)
- **DSM 7.x** (tested on DSM 7.2+)
- **2GB RAM** minimum (system will use 70-90% during processing)
- **10GB+ free disk space** at all times

### SSH Access

Enable SSH access via **Control Panel > Terminal & SNMP > Enable SSH service**.

---

## Initial Setup

### 1. SSH into Your NAS

```bash
ssh admin@YOUR_NAS_IP
# Enter your admin password
```

### 2. Create Directory Structure on NAS

```bash
# Create main photo directory
sudo mkdir -p /volume1/photos

# Create subdirectories
sudo mkdir -p /volume1/photos/{incoming,archive,enhanced,logs,temp,originals_backup}

# Set permissions
sudo chown -R admin:users /volume1/photos
sudo chmod -R 755 /volume1/photos
```

### 3. Upload Photoner Code

**Option A: Using Git (Recommended)**

```bash
cd /volume1/photos
git clone https://github.com/binarybcc/photoner.git
cd photoner
```

**Option B: Manual Upload**

1. Download the code from GitHub as ZIP
2. Upload to NAS via **File Station**
3. Extract to `/volume1/photos/photoner/`

### 4. Create Virtual Environment

```bash
cd /volume1/photos/photoner

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.9 or 3.10
```

---

## Installing Dependencies

### Install Python Packages

```bash
# Ensure virtual environment is active
source /volume1/photos/photoner/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### Troubleshooting Installation

**If OpenCV fails to install:**

```bash
# Install system dependencies first
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0

# Then retry
pip install opencv-python==4.8.1.78
```

**If rawpy fails to install:**

RAW support is optional. If you don't need RAW file processing, you can skip this:

```bash
pip install rawpy==0.18.1
```

If installation fails, edit `requirements.txt` and comment out the rawpy line.

---

## Configuration

### 1. Copy Production Configuration

```bash
cd /volume1/photos/photoner

# Create production config from template
cp config/config.yaml config/production.yaml
```

### 2. Edit Production Configuration

```bash
nano config/production.yaml
```

**Critical settings to update:**

```yaml
paths:
  incoming: /volume1/photos/incoming
  archive: /volume1/photos/archive
  enhanced: /volume1/photos/enhanced
  logs: /volume1/photos/logs
  backup: /volume1/photos/originals_backup
  temp: /volume1/photos/temp

processing:
  max_batch_size: 500
  processing_threads: 2  # Conservative for 2GB RAM
  move_processed_originals: true
  create_backups: false  # Set true for first run on production

enhancement:
  profile: conservative  # Start conservative, tune later

schedule:
  incoming:
    enabled: true
    check_interval_hours: 2
    business_hours_only: true
    business_hours_start: 6
    business_hours_end: 22

  archive:
    enabled: true
    start_time: "23:00"
    max_duration_hours: 7
    daily_target_images: 3000
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## Testing

### 1. Run System Test

```bash
cd /volume1/photos/photoner
source venv/bin/activate

# Run test suite
./scripts/run_test.sh
```

### 2. Test on Sample Images

```bash
# Copy a few test images to incoming directory
cp /path/to/sample/images/*.jpg /volume1/photos/incoming/

# Run test processing
python src/photo_enhancer.py \
    --config config/production.yaml \
    --mode test \
    --batch-size 5

# Check enhanced output
ls -lh /volume1/photos/enhanced/
```

### 3. Validate EXIF Preservation

```bash
# Pick an original and its enhanced version
python scripts/validate_exif.py \
    --original /volume1/photos/incoming/sample.jpg \
    --enhanced /volume1/photos/enhanced/incoming/sample_enhanced.jpg \
    --verbose
```

**Expected output:** `✅ EXIF VALIDATION PASSED`

---

## Scheduling Automated Tasks

### Using Synology Task Scheduler

1. Open **Control Panel > Task Scheduler**
2. Create two scheduled tasks:

#### Task 1: Process Incoming Photos

**Settings:**
- **Task Name:** `Photoner - Process Incoming`
- **User:** `admin` or your admin user
- **Schedule:** Every 2 hours from 6 AM to 10 PM
  - **Repeat:** Custom → `*/2 * * * *` (every 2 hours)
  - **Time:** First run at 6:00 AM
- **Task Settings > Run command:**

```bash
source /volume1/photos/photoner/venv/bin/activate && \
python /volume1/photos/photoner/src/photo_enhancer.py \
    --config /volume1/photos/photoner/config/production.yaml \
    --mode incoming \
    --batch-size 500 \
    >> /volume1/photos/logs/incoming_cron.log 2>&1
```

- **Send run details by email:** Optional, enable if you want email notifications

#### Task 2: Process Archive Photos

**Settings:**
- **Task Name:** `Photoner - Process Archive`
- **User:** `admin`
- **Schedule:** Daily at 11:00 PM
  - **Repeat:** Daily at specific time
  - **Time:** 23:00 (11 PM)
- **Task Settings > Run command:**

```bash
source /volume1/photos/photoner/venv/bin/activate && \
python /volume1/photos/photoner/src/photo_enhancer.py \
    --config /volume1/photos/photoner/config/production.yaml \
    --mode archive \
    --batch-size 3000 \
    >> /volume1/photos/logs/archive_cron.log 2>&1
```

### Verify Scheduled Tasks

After creating tasks, run them manually first:

1. Select the task in Task Scheduler
2. Click **Run**
3. Monitor `/volume1/photos/logs/` for output

---

## Monitoring

### Check Processing Logs

```bash
# View real-time processing
tail -f /volume1/photos/logs/processing.log

# View errors only
tail -f /volume1/photos/logs/errors.log

# View cron output
tail -f /volume1/photos/logs/incoming_cron.log
tail -f /volume1/photos/logs/archive_cron.log
```

### Check System Status

```bash
source /volume1/photos/photoner/venv/bin/activate
python /volume1/photos/photoner/src/photo_enhancer.py \
    --config /volume1/photos/photoner/config/production.yaml \
    --status
```

### Monitor Disk Space

```bash
df -h /volume1
```

**Alert:** If free space drops below 1TB, pause processing and review storage.

### Check Processing Statistics

```bash
# Count processed images
find /volume1/photos/enhanced -name "*_enhanced.jpg" | wc -l

# Count errors in last 24 hours
grep "ERROR" /volume1/photos/logs/processing.log | grep "$(date +%Y-%m-%d)" | wc -l

# View processing throughput
grep "Batch processing complete" /volume1/photos/logs/processing.log | tail -5
```

---

## Troubleshooting

### Common Issues

#### 1. "Permission Denied" Errors

```bash
# Fix ownership
sudo chown -R admin:users /volume1/photos

# Fix permissions
sudo chmod -R 755 /volume1/photos
```

#### 2. "Out of Memory" Errors

Edit `config/production.yaml`:

```yaml
processing:
  max_batch_size: 250  # Reduce from 500
  processing_threads: 1  # Reduce from 2
```

#### 3. Processing Too Slow

Check CPU usage:

```bash
top
```

If CPU is not maxed out, increase threads:

```yaml
processing:
  processing_threads: 3  # Increase to 3-4
```

#### 4. EXIF Data Not Preserved

Check logs for EXIF warnings:

```bash
grep "EXIF" /volume1/photos/logs/processing.log
```

Verify Pillow and piexif are installed:

```bash
source venv/bin/activate
pip show Pillow piexif
```

#### 5. "Module Not Found" Errors

Ensure virtual environment is active:

```bash
source /volume1/photos/photoner/venv/bin/activate
which python  # Should show /volume1/photos/photoner/venv/bin/python
```

#### 6. Scheduled Tasks Not Running

Check Task Scheduler logs:

1. **Control Panel > Task Scheduler**
2. Select task
3. Click **View Results**

Verify permissions and paths in the Run command.

---

## Maintenance

### Weekly Maintenance

```bash
# Clean up old logs (keep last 30 days)
find /volume1/photos/logs -name "*.log.*" -mtime +30 -delete

# Check error rate
ERROR_COUNT=$(grep "ERROR" /volume1/photos/logs/processing.log | wc -l)
TOTAL_COUNT=$(grep "Processing complete" /volume1/photos/logs/processing.log | wc -l)
echo "Error rate: $(( ERROR_COUNT * 100 / TOTAL_COUNT ))%"
```

### Monthly Maintenance

1. **Review spot-check samples** in enhancement output
2. **Tune enhancement parameters** in `config/production.yaml` if needed
3. **Check disk space trends**
4. **Update dependencies** (test in dev first):

```bash
source venv/bin/activate
pip list --outdated
# Selectively update if needed
```

### Backup Configuration

```bash
# Create backup of config
cp config/production.yaml config/production.yaml.backup.$(date +%Y%m%d)

# Create backup of logs (before cleanup)
tar -czf logs_backup_$(date +%Y%m%d).tar.gz /volume1/photos/logs/*.log
```

---

## Performance Tuning

### For Faster Processing

1. **Increase threads** (if RAM allows):
   ```yaml
   processing_threads: 3  # or 4
   ```

2. **Use aggressive profile** for older archive images:
   ```yaml
   enhancement:
     profile: aggressive
   ```

3. **Disable spot-checking** (for speed):
   ```yaml
   quality:
     spot_check_enabled: false
   ```

### For Better Quality

1. **Increase JPEG quality**:
   ```yaml
   processing:
     jpeg_quality: 98  # Higher quality, larger files
   ```

2. **Fine-tune enhancement**:
   ```yaml
   enhancement:
     clahe:
       clip_limit: 3.0  # More contrast
     saturation:
       boost_factor: 1.20  # More vibrant
   ```

---

## Getting Help

**For issues:**

1. Check logs: `/volume1/photos/logs/errors.log`
2. Run with verbose logging:
   ```bash
   # Edit config
   logging:
     level: DEBUG
   ```
3. Report issues on GitHub: https://github.com/binarybcc/photoner/issues

---

**Deployment Complete!**

Your Photoner system should now be processing images automatically. Monitor logs for the first few days to ensure smooth operation.
