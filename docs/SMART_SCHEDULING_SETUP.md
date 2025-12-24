# Smart Scheduling Setup Guide

Complete guide for setting up intelligent, NAS-friendly photo processing that works around Google Drive syncs and peak usage times.

## Overview

Your scheduling requirements:
- **Google Drive sync**: Every 3 hours (12am, 3am, 6am, 9am, 12pm, 3pm, 6pm, 9pm)
- **Archive processing**: 1 AM - 3 AM (deep night, 2-hour window)
- **Current photo catchup**: 3 AM - 8 AM (early morning, 5-hour window)
- **Periodic checking**: After hours, minimal impact

## Smart Scheduling Strategy

### Visual Timeline

```
Midnight                                                    Midnight
│                                                                  │
├─12:00 AM─┐                                                      │
│          │ Google Drive Sync                                    │
├─12:15 AM─┘                                                      │
│                                                                  │
├─1:00 AM──┐                                                      │
│          │ ARCHIVE PROCESSING (Deep Night)                      │
│          │ • 2,000 images max                                   │
│          │ • Oldest first (methodical)                          │
│          │ • 2 threads, conservative                            │
├─3:00 AM──┤ Google Drive Sync                                   │
│          │                                                       │
├─3:10 AM──┤                                                      │
│          │ CURRENT PHOTOS CATCHUP (Early Morning)               │
│          │ • 1,500 images per batch                             │
│          │ • Newest first (most relevant)                       │
│          │ • 2 threads                                          │
├─5:50 AM──┤ PAUSE (Google Drive sync buffer)                    │
├─6:00 AM──┤ Google Drive Sync                                   │
├─6:10 AM──┤ RESUME CATCHUP                                      │
│          │                                                       │
├─7:45 AM──┘ Stop before business hours                          │
│                                                                  │
├─8:00 AM──┐                                                      │
│          │ BUSINESS HOURS (No processing)                       │
│          │                                                       │
├─6:00 PM──┘                                                      │
│                                                                  │
├─9:00 PM──┤ Google Drive Sync                                   │
├─9:15 PM──┐                                                      │
│          │ PERIODIC CHECK (Evening)                             │
│          │ • 200 images max                                     │
│          │ • 1 thread, minimal impact                           │
├─11:45 PM─┘                                                      │
│                                                                  │
└─Midnight                                                         │
```

## Configuration File Setup

### 1. Update Paths in config.production-nas.yaml

```yaml
paths:
  # CURRENT PHOTOS - Where Google Drive syncs to
  incoming: /volume1/photos/current_photos  # UPDATE THIS PATH

  # ARCHIVE - Historical photos location
  archive: /volume1/photos/archives  # UPDATE THIS PATH

  # OUTPUT - Enhanced photos
  enhanced: /volume1/photos/enhanced

  # LOGS
  logs: /volume1/photos/logs
```

### 2. Verify Google Drive Sync Times

```yaml
scheduling:
  google_drive_sync_times:
    - "00:00"
    - "03:00"
    - "06:00"
    - "09:00"
    - "12:00"
    - "15:00"
    - "18:00"
    - "21:00"
```

**IMPORTANT:** Update these if your Google Drive sync runs at different times!

### 3. Adjust Resource Limits (If Needed)

Based on your NAS performance, you may want to adjust:

```yaml
resources:
  # Archive (1-3 AM) - Can be more aggressive
  archive:
    max_batch_size: 2000  # Lower if NAS struggles
    processing_threads: 2  # 1-3 depending on CPU

  # Catchup (3-8 AM) - Moderate
  current_catchup:
    max_batch_size: 1500
    processing_threads: 2

  # Periodic (evening) - Minimal
  current_periodic:
    max_batch_size: 200
    processing_threads: 1
```

## Synology Task Scheduler Setup

### Single Cron Job (Every 30 Minutes)

The smart scheduler decides what to run based on the time of day.

**Settings:**
- **Task Name:** `Photoner Smart Scheduler`
- **User:** `admin` (or your admin account)
- **Schedule:** Every 30 minutes, 24/7
  - **Repeat:** Custom
  - **Cron Expression:** `*/30 * * * *`
- **Send run details by email:** Optional
- **Task Settings > Run command:**

```bash
/volume1/photos/photoner/scripts/cron_scheduler.sh
```

**That's it!** One cron job handles everything.

### How It Works

The smart scheduler checks:
1. **Current time** → What phase should be running?
2. **Google Drive sync** → Are we in/near a sync window?
3. **NAS resources** → Is system under stress?
4. **Processing queue** → Are there files to process?

Then runs the appropriate processing mode.

## Testing the Smart Scheduler

### 1. Manual Test

```bash
# SSH into NAS
ssh admin@YOUR_NAS_IP

# Activate environment
cd /volume1/photos/photoner
source venv/bin/activate

# Test scheduler (won't run outside time windows)
python scripts/smart_scheduler.py config/config.production-nas.yaml
```

**Expected output:**
```
Smart Scheduler Starting
Archive Processing: NO (outside time window)
Current Catchup: NO (outside time window)
Current Periodic: NO (outside time window)
No processing scheduled for current time
```

### 2. Force Test Archive Processing

Temporarily edit config to allow current time:

```yaml
scheduling:
  archive_processing:
    start_time: "00:00"  # Change to current hour
    end_time: "23:59"    # Allow all day
```

Then run:
```bash
python scripts/smart_scheduler.py config/config.production-nas.yaml
```

Should process archive images.

### 3. Check Logs

```bash
# Scheduler decisions
tail -f /volume1/photos/logs/scheduler.log

# Processing details
tail -f /volume1/photos/logs/processing.log

# Cron execution
tail -f /volume1/photos/logs/cron_scheduler.log
```

## Monitoring

### Check Processing Progress

```bash
# Count enhanced images
find /volume1/photos/enhanced -name "*_enhanced.jpg" | wc -l

# Check error rate
grep "ERROR" /volume1/photos/logs/processing.log | wc -l

# View recent batches
grep "Batch processing complete" /volume1/photos/logs/processing.log | tail -5
```

### Check Scheduler Activity

```bash
# Last 24 hours of scheduler runs
grep "Smart Scheduler" /volume1/photos/logs/scheduler.log | tail -50

# Archive processing runs
grep "Archive Processing: YES" /volume1/photos/logs/scheduler.log

# Catchup runs
grep "Current Catchup: YES" /volume1/photos/logs/scheduler.log
```

### Resource Usage

```bash
# CPU and memory
top

# Disk space
df -h /volume1

# Active processes
ps aux | grep python
```

## Optimization Tips

### If Archive Processing is Too Slow

```yaml
resources:
  archive:
    max_batch_size: 3000  # Increase from 2000
    processing_threads: 3  # Increase from 2
```

### If NAS Gets Overwhelmed

```yaml
resources:
  archive:
    max_batch_size: 1000  # Decrease
    processing_threads: 1  # Decrease
```

Add resource monitoring:

```yaml
nas_optimizations:
  check_system_load: true
  max_cpu_percent: 80  # Lower threshold
  auto_reduce_load_on_stress: true
```

### If Google Drive Sync Conflicts

Increase buffer:

```yaml
scheduling:
  sync_pause_buffer_minutes: 15  # Increase from 10
```

### If Catching Up Takes Too Long

Extend catchup window:

```yaml
scheduling:
  current_catchup:
    start_time: "03:10"
    end_time: "08:00"  # Extend to 8 AM instead of 7:45
```

Or add more periodic windows:

```yaml
scheduling:
  current_periodic:
    allowed_windows:
      - start: "21:15"
        end: "23:45"
      - start: "00:15"
        end: "00:45"
      # Add lunchtime window
      - start: "12:15"
        end: "12:45"
```

## Troubleshooting

### Scheduler Not Running Anything

**Check:**
1. Is current time in a processing window?
2. Are there unprocessed files?
3. Is sync window active?

```bash
# Check current time windows
python -c "
from datetime import datetime
print(f'Current time: {datetime.now().strftime(\"%H:%M\")}'
"

# Check for unprocessed files
find /volume1/photos/current_photos -name "*.jpg" | head -5
find /volume1/photos/archives -name "*.jpg" | head -5
```

### Lockfile Error

If scheduler says "already running" but nothing is running:

```bash
# Remove stale lockfile
rm -f /tmp/photoner_scheduler.lock
```

### Processing Stops During Sync

**Expected behavior!** The scheduler pauses during Google Drive sync to avoid conflicts.

Check logs:
```bash
grep "sync window" /volume1/photos/logs/scheduler.log
```

### Out of Disk Space

Check thresholds:

```yaml
advanced:
  min_free_space_gb: 50  # Increase if getting warnings
```

Monitor space:
```bash
df -h /volume1
```

## Advanced: Multi-Phase Deployment

### Week 1: Archive Only

Disable current photo processing while testing:

```yaml
scheduling:
  current_catchup:
    enabled: false
  current_periodic:
    enabled: false
```

Monitor archive processing for one week.

### Week 2: Enable Catchup

Once comfortable with archive processing:

```yaml
scheduling:
  current_catchup:
    enabled: true
```

### Week 3: Enable Periodic

After catchup is complete:

```yaml
scheduling:
  current_periodic:
    enabled: true
```

## Performance Expectations

### Archive Processing (1-3 AM, 2 hours)

- **Target:** 2,000 images/night
- **Speed:** ~1,000 images/hour
- **Complete archive:** Depends on size (30-60 days for 60,000 images)

### Current Catchup (3-8 AM, 5 hours)

- **Target:** 5,000 images total
- **Speed:** ~1,000 images/hour
- **Should catch up:** Within 1-2 weeks of backlog

### Periodic (Evening, 30 min)

- **Target:** 200 images/run
- **Frequency:** Every 30 minutes during windows
- **Purpose:** Keep current with new uploads

## Support

**Documentation:**
- Configuration: `config/config.production-nas.yaml`
- Scheduler code: `scripts/smart_scheduler.py`
- Cron wrapper: `scripts/cron_scheduler.sh`

**Logs:**
- Scheduler: `/volume1/photos/logs/scheduler.log`
- Processing: `/volume1/photos/logs/processing.log`
- Cron: `/volume1/photos/logs/cron_scheduler.log`

**Issues:**
Report on GitHub: https://github.com/binarybcc/photoner/issues
