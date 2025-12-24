## Record-Keeping & Cleanup Guide

Complete guide to logging, record-keeping, reporting, and safe cleanup of processed originals.

## Overview

Photoner maintains comprehensive records of all processing activities, making it easy to:
- Track what was processed and when
- Monitor error rates and troubleshoot issues
- Generate reports for auditing
- Safely cleanup processed originals (you have Glacier backups!)

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

**Comprehensive records including:**
- Input/output file paths
- File sizes (before/after)
- Processing time
- Success/failure status
- Error messages
- Enhancement adjustments applied
- Whether original was moved to /processed
- Timestamps

**Cleanup tracking:**
- Cleanup dates
- Files deleted per cleanup
- Space freed
- Manifests generated

## The /processed Folder System

### How It Works

After successful enhancement, originals are moved to a `/processed` subfolder:

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
    └── processed/
        ├── photo_001.jpg  ← Moved here (enhanced version in /enhanced)
        ├── photo_002.jpg
        └── photo_003.jpg
```

### Why This Helps

Since you have **Glacier backups**, the originals in `/processed` are redundant:

1. ✓ Original in Glacier (cold storage backup)
2. ✓ Enhanced version in `/enhanced` (production use)
3. ❌ Original in `/processed` (taking up space)

**You can safely delete files in `/processed` to free disk space!**

### Safety Verification

Before deletion, the system verifies:
- Enhanced version exists in `/enhanced`
- Processing status was "success"
- Adjustments were recorded
- File has been processed for N days (configurable)

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
  ✓ Successful: 44,901
  ✗ Failed: 387
  ○ Skipped: 94

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
- Billing records (if selling enhanced photos)
- Audit trails
- Performance analysis

### Cleanup Manifest

```bash
# Files older than 30 days
python scripts/generate_reports.py --report-type cleanup --cleanup-age 30
```

**Output:** `/volume1/photos/logs/reports/cleanup_manifest_2024-12-23_143022.txt`

```
Cleanup Manifest Generated: 2024-12-23T14:30:22
Files older than: 30 days
Total files: 38,492
Total size: 158.73 GB
================================================================================

Files to delete (all have enhanced versions):

/volume1/photos/incoming/2024-11-15/processed/photo_001.jpg    4.23 MB    2024-11-15T08:23:11Z
/volume1/photos/incoming/2024-11-15/processed/photo_002.jpg    3.87 MB    2024-11-15T08:23:15Z
...
```

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

### All Reports at Once

```bash
python scripts/generate_reports.py --report-type all --days 30
```

## Safe Cleanup of Processed Originals

### Dry Run (See What Would Be Deleted)

```bash
# Preview cleanup (older than 30 days)
python scripts/cleanup_processed.py --older-than-days 30 --dry-run
```

**Output:**
```
Analyzing processed files (older than 30 days)...

Ready for cleanup:
  Files: 38,492
  Total Size: 158.73 GB
  Manifest: /volume1/photos/logs/reports/cleanup_manifest_2024-12-23_143022.txt

Sample files (first 10):
  /volume1/photos/incoming/2024-11-15/processed/photo_001.jpg (4.23 MB)
  /volume1/photos/incoming/2024-11-15/processed/photo_002.jpg (3.87 MB)
  ... and 38,482 more

DRY RUN MODE - No files will be deleted
```

### Actual Cleanup

```bash
# Delete processed originals (requires confirmation)
python scripts/cleanup_processed.py --older-than-days 30
```

**Interactive confirmation:**
```
⚠️  WARNING: This will permanently delete these files!
   You mentioned having Glacier backups, but please verify:

   1. Enhanced versions exist in /enhanced directory
   2. Originals are backed up in Glacier
   3. You're ready to free up space

Type 'DELETE' to proceed:
```

**After typing 'DELETE':**
```
Deleting files...
  Deleted 100/38492 files...
  Deleted 200/38492 files...
  ...
  Deleted 38492/38492 files...

✓ Cleanup complete!
  Deleted: 38,492 files
  Freed: 158.73 GB

Cleaning up empty /processed directories...
  Removed empty directory: /volume1/photos/incoming/2024-11-15/processed
  Removed empty directory: /volume1/photos/incoming/2024-11-16/processed
```

### Automated Monthly Cleanup

Add to Synology Task Scheduler:

**Task:** Monthly Cleanup (runs 1st of month at 2 AM)

```bash
source /volume1/photos/photoner/venv/bin/activate && \
python /volume1/photos/photoner/scripts/cleanup_processed.py \
    --older-than-days 60 \
    --confirm \
    >> /volume1/photos/logs/cleanup_cron.log 2>&1
```

**WARNING:** `--confirm` skips the confirmation prompt. Only use in automated scripts after testing!

## Recommended Cleanup Strategy

### Conservative (Recommended for First 3 Months)

```bash
# Only delete files older than 90 days
python scripts/cleanup_processed.py --older-than-days 90
```

**Why:** Gives you time to verify:
- Enhanced versions are acceptable quality
- Glacier backups are working
- No issues with the enhancement process

### Standard (After Comfortable)

```bash
# Delete files older than 30 days
python scripts/cleanup_processed.py --older-than-days 30
```

**Why:** Monthly cleanup keeps storage manageable while maintaining recent originals

### Aggressive (If Disk Space Critical)

```bash
# Delete files older than 7 days
python scripts/cleanup_processed.py --older-than-days 7
```

**Why:** Minimal retention since:
- Originals in Glacier
- Enhanced versions in /enhanced
- Processing is stable

## Monitoring Cleanup History

### View Cleanup History

```bash
# Query the database
sqlite3 /volume1/photos/logs/database/processing_records.db

SELECT
    cleanup_date,
    files_deleted,
    space_freed_gb
FROM cleanup_history
ORDER BY cleanup_date DESC
LIMIT 10;
```

**Output:**
```
2024-12-23T02:00:00Z|38492|158.73
2024-11-23T02:00:00Z|42381|175.29
2024-10-23T02:00:00Z|39204|161.87
```

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
├── processing.log.1        # Yesterday
├── processing.log.2        # 2 days ago
└── processing.log.10       # Oldest
```

**Old logs are automatically deleted** after `backup_count` is reached.

## Query the Database Directly

### Useful SQL Queries

**Total images processed:**
```sql
SELECT COUNT(*) FROM processing_records WHERE status = 'success';
```

**Error rate by day:**
```sql
SELECT
    DATE(timestamp) as date,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_percent
FROM processing_records
WHERE timestamp >= date('now', '-30 days')
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

**Top error messages:**
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

**Processing throughput by hour:**
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

**Files ready for cleanup:**
```sql
SELECT COUNT(*), SUM(original_size_bytes) / 1024.0 / 1024 / 1024 as size_gb
FROM processing_records
WHERE moved_to_processed = 1
AND status = 'success'
AND timestamp <= datetime('now', '-30 days');
```

## Backup the Database

```bash
# Backup processing records database
sqlite3 /volume1/photos/logs/database/processing_records.db ".backup '/volume1/photos/logs/database/processing_records_backup_$(date +%Y%m%d).db'"

# Or using compression
sqlite3 /volume1/photos/logs/database/processing_records.db ".dump" | gzip > processing_records_$(date +%Y%m%d).sql.gz
```

## Troubleshooting

### "Database is locked"

**Cause:** Another process is accessing the database

**Solution:**
```bash
# Check for running processes
ps aux | grep photo_enhancer

# Wait for current batch to finish
# Or kill the process (not recommended during processing)
```

### High Error Rate

```bash
# Get error summary
python scripts/generate_reports.py --report-type errors --days 7

# Check specific errors in log
grep "ERROR" /volume1/photos/logs/errors.log | tail -20
```

### Disk Space Not Freed After Cleanup

**Check:**
1. Files actually deleted (not just moved)
2. Empty `/processed` directories removed
3. Database records accurate

```bash
# Verify /processed directories are empty/gone
find /volume1/photos -type d -name "processed" -exec du -sh {} \;
```

## Best Practices

1. **Start Conservative**
   - Use `--dry-run` first
   - Keep 90-day retention initially
   - Monitor for issues

2. **Verify Glacier Backups**
   - Confirm originals are in Glacier
   - Test restore procedure
   - Document backup locations

3. **Regular Reporting**
   - Weekly error summary
   - Monthly cleanup
   - Quarterly full audit

4. **Monitor Disk Space**
   ```bash
   # Before cleanup
   df -h /volume1

   # After cleanup
   df -h /volume1
   ```

5. **Keep Cleanup Manifests**
   - Store in `/volume1/photos/logs/reports/`
   - Reference if you need to restore
   - Audit trail for compliance

## Automation Schedule

**Weekly Reports (Sunday 8 AM):**
```bash
python scripts/generate_reports.py --report-type all --days 7
```

**Monthly Cleanup (1st of month, 2 AM):**
```bash
python scripts/cleanup_processed.py --older-than-days 60 --confirm
```

**Quarterly Audit (1st of Jan/Apr/Jul/Oct):**
```bash
python scripts/generate_reports.py --report-type all --days 90
```

## Support

**Logs Location:**
- Processing: `/volume1/photos/logs/processing.log`
- Errors: `/volume1/photos/logs/errors.log`
- Database: `/volume1/photos/logs/database/processing_records.db`
- Reports: `/volume1/photos/logs/reports/`

**Scripts:**
- `scripts/generate_reports.py` - Generate all reports
- `scripts/cleanup_processed.py` - Safe cleanup utility
