# Record-Keeping Guide

Simple guide to logging, monitoring, and the /processed folder system.

## Philosophy

Photoner focuses on **enhancement and record-keeping**. It:
- ✅ Processes images
- ✅ Keeps detailed logs
- ✅ Moves originals to /processed folders
- ✅ Generates reports

It does NOT:
- ❌ Delete files
- ❌ Manage retention policies
- ❌ Cleanup storage

**You handle cleanup** using standard tools (rm, File Station, etc.) when ready.

## What Gets Logged

### 1. Processing Logs (JSON Format)

**Location:** `/volume1/photos/logs/processing.log`

Every processed image creates a JSON log entry:

```json
{
  "timestamp": "2024-12-23T03:45:12Z",
  "level": "INFO",
  "message": "Processing complete: DSC_0001.jpg (3.2s)",
  "input_file": "/volume1/photos/incoming/DSC_0001.jpg",
  "output_file": "/volume1/photos/enhanced/incoming/DSC_0001_enhanced.jpg",
  "processing_time_sec": 3.2,
  "adjustments": {
    "contrast_delta": "+23%",
    "brightness_delta": "+15%",
    "saturation_boost": "15%",
    "sharpening": "radius=1.5, amount=0.7"
  },
  "status": "success"
}
```

### 2. Error Logs

**Location:** `/volume1/photos/logs/errors.log`

Failed processing attempts:

```json
{
  "timestamp": "2024-12-23T04:12:33Z",
  "level": "ERROR",
  "message": "Processing failed: corrupted.jpg",
  "input_file": "/volume1/photos/archive/corrupted.jpg",
  "error_type": "ImageDecodeError",
  "error_message": "Cannot identify image file",
  "status": "failed"
}
```

### 3. SQLite Database

**Location:** `/volume1/photos/logs/database/processing_records.db`

**Tracks:**
- Input/output file paths
- File sizes (before/after)
- Processing time
- Success/failure status
- Error messages
- Enhancement adjustments applied
- Whether original was moved to /processed
- Timestamps

**Query anytime with SQL!**

## The /processed Folder System

### How It Works

After successful enhancement, originals are **moved** to a `/processed` subfolder:

```
Before Processing:
/volume1/photos/incoming/
└── 2024-12-23/
    ├── photo_001.jpg
    ├── photo_002.jpg
    └── photo_003.jpg

After Processing:
/volume1/photos/incoming/
└── 2024-12-23/
    └── processed/              ← Originals moved here
        ├── photo_001.jpg
        ├── photo_002.jpg
        └── photo_003.jpg

Enhanced Versions:
/volume1/photos/enhanced/
└── incoming/
    └── 2024-12-23/
        ├── photo_001_enhanced.jpg
        ├── photo_002_enhanced.jpg
        └── photo_003_enhanced.jpg
```

### Why This Helps

**Easy identification:**
- Files in `/processed` = Successfully enhanced
- Enhanced version exists in `/enhanced`
- Original is redundant (you have Glacier backup)

**Manual cleanup is simple:**
```bash
# Delete all processed originals (when you're ready)
rm -rf /volume1/photos/incoming/*/processed/
rm -rf /volume1/photos/archive/*/processed/

# Or use File Station GUI
# Navigate to /processed folders and delete
```

### Disable This Feature (Optional)

In `config.yaml`:
```yaml
processing:
  move_processed_originals: false  # Keep originals in place
```

## Generating Reports

### Processing Statistics

```bash
# Last 30 days
python scripts/generate_reports.py --report-type stats --days 30
```

**Output:**
```
Processing Statistics (Last 30 days)
----------------------------------------------------------------------
Total Processed: 45,382
  ✓ Successful: 44,901 (98.9%)
  ✗ Failed: 387 (0.9%)
  ○ Skipped: 94 (0.2%)

Average Processing Time: 3.47 seconds

Original Images Size: 187.32 GB
Enhanced Images Size: 193.15 GB
Error Rate: 0.86%
```

### CSV Export

```bash
# Export last 90 days to CSV
python scripts/generate_reports.py --report-type csv --days 90
```

**Output:** `/volume1/photos/logs/reports/processing_2024-12-23.csv`

```csv
Timestamp,Original Path,Enhanced Path,Status,Processing Time (sec),Error,Moved to Processed,Processed Folder Path
2024-12-23T03:45:12Z,/volume1/photos/incoming/DSC_0001.jpg,/volume1/photos/enhanced/incoming/DSC_0001_enhanced.jpg,success,3.2,,true,/volume1/photos/incoming/processed/DSC_0001.jpg
```

**Use cases:**
- Import into Excel/Google Sheets
- Performance analysis
- Audit trails
- Billing records

### Error Summary

```bash
# Top errors in last 7 days
python scripts/generate_reports.py --report-type errors --days 7
```

**Output:**
```
Error Summary (Last 7 days)
----------------------------------------------------------------------
✗ Cannot identify image file
  Count: 23 occurrences
  Last seen: 2024-12-22T15:34:12Z

✗ Out of memory
  Count: 5 occurrences
  Last seen: 2024-12-21T03:12:45Z
```

**Use for troubleshooting and optimization.**

### All Reports at Once

```bash
python scripts/generate_reports.py --report-type all --days 30
```

## Finding Files Ready for Cleanup

### Query the Database

```bash
sqlite3 /volume1/photos/logs/database/processing_records.db
```

**Files in /processed folders:**
```sql
SELECT
    processed_folder_path,
    original_size_bytes / 1024.0 / 1024.0 as size_mb,
    timestamp
FROM processing_records
WHERE moved_to_processed = 1
AND status = 'success'
ORDER BY timestamp;
```

**Space used by /processed folders:**
```sql
SELECT
    COUNT(*) as files,
    SUM(original_size_bytes) / 1024.0 / 1024.0 / 1024.0 as total_gb
FROM processing_records
WHERE moved_to_processed = 1
AND status = 'success';
```

**Files older than 30 days:**
```sql
SELECT
    processed_folder_path,
    original_size_bytes / 1024.0 / 1024.0 as size_mb
FROM processing_records
WHERE moved_to_processed = 1
AND status = 'success'
AND timestamp <= datetime('now', '-30 days')
ORDER BY timestamp;
```

### Using File System Tools

```bash
# Count files in /processed
find /volume1/photos -type d -name "processed" -exec sh -c 'echo "$1: $(find "$1" -type f | wc -l) files"' _ {} \;

# Check disk space used
du -sh /volume1/photos/*/processed
du -sh /volume1/photos/*/*/processed

# List oldest /processed folders
find /volume1/photos -type d -name "processed" -printf '%T+ %p\n' | sort | head -20
```

## Manual Cleanup When Ready

### Conservative Approach

```bash
# 1. Verify Glacier backups are working
# 2. Spot-check enhanced versions
# 3. Delete specific old folders

rm -rf /volume1/photos/incoming/2024-01-*/processed/
```

### Complete Cleanup

```bash
# Delete ALL /processed folders (when confident)
find /volume1/photos -type d -name "processed" -exec rm -rf {} +
```

### Synology File Station

1. Navigate to `/volume1/photos/`
2. Search for folders named "processed"
3. Select and delete as needed

**Advantages:**
- Visual confirmation
- Can preview before deleting
- Recycle bin available (if enabled)

## Log Rotation

**Processing and error logs rotate automatically:**

```yaml
# In config.yaml
logging:
  max_log_size_mb: 100     # Rotate when log reaches 100 MB
  backup_count: 10         # Keep 10 old logs
```

**Log files:**
```
/volume1/photos/logs/
├── processing.log          # Current
├── processing.log.1        # Previous rotation
├── processing.log.2        # 2 rotations ago
└── processing.log.10       # Oldest (will be deleted on next rotation)
```

Old logs are **automatically deleted** after `backup_count` is reached.

## Useful SQL Queries

### Total Images Processed

```sql
SELECT COUNT(*) FROM processing_records WHERE status = 'success';
```

### Error Rate by Day

```sql
SELECT
    DATE(timestamp) as date,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate
FROM processing_records
WHERE timestamp >= date('now', '-30 days')
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

### Top Error Messages

```sql
SELECT
    error_message,
    COUNT(*) as count
FROM processing_records
WHERE status = 'failed'
GROUP BY error_message
ORDER BY count DESC
LIMIT 10;
```

### Processing Throughput by Hour

```sql
SELECT
    strftime('%H', timestamp) as hour,
    COUNT(*) as images_processed,
    AVG(processing_time_sec) as avg_time_sec
FROM processing_records
WHERE status = 'success'
AND timestamp >= datetime('now', '-7 days')
GROUP BY hour
ORDER BY hour;
```

### Space Analysis

```sql
SELECT
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_images,
    SUM(original_size_bytes) / 1024.0 / 1024.0 / 1024.0 as original_size_gb,
    SUM(enhanced_size_bytes) / 1024.0 / 1024.0 / 1024.0 as enhanced_size_gb,
    (SUM(enhanced_size_bytes) - SUM(original_size_bytes)) / 1024.0 / 1024.0 / 1024.0 as size_diff_gb
FROM processing_records
WHERE status = 'success';
```

## Backup the Database

```bash
# Backup processing records database
sqlite3 /volume1/photos/logs/database/processing_records.db ".backup '/volume1/photos/logs/database/processing_records_backup_$(date +%Y%m%d).db'"

# Or export as SQL
sqlite3 /volume1/photos/logs/database/processing_records.db ".dump" | gzip > processing_records_$(date +%Y%m%d).sql.gz
```

## Monitoring Best Practices

### Daily Checks

```bash
# Recent errors
tail -20 /volume1/photos/logs/errors.log

# Processing status
python scripts/generate_reports.py --report-type stats --days 1
```

### Weekly Reports

```bash
# Full report
python scripts/generate_reports.py --report-type all --days 7

# CSV export
python scripts/generate_reports.py --report-type csv --days 7
```

### Monthly Audits

```bash
# Long-term statistics
python scripts/generate_reports.py --report-type stats --days 30

# Error analysis
python scripts/generate_reports.py --report-type errors --days 30

# Database size check
du -sh /volume1/photos/logs/database/processing_records.db

# Review disk space used by /processed folders
du -sh /volume1/photos/*/processed
```

## Troubleshooting

### High Error Rate

```bash
# Get detailed error summary
python scripts/generate_reports.py --report-type errors --days 7

# Check specific errors
grep "ERROR" /volume1/photos/logs/errors.log | tail -50
```

### "Database is locked"

**Cause:** Another process is accessing the database

**Solution:**
```bash
# Check for running processes
ps aux | grep photo_enhancer

# Wait for current batch to finish
```

### Disk Space Filling Up

**Check /processed folders:**
```bash
du -sh /volume1/photos/*/processed
du -sh /volume1/photos/*/*/processed

# Total space in /processed
find /volume1/photos -type d -name "processed" -exec du -sb {} + | awk '{sum+=$1} END {print sum/1024/1024/1024 " GB"}'
```

**Delete when ready** (manually, at your discretion).

## Summary

**Photoner handles:**
- ✅ Image enhancement
- ✅ Comprehensive logging
- ✅ Moving originals to /processed
- ✅ Performance tracking
- ✅ Error monitoring
- ✅ Report generation

**You handle:**
- 🗑️ Deleting /processed folders when ready
- 📦 Managing Glacier backups
- 💾 Storage capacity planning
- 🔍 Deciding retention policies

**Keep it simple, keep it focused!**
