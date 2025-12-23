# Product Requirements Document: Automated Newspaper Photo Enhancement System

**Project Name:** UpstateToday Photo Enhancement Pipeline  
**Version:** 1.0  
**Date:** December 21, 2024  
**Author:** John (UpstateToday.com)  
**Target Platform:** Synology DS1522+ NAS

---

## 1. Executive Summary

### 1.1 Problem Statement
UpstateToday.com has accumulated years of newspaper photographs that have never been published online or made available for sale because:
- Photographers only prep 1-2 photos for print deadline, leaving remaining shots unprocessed
- Archive images from older coverage were never digitally enhanced
- New images arrive 8 times daily with no staff capacity for basic toning/enhancement
- Potential revenue from photo sales is lost due to unprocessed inventory

### 1.2 Solution Overview
Develop an automated photo enhancement system that runs on existing Synology NAS infrastructure to:
- Process incoming photos automatically (8x daily uploads)
- Enhance archived newspaper photos during off-hours
- Preserve original image quality and metadata
- Prepare photos for sale via Cloudspot.io integration
- Require zero manual intervention once configured

### 1.3 Success Criteria
- **Functional:** 95%+ of photos successfully enhanced without manual intervention
- **Quality:** Enhanced photos match or exceed manual photographer adjustments
- **Performance:** Archive processing completes within 30 days; incoming photos within 2 hours
- **Reliability:** System runs unattended for weeks without crashes
- **Data Safety:** Zero loss of original images or metadata

---

## 2. Technical Specifications

### 2.1 Hardware Environment
- **Device:** Synology DS1522+
- **CPU:** Intel Celeron J4125 (quad-core, 2.0-2.7 GHz)
- **RAM:** 2GB (no upgrade)
- **Storage:** 25TB available
- **OS:** DSM 7.x (latest)
- **Network:** Gigabit Ethernet

### 2.2 Input Specifications
**File Formats:**
- Primary: JPEG (.jpg, .jpeg)
- Secondary: RAW formats (.cr2, .nef, .arw, .dng) - convert to JPEG
- Rare: TIFF (.tif, .tiff) - treat as JPEG

**File Characteristics:**
- Resolution: Variable (likely 3000x2000 to 6000x4000 pixels)
- File Size: 2MB to 25MB per image (estimated)
- EXIF Data: Must be preserved (photographer credits, dates, camera settings)
- Color Space: sRGB or Adobe RGB
- Volume: Thousands of archive images + ~50-200 new images daily

### 2.3 Output Specifications
**Processed Images:**
- Format: JPEG
- Quality: 95% (high quality, minimal compression)
- Resolution: Original resolution preserved (no resizing)
- Color Space: sRGB (web-standard)
- EXIF: All original metadata preserved
- File Naming: Original filename + "_enhanced" suffix

**Storage Requirements:**
- Originals: Never modified, remain in place
- Processed: Separate directory structure
- Backup: Optional redundant copy of originals before processing

---

## 3. System Architecture

### 3.1 Directory Structure
```
/volume1/photos/
├── incoming/                    # 8x daily uploads land here
│   ├── [date]/                 # Organized by upload date
│   └── processed/              # Move here after enhancement
├── archive/                     # Years of old newspaper photos
│   ├── [year]/[month]/        # Organized chronologically
│   └── processed/              # Move here after enhancement
├── enhanced/                    # All enhanced output goes here
│   ├── incoming/[date]/       # Enhanced versions of new uploads
│   └── archive/[year]/[month]/ # Enhanced versions of archive
├── originals_backup/           # Safety copy (optional)
│   └── [timestamp]/           # Timestamped backups
└── logs/                       # Processing logs and reports
    ├── processing.log         # Main log file
    ├── errors.log            # Error tracking
    └── reports/              # Daily/weekly summary reports
```

### 3.2 Processing Pipeline

**Stage 1: Discovery**
- Scan target directory for unprocessed images
- Filter by file extension (.jpg, .jpeg, .raw, .cr2, .nef, etc.)
- Check if already processed (avoid duplicates)
- Build processing queue with priority ordering

**Stage 2: Pre-Processing**
- Validate file integrity (not corrupted)
- Read EXIF metadata
- Determine file type (JPEG vs RAW)
- Create backup reference (optional safety step)

**Stage 3: Enhancement**
- Load image into memory
- Apply auto-enhancement algorithms:
  - Histogram equalization (contrast improvement)
  - Auto white balance
  - Brightness/exposure correction
  - Color saturation optimization
  - Sharpening (subtle, newspaper-appropriate)
  - Noise reduction (if needed for older/high-ISO images)
- Preserve aspect ratio and resolution

**Stage 4: Output**
- Save enhanced image to target directory
- Copy all EXIF metadata to enhanced version
- Set JPEG quality to 95%
- Create processing record (log entry)

**Stage 5: Post-Processing**
- Move original to "processed" subfolder (or leave in place)
- Update processing database/log
- Generate statistics (processing time, adjustments made)
- Handle errors gracefully (log and continue)

### 3.3 Component Architecture

**Python Script Components:**

1. **Main Controller** (`photo_enhancer.py`)
   - Orchestrates entire pipeline
   - Manages configuration
   - Handles scheduling logic

2. **Image Processor** (`processor.py`)
   - OpenCV-based enhancement engine
   - RAW file handling (using rawpy library)
   - EXIF preservation

3. **File Manager** (`file_manager.py`)
   - Directory scanning
   - File validation
   - Safe file operations (atomic writes)

4. **Logger** (`logger.py`)
   - Structured logging
   - Error tracking
   - Performance metrics

5. **Configuration** (`config.yaml`)
   - Processing parameters
   - Directory paths
   - Enhancement presets

---

## 4. Enhancement Algorithms

### 4.1 Auto-Enhancement Strategy

**Primary Approach: OpenCV-based Processing**

The system will apply a series of enhancement operations designed for newspaper photography:

1. **Histogram Equalization (Adaptive CLAHE)**
   - Contrast Limited Adaptive Histogram Equalization
   - Improves local contrast without over-brightening highlights
   - Clip limit: 2.0-3.0
   - Tile grid: 8x8

2. **White Balance Correction**
   - Gray world assumption algorithm
   - Adjusts color temperature automatically
   - Preserves skin tones (important for event/portrait photography)

3. **Brightness/Exposure Auto-Correction**
   - Analyze histogram distribution
   - Adjust exposure to optimal range (5th-95th percentile)
   - Avoid clipping highlights or crushing shadows

4. **Color Saturation Enhancement**
   - Subtle boost to vibrancy (10-20%)
   - Prevent oversaturation (clip at realistic values)
   - Preserve natural skin tones

5. **Sharpening (Unsharp Mask)**
   - Radius: 1.0-2.0 pixels
   - Amount: 0.5-1.0
   - Threshold: 0 (apply to all pixels)
   - Compensates for slight softness in older scans

6. **Noise Reduction (Conditional)**
   - Only apply if ISO > 800 (detected from EXIF)
   - Non-local means denoising
   - Preserve edge detail

### 4.2 Special Handling

**RAW Files:**
- Use `rawpy` library to decode
- Apply camera-specific color profiles when available
- Convert to 16-bit intermediate, then 8-bit JPEG output
- Slightly more aggressive enhancement (RAW files are "flatter")

**Very Dark/Underexposed Images:**
- Additional gamma correction
- Shadow lifting without introducing noise
- Flag for manual review if severely underexposed

**Very Bright/Overexposed Images:**
- Highlight recovery (if data exists in file)
- Reduce global brightness
- Flag for manual review if highlights are clipped

### 4.3 Processing Presets

The system will support multiple enhancement profiles:

**Conservative (Default):**
- Subtle improvements
- Maximum preservation of original look
- Best for already-decent photos

**Aggressive:**
- Stronger corrections
- For poorly exposed or old scans
- Use on archive images from earlier eras

**Custom:**
- User-defined parameters via config file
- Ability to tune per-photographer style preferences

---

## 5. Operational Requirements

### 5.1 Processing Schedules

**Incoming Photos (Priority Processing):**
- **Trigger:** New files detected in `/incoming/` directory
- **Frequency:** Every 2 hours during business hours (6am-10pm)
- **Batch Size:** Up to 500 images per run (estimated 1-2 hours processing)
- **Resource Limit:** 70% CPU, 1.5GB RAM max

**Archive Photos (Background Processing):**
- **Trigger:** Scheduled task
- **Frequency:** Nightly, 11pm-6am (7-hour window)
- **Batch Size:** 2,000-5,000 images per night (depends on size/complexity)
- **Resource Limit:** 90% CPU, 1.8GB RAM max
- **Completion Goal:** Process entire archive within 30 days

**Error Recovery:**
- Retry failed images once before logging as error
- Daily summary of failures sent to log
- Manual review queue for problematic images

### 5.2 Performance Expectations

**Processing Speed (Estimated):**
- JPEG (4000x3000): 2-5 seconds per image
- RAW (6000x4000): 8-15 seconds per image
- Throughput: 720-1,800 JPEG/hour, 240-450 RAW/hour

**Resource Consumption:**
- CPU: Will spike to 70-90% during processing (expected)
- RAM: 200-400MB per image in processing
- Disk I/O: Sequential reads/writes (NAS-friendly)
- Network: None (all local processing)

### 5.3 Monitoring & Alerts

**Daily Health Check:**
- Images processed in last 24 hours
- Error rate (should be <5%)
- Disk space remaining
- Processing queue size

**Alert Conditions:**
- Error rate >10%
- Processing stopped for >4 hours during scheduled time
- Disk space <1TB remaining
- Memory errors or crashes

---

## 6. Data Safety & Quality Assurance

### 6.1 Data Protection

**Original Files:**
- NEVER modify original files in place
- Always write to separate output directory
- Optional: Create timestamped backup before first processing run
- Implement atomic file operations (write to temp, then move)

**EXIF Metadata Preservation:**
- Copy all EXIF tags to enhanced images
- Preserve: Camera model, lens, exposure settings, GPS, copyright, photographer
- Add: Processing software tag ("OpenCV Auto-Enhance v1.0")
- Add: Processing timestamp in EXIF

**Filesystem Safety:**
- Check available disk space before processing
- Abort if <10GB free space
- Verify write success before marking as processed
- Handle filename collisions (append counter)

### 6.2 Quality Control

**Automated Quality Checks:**
- Verify output file is not corrupted
- Check that resolution matches input
- Validate EXIF data was preserved
- Compare file size (should be similar, not drastically different)

**Sample Review Process:**
- Every 100th enhanced image flagged for manual spot-check
- Generate side-by-side comparison HTML reports
- Log images with extreme adjustments for review

**Rollback Capability:**
- Keep processing log with input/output file paths
- Ability to delete enhanced versions and re-process
- Version control for enhancement parameters

---

## 7. Implementation Plan

### 7.1 Development Phases

**Phase 1: Core Processor (Week 1)**
- Set up Python environment on Synology
- Install dependencies (OpenCV, rawpy, Pillow, piexif)
- Build basic enhancement pipeline
- Test on 10-20 sample images
- Validate EXIF preservation

**Phase 2: File Management (Week 1-2)**
- Implement directory scanning
- Build processing queue
- Create safe file operations
- Add duplicate detection
- Test on 100 sample images

**Phase 3: Logging & Monitoring (Week 2)**
- Structured logging system
- Error tracking and reporting
- Performance metrics collection
- Daily summary reports

**Phase 4: Scheduling & Automation (Week 2-3)**
- Configure Synology Task Scheduler
- Set up incoming photo monitoring
- Configure archive processing schedule
- Test unattended operation for 48 hours

**Phase 5: Production Deployment (Week 3)**
- Process small test batch from archive (1,000 images)
- Manual quality review
- Tune enhancement parameters if needed
- Launch full production processing

**Phase 6: Optimization (Ongoing)**
- Monitor performance
- Adjust batch sizes for optimal throughput
- Fine-tune enhancement algorithms based on results
- Add features as needed

### 7.2 Testing Strategy

**Unit Testing:**
- Test each enhancement algorithm independently
- Verify EXIF preservation
- Test RAW conversion
- Error handling for corrupted files

**Integration Testing:**
- Full pipeline with sample dataset
- Directory management
- Logging accuracy
- Resource consumption monitoring

**Load Testing:**
- Process 1,000 images to verify stability
- Monitor memory usage over time
- Check for memory leaks
- Validate error recovery

**User Acceptance Testing:**
- Manual review of 50 enhanced images
- Compare quality to photographer-adjusted images
- Verify Cloudspot.io compatibility
- Confirm EXIF data intact

---

## 8. Dependencies & Installation

### 8.1 Software Requirements

**Python Environment:**
- Python 3.8+ (available on DSM 7)
- pip package manager

**Required Python Libraries:**
```
opencv-python==4.8.1.78        # Core image processing
rawpy==0.18.1                  # RAW file handling
Pillow==10.1.0                 # Additional image operations
piexif==1.1.3                  # EXIF metadata handling
numpy==1.24.3                  # Array operations (OpenCV dependency)
pyyaml==6.0.1                  # Configuration file parsing
tqdm==4.66.1                   # Progress bars (optional, helpful)
```

**System Packages (via Synology Package Center):**
- Python 3.9 or 3.10
- Git (for version control, optional)

### 8.2 Installation Steps

1. SSH into Synology NAS
2. Install Python 3 via Package Center
3. Create virtual environment: `python3 -m venv /volume1/photos/venv`
4. Activate venv: `source /volume1/photos/venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Configure directory structure
7. Set up Task Scheduler jobs
8. Run test batch

---

## 9. Configuration Management

### 9.1 Configuration File Structure

**config.yaml:**
```yaml
# Directory Paths
paths:
  incoming: /volume1/photos/incoming
  archive: /volume1/photos/archive
  enhanced: /volume1/photos/enhanced
  logs: /volume1/photos/logs
  backup: /volume1/photos/originals_backup  # optional

# Processing Settings
processing:
  jpeg_quality: 95
  preserve_resolution: true
  max_batch_size: 500
  processing_threads: 2  # Conservative for 2GB RAM
  
# Enhancement Parameters
enhancement:
  profile: conservative  # conservative | aggressive | custom
  
  clahe:
    clip_limit: 2.5
    tile_grid_size: 8
  
  sharpening:
    radius: 1.5
    amount: 0.7
    threshold: 0
  
  saturation_boost: 1.15  # 15% increase
  
  noise_reduction:
    enabled: true
    iso_threshold: 800  # Only apply if ISO > 800
    strength: 5

# Scheduling
schedule:
  incoming:
    enabled: true
    check_interval_hours: 2
    business_hours: "6-22"  # 6am to 10pm
    
  archive:
    enabled: true
    start_time: "23:00"  # 11pm
    max_duration_hours: 7
    daily_target: 3000  # images per night

# Quality Control
quality:
  spot_check_frequency: 100  # Every 100th image
  generate_comparison_html: true
  flag_extreme_adjustments: true

# Logging
logging:
  level: INFO  # DEBUG | INFO | WARNING | ERROR
  max_log_size_mb: 100
  backup_count: 5
  daily_summary: true
```

### 9.2 Tunable Parameters

Users can adjust via config file:
- Enhancement strength (conservative vs aggressive)
- CLAHE parameters
- Sharpening intensity
- Saturation boost amount
- Noise reduction threshold
- Batch sizes
- Processing schedules
- Logging verbosity

---

## 10. Error Handling & Edge Cases

### 10.1 Common Error Scenarios

**Corrupted Files:**
- Detect via file validation
- Log error with filename
- Skip and continue processing
- Flag for manual review

**Unsupported Formats:**
- Log unsupported file type
- Skip processing
- Option to convert or ignore

**Insufficient Disk Space:**
- Pre-flight check before batch
- Abort processing if <10GB free
- Send alert
- Resume when space available

**Memory Errors:**
- Catch out-of-memory exceptions
- Reduce batch size automatically
- Process larger files one at a time
- Log incident

**EXIF Read/Write Failures:**
- Attempt processing without EXIF
- Log warning
- Still save enhanced image
- Flag for manual EXIF restoration

### 10.2 Recovery Mechanisms

**Crash Recovery:**
- Maintain processing state file
- Resume from last successful image
- Avoid re-processing completed images

**Duplicate Prevention:**
- Check if output file already exists
- Skip if timestamp newer than source
- Option to force re-process if needed

**Bad Output Detection:**
- Verify output file size >0
- Check image can be opened
- Validate dimensions match input
- Delete and retry if corrupted

---

## 11. Future Enhancements (Post-MVP)

### 11.1 Potential Features

**Machine Learning Integration:**
- Train custom model on photographer-adjusted images
- Learn newspaper's specific enhancement preferences
- Implement person/face detection for optimal crop suggestions

**Advanced Organization:**
- Auto-tagging based on image content
- Facial recognition for photographer/subject indexing
- GPS-based location tagging

**Web Interface:**
- Browser-based dashboard for monitoring
- Manual override/re-processing controls
- Before/after comparison viewer
- Processing queue management

**Performance Optimization:**
- GPU acceleration (if NAS upgraded)
- Multi-threading improvements
- Distributed processing across multiple NAS units

**Integration Features:**
- Direct API push to Cloudspot.io
- Automatic watermarking before upload
- Metadata synchronization with CMS

### 11.2 Scalability Considerations

**If Archive Grows Significantly:**
- Implement priority queuing (sell-worthy images first)
- Add incremental processing checkpoints
- Consider distributed processing

**If Processing Too Slow:**
- Upgrade NAS RAM to 32GB (DS1522+ supports it)
- Optimize OpenCV operations
- Consider dedicated processing server

---

## 12. Success Metrics & KPIs

### 12.1 Performance Metrics

**Processing Efficiency:**
- Images processed per hour
- Error rate (target: <5%)
- Average processing time per image
- Queue backlog size

**Quality Metrics:**
- Percentage of images requiring manual adjustment (target: <10%)
- Photographer satisfaction rating
- Sales conversion rate for enhanced photos

**System Health:**
- Uptime percentage (target: >99%)
- Failed processing runs
- Disk space utilization
- Memory/CPU stability

### 12.2 Business Impact

**Short-term (3 months):**
- Archive processing 80% complete
- All incoming photos enhanced within 4 hours
- Zero data loss incidents
- Positive photographer feedback

**Long-term (12 months):**
- Entire archive processed and searchable
- Photo sales revenue increase (measurable)
- Reduced staff time on manual enhancement
- System runs with minimal intervention

---

## 13. Risk Assessment

### 13.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss/corruption | Low | Critical | Backup originals, atomic writes, extensive testing |
| Insufficient NAS performance | Medium | High | Conservative batch sizing, monitor resources, upgrade path |
| Poor enhancement quality | Medium | Medium | Tunable parameters, spot-checking, manual override |
| Script crashes/hangs | Medium | Medium | Error handling, crash recovery, monitoring |
| Disk space exhaustion | Low | High | Pre-flight checks, alerts, auto-pause |

### 13.2 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Photos unusable for sale | Low | High | Quality control, manual review process |
| Processing takes too long | Medium | Medium | Phased approach, prioritize valuable images |
| EXIF data loss | Low | Critical | Extensive testing, validation |
| System requires constant maintenance | Low | Medium | Robust error handling, clear documentation |

---

## 14. Acceptance Criteria

### 14.1 MVP Completion Requirements

**Functional Requirements:**
- ✅ Process JPEG files with auto-enhancement
- ✅ Convert RAW files to enhanced JPEG
- ✅ Preserve all EXIF metadata
- ✅ Maintain original resolution
- ✅ Never modify original files
- ✅ Process incoming photos automatically
- ✅ Process archive photos on schedule
- ✅ Generate processing logs

**Quality Requirements:**
- ✅ <5% error rate on test dataset
- ✅ Enhanced images match or exceed manual adjustments (subjective review)
- ✅ EXIF data 100% preserved
- ✅ Zero data loss in testing

**Performance Requirements:**
- ✅ Process 500+ JPEG/hour
- ✅ Run unattended for 7+ days without intervention
- ✅ Memory usage stable over time
- ✅ CPU usage within acceptable limits

**Operational Requirements:**
- ✅ Documentation complete
- ✅ Configuration file working
- ✅ Task Scheduler jobs configured
- ✅ Monitoring/alerts functional

### 14.2 Sign-off

**Stakeholder:** John (UpstateToday.com)

**Approval Criteria:**
- Test batch of 1,000 images processed successfully
- Manual review shows acceptable quality
- System runs autonomously for 1 week
- Documentation allows for future maintenance

---

## 15. Documentation Deliverables

### 15.1 Required Documentation

1. **Installation Guide** - Step-by-step setup on Synology
2. **User Manual** - How to monitor, tune, and maintain
3. **Configuration Reference** - All config.yaml parameters explained
4. **Troubleshooting Guide** - Common issues and solutions
5. **Code Documentation** - Inline comments and module descriptions
6. **Processing Reports** - Sample daily/weekly reports

### 15.2 Maintenance Plan

**Weekly Tasks:**
- Review processing logs
- Check error rate
- Verify disk space

**Monthly Tasks:**
- Review quality spot-checks
- Tune enhancement parameters if needed
- Clean old log files

**Quarterly Tasks:**
- Review system performance
- Consider parameter adjustments
- Plan feature enhancements

---

## 16. Glossary

**CLAHE:** Contrast Limited Adaptive Histogram Equalization - advanced contrast enhancement  
**EXIF:** Exchangeable Image File Format - metadata embedded in photos  
**OpenCV:** Open Computer Vision - image processing library  
**RAW:** Unprocessed camera sensor data requiring conversion  
**Histogram Equalization:** Technique to improve image contrast  
**White Balance:** Color temperature adjustment for natural colors  
**Unsharp Mask:** Sharpening technique  
**Non-local Means:** Advanced noise reduction algorithm  
**Atomic Write:** Safe file operation that prevents partial writes  

---

## 17. Appendices

### Appendix A: Sample Processing Log Entry
```json
{
  "timestamp": "2024-12-21T03:45:12Z",
  "input_file": "/volume1/photos/archive/2018/03/IMG_4521.jpg",
  "output_file": "/volume1/photos/enhanced/archive/2018/03/IMG_4521_enhanced.jpg",
  "processing_time_sec": 3.2,
  "enhancement_profile": "conservative",
  "adjustments": {
    "brightness_delta": "+0.15",
    "contrast_delta": "+0.23",
    "saturation_delta": "+0.12",
    "sharpening_applied": true,
    "noise_reduction_applied": false
  },
  "input_size_mb": 4.2,
  "output_size_mb": 4.5,
  "exif_preserved": true,
  "status": "success"
}
```

### Appendix B: Sample Error Log Entry
```json
{
  "timestamp": "2024-12-21T04:12:33Z",
  "input_file": "/volume1/photos/archive/2015/07/DSC_9821.NEF",
  "error_type": "RAWDecodeError",
  "error_message": "Unable to decode RAW file: unsupported camera model",
  "retry_attempted": true,
  "retry_success": false,
  "action_taken": "Flagged for manual review",
  "status": "failed"
}
```

### Appendix C: Resource Links

- OpenCV Documentation: https://docs.opencv.org/
- rawpy Documentation: https://letmaik.github.io/rawpy/
- Synology DSM Task Scheduler: https://kb.synology.com/
- Python EXIF Libraries: https://piexif.readthedocs.io/

---

**END OF DOCUMENT**

---

## Quick Start Checklist for Claude Code

When implementing this system, prioritize in this order:

1. ✅ Set up directory structure
2. ✅ Install Python dependencies
3. ✅ Build core enhancement engine (processor.py)
4. ✅ Test on 10 sample images
5. ✅ Add EXIF preservation
6. ✅ Build file manager (scanning, queue)
7. ✅ Add logging system
8. ✅ Test on 100 sample images
9. ✅ Create configuration file
10. ✅ Set up Task Scheduler
11. ✅ Run production test (1,000 images)
12. ✅ Deploy to full archive

**Critical Success Factors:**
- Never modify originals
- Always preserve EXIF
- Graceful error handling
- Conservative resource usage (2GB RAM limit)
- Extensive logging for debugging
