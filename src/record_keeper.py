"""
Record Keeper for Photoner
Maintains detailed processing records, audit trails, and cleanup reports.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import sqlite3


class RecordKeeper:
    """
    Maintains comprehensive records of all processing activities:
    - SQLite database of processed files
    - CSV export for reporting
    - Audit trail for compliance
    - Cleanup manifests
    """

    def __init__(self, config: Dict[str, Any], logger):
        """
        Initialize record keeper.

        Args:
            config: Configuration dictionary
            logger: PhotonerLogger instance
        """
        self.config = config
        self.logger = logger

        # Database path
        db_dir = Path(config["paths"]["logs"]) / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "processing_records.db"

        # CSV reports path
        self.reports_dir = Path(config["paths"]["logs"]) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main processing records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    output_path TEXT,
                    original_size_bytes INTEGER,
                    enhanced_size_bytes INTEGER,
                    processing_time_sec REAL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    profile TEXT,
                    adjustments TEXT,
                    moved_to_processed BOOLEAN,
                    processed_folder_path TEXT,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_input_path
                ON processing_records(input_path)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON processing_records(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON processing_records(status)
            """)

            # Cleanup tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cleanup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cleanup_date TEXT NOT NULL,
                    files_deleted INTEGER,
                    space_freed_gb REAL,
                    directories_cleaned TEXT,
                    manifest_path TEXT,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

        self.logger.info(f"Record keeper initialized: {self.db_path}")

    def record_processing(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        status: str = "success",
        processing_time: Optional[float] = None,
        error_message: Optional[str] = None,
        adjustments: Optional[Dict[str, Any]] = None,
        moved_to_processed: bool = False,
        processed_folder_path: Optional[Path] = None
    ) -> int:
        """
        Record a processing event in the database.

        Args:
            input_path: Original image path
            output_path: Enhanced image path
            status: "success", "failed", "skipped"
            processing_time: Time taken in seconds
            error_message: Error description if failed
            adjustments: Enhancement adjustments made
            moved_to_processed: Whether original was moved
            processed_folder_path: Where original was moved to

        Returns:
            Record ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get file sizes
            original_size = input_path.stat().st_size if input_path.exists() else None
            enhanced_size = output_path.stat().st_size if output_path and output_path.exists() else None

            cursor.execute("""
                INSERT INTO processing_records (
                    timestamp,
                    input_path,
                    output_path,
                    original_size_bytes,
                    enhanced_size_bytes,
                    processing_time_sec,
                    status,
                    error_message,
                    profile,
                    adjustments,
                    moved_to_processed,
                    processed_folder_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat() + "Z",
                str(input_path),
                str(output_path) if output_path else None,
                original_size,
                enhanced_size,
                processing_time,
                status,
                error_message,
                self.config["enhancement"]["profile"],
                json.dumps(adjustments) if adjustments else None,
                moved_to_processed,
                str(processed_folder_path) if processed_folder_path else None
            ))

            conn.commit()
            record_id = cursor.lastrowid

        return record_id

    def get_processing_stats(self, days: int = 1) -> Dict[str, Any]:
        """
        Get processing statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of statistics
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total counts
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                    AVG(processing_time_sec) as avg_time,
                    SUM(original_size_bytes) as total_original_bytes,
                    SUM(enhanced_size_bytes) as total_enhanced_bytes
                FROM processing_records
                WHERE timestamp >= ?
            """, (cutoff_date,))

            row = cursor.fetchone()

        return {
            "period_days": days,
            "total_processed": row[0] or 0,
            "successful": row[1] or 0,
            "failed": row[2] or 0,
            "skipped": row[3] or 0,
            "avg_processing_time_sec": round(row[4], 2) if row[4] else 0,
            "total_original_size_gb": round((row[5] or 0) / (1024**3), 2),
            "total_enhanced_size_gb": round((row[6] or 0) / (1024**3), 2),
        }

    def export_to_csv(self, output_file: Optional[Path] = None, days: int = 30) -> Path:
        """
        Export processing records to CSV.

        Args:
            output_file: Output CSV path (default: reports/processing_YYYY-MM-DD.csv)
            days: Export records from last N days

        Returns:
            Path to created CSV file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            output_file = self.reports_dir / f"processing_{timestamp}.csv"

        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    timestamp,
                    input_path,
                    output_path,
                    status,
                    processing_time_sec,
                    error_message,
                    moved_to_processed,
                    processed_folder_path
                FROM processing_records
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (cutoff_date,))

            rows = cursor.fetchall()

        # Write CSV
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Timestamp',
                'Original Path',
                'Enhanced Path',
                'Status',
                'Processing Time (sec)',
                'Error',
                'Moved to Processed',
                'Processed Folder Path'
            ])
            writer.writerows(rows)

        self.logger.info(f"Exported {len(rows)} records to {output_file}")
        return output_file

    def get_cleanup_candidates(self) -> List[Dict[str, Any]]:
        """
        Get list of files in /processed folders ready for cleanup.

        Returns:
            List of cleanup candidates with metadata
        """
        candidates = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    input_path,
                    output_path,
                    processed_folder_path,
                    original_size_bytes,
                    timestamp
                FROM processing_records
                WHERE moved_to_processed = 1
                AND status = 'success'
                ORDER BY timestamp
            """)

            for row in cursor.fetchall():
                input_path = Path(row[0])
                processed_path = Path(row[2]) if row[2] else None

                # Check if file still exists in processed folder
                if processed_path and processed_path.exists():
                    candidates.append({
                        "original_location": str(input_path),
                        "current_location": str(processed_path),
                        "enhanced_version": str(row[1]),
                        "size_bytes": row[3],
                        "size_mb": round(row[3] / (1024**2), 2),
                        "processed_date": row[4]
                    })

        return candidates

    def create_cleanup_manifest(self, older_than_days: int = 30) -> Path:
        """
        Create a manifest of files that can be safely deleted.

        Args:
            older_than_days: Only include files processed more than N days ago

        Returns:
            Path to manifest file
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat() + "Z"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        manifest_path = self.reports_dir / f"cleanup_manifest_{timestamp}.txt"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    processed_folder_path,
                    original_size_bytes,
                    timestamp
                FROM processing_records
                WHERE moved_to_processed = 1
                AND status = 'success'
                AND timestamp <= ?
                AND processed_folder_path IS NOT NULL
                ORDER BY timestamp
            """, (cutoff_date,))

            files = cursor.fetchall()

        total_size = sum(row[1] for row in files if row[1])

        with open(manifest_path, 'w') as f:
            f.write(f"Cleanup Manifest Generated: {datetime.now().isoformat()}\n")
            f.write(f"Files older than: {older_than_days} days\n")
            f.write(f"Total files: {len(files)}\n")
            f.write(f"Total size: {total_size / (1024**3):.2f} GB\n")
            f.write("=" * 80 + "\n\n")
            f.write("Files to delete (all have enhanced versions):\n\n")

            for row in files:
                file_path = Path(row[0])
                if file_path.exists():
                    size_mb = row[1] / (1024**2) if row[1] else 0
                    f.write(f"{file_path}\t{size_mb:.2f} MB\t{row[2]}\n")

        self.logger.info(f"Cleanup manifest created: {manifest_path}")
        self.logger.info(f"Ready for cleanup: {len(files)} files ({total_size / (1024**3):.2f} GB)")

        return manifest_path

    def record_cleanup(self, files_deleted: int, space_freed_gb: float, directories: List[str], manifest_path: Path) -> None:
        """
        Record a cleanup operation in the database.

        Args:
            files_deleted: Number of files deleted
            space_freed_gb: Space freed in GB
            directories: List of directories cleaned
            manifest_path: Path to cleanup manifest
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cleanup_history (
                    cleanup_date,
                    files_deleted,
                    space_freed_gb,
                    directories_cleaned,
                    manifest_path
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat() + "Z",
                files_deleted,
                space_freed_gb,
                json.dumps(directories),
                str(manifest_path)
            ))
            conn.commit()

        self.logger.info(f"Cleanup recorded: {files_deleted} files, {space_freed_gb:.2f} GB freed")

    def get_error_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get summary of errors for troubleshooting.

        Args:
            days: Number of days to analyze

        Returns:
            List of error summaries
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    error_message,
                    COUNT(*) as count,
                    MAX(timestamp) as last_occurrence
                FROM processing_records
                WHERE status = 'failed'
                AND timestamp >= ?
                AND error_message IS NOT NULL
                GROUP BY error_message
                ORDER BY count DESC
            """, (cutoff_date,))

            errors = []
            for row in cursor.fetchall():
                errors.append({
                    "error": row[0],
                    "count": row[1],
                    "last_seen": row[2]
                })

        return errors


from datetime import timedelta
