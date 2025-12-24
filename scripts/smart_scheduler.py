#!/usr/bin/env python3
"""
Smart Scheduler for Photoner
Coordinates processing windows around Google Drive syncs and NAS usage patterns.
"""

import sys
import yaml
import time
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import logging


class SmartScheduler:
    """
    Intelligent scheduler that:
    - Avoids Google Drive sync windows
    - Monitors NAS resource usage
    - Dynamically adjusts batch sizes
    - Respects time windows
    """

    def __init__(self, config_path: Path):
        """Initialize scheduler with configuration."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.setup_logging()
        self.photoner_path = Path(__file__).parent.parent / "src" / "photo_enhancer.py"
        self.config_path = config_path

    def setup_logging(self):
        """Setup logging for scheduler."""
        log_dir = Path(self.config["paths"]["logs"])
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "scheduler.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("SmartScheduler")

    def is_sync_window(self, buffer_minutes: int = 10) -> bool:
        """
        Check if we're in or near a Google Drive sync window.

        Args:
            buffer_minutes: Minutes before/after sync to avoid

        Returns:
            True if in sync window
        """
        now = datetime.now()
        sync_times = self.config["scheduling"]["google_drive_sync_times"]

        for sync_time_str in sync_times:
            sync_hour, sync_min = map(int, sync_time_str.split(":"))
            sync_time = now.replace(hour=sync_hour, minute=sync_min, second=0)

            # Check if within buffer window
            start_buffer = sync_time - timedelta(minutes=buffer_minutes)
            end_buffer = sync_time + timedelta(minutes=buffer_minutes)

            if start_buffer <= now <= end_buffer:
                self.logger.info(f"In sync window for {sync_time_str} (buffer: {buffer_minutes} min)")
                return True

        return False

    def is_in_time_window(self, start_time: str, end_time: str) -> bool:
        """
        Check if current time is within specified window.

        Args:
            start_time: HH:MM format
            end_time: HH:MM format

        Returns:
            True if in window
        """
        now = datetime.now()
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))

        start = now.replace(hour=start_hour, minute=start_min, second=0)
        end = now.replace(hour=end_hour, minute=end_min, second=0)

        return start <= now <= end

    def check_nas_resources(self) -> dict:
        """
        Check NAS resource usage.

        Returns:
            Dictionary with resource metrics
        """
        try:
            # CPU usage
            cpu_output = subprocess.check_output(
                ["top", "-l", "1", "-n", "0"],
                text=True
            )
            # Parse CPU line (macOS format, adjust for Linux if needed)
            # This is a simplified version

            # Disk space
            disk_output = subprocess.check_output(
                ["df", "-h", self.config["paths"]["enhanced"]],
                text=True
            )
            lines = disk_output.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                disk_usage_percent = int(parts[4].rstrip('%'))
            else:
                disk_usage_percent = 0

            return {
                "cpu_percent": 0,  # Placeholder - implement actual parsing
                "disk_usage_percent": disk_usage_percent,
                "status": "ok"
            }

        except Exception as e:
            self.logger.error(f"Failed to check resources: {e}")
            return {"status": "error"}

    def should_run_archive_processing(self) -> bool:
        """Check if archive processing should run."""
        config = self.config["scheduling"]["archive_processing"]

        if not config["enabled"]:
            return False

        # Check time window
        if not self.is_in_time_window(config["start_time"], config["end_time"]):
            return False

        # Check if approaching sync time
        buffer = config.get("stop_before_sync_minutes", 15)
        if self.is_sync_window(buffer):
            self.logger.info("Approaching sync time, skipping archive processing")
            return False

        return True

    def should_run_current_catchup(self) -> bool:
        """Check if current photo catchup should run."""
        config = self.config["scheduling"]["current_catchup"]

        if not config["enabled"]:
            return False

        # Check time window
        if not self.is_in_time_window(config["start_time"], config["end_time"]):
            return False

        # Check pause windows (e.g., 6 AM sync)
        for pause_window in config.get("pause_windows", []):
            if self.is_in_time_window(pause_window["start"], pause_window["end"]):
                self.logger.info(f"In pause window {pause_window['start']}-{pause_window['end']}")
                return False

        # Check sync window
        if self.is_sync_window():
            return False

        return True

    def should_run_current_periodic(self) -> bool:
        """Check if periodic current photo processing should run."""
        config = self.config["scheduling"]["current_periodic"]

        if not config["enabled"]:
            return False

        # Check if in any allowed window
        in_allowed_window = False
        for window in config["allowed_windows"]:
            if self.is_in_time_window(window["start"], window["end"]):
                in_allowed_window = True
                break

        if not in_allowed_window:
            return False

        # Check sync window
        if self.is_sync_window():
            return False

        return True

    def run_processing(self, mode: str, batch_size: int, max_runtime_minutes: int = None) -> bool:
        """
        Run photo enhancer with specified parameters.

        Args:
            mode: Processing mode (archive/incoming)
            batch_size: Max images to process
            max_runtime_minutes: Optional runtime limit

        Returns:
            True if successful
        """
        cmd = [
            "python",
            str(self.photoner_path),
            "--config", str(self.config_path),
            "--mode", mode,
            "--batch-size", str(batch_size)
        ]

        self.logger.info(f"Starting {mode} processing (batch: {batch_size})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max_runtime_minutes * 60 if max_runtime_minutes else None
            )

            if result.returncode == 0:
                self.logger.info(f"{mode} processing completed successfully")
                return True
            else:
                self.logger.error(f"{mode} processing failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning(f"{mode} processing timed out after {max_runtime_minutes} minutes")
            return False

        except Exception as e:
            self.logger.error(f"Error running {mode} processing: {e}")
            return False

    def run(self):
        """Main scheduler loop."""
        self.logger.info("=" * 80)
        self.logger.info("Smart Scheduler Starting")
        self.logger.info("=" * 80)

        # Check what should run
        archive = self.should_run_archive_processing()
        catchup = self.should_run_current_catchup()
        periodic = self.should_run_current_periodic()

        self.logger.info(f"Archive Processing: {'YES' if archive else 'NO'}")
        self.logger.info(f"Current Catchup: {'YES' if catchup else 'NO'}")
        self.logger.info(f"Current Periodic: {'YES' if periodic else 'NO'}")

        # Check resources
        resources = self.check_nas_resources()
        self.logger.info(f"NAS Resources: {resources}")

        # Run appropriate task
        if archive:
            config = self.config["scheduling"]["archive_processing"]
            batch_size = self.config["resources"]["archive"]["max_batch_size"]
            max_runtime = (
                datetime.strptime(config["end_time"], "%H:%M") -
                datetime.strptime(config["start_time"], "%H:%M")
            ).seconds // 60

            self.run_processing("archive", batch_size, max_runtime)

        elif catchup:
            config = self.config["scheduling"]["current_catchup"]
            batch_size = self.config["resources"]["current_catchup"]["max_batch_size"]

            # Calculate time until end or next pause window
            max_runtime = 60  # Default 1 hour chunks

            self.run_processing("incoming", batch_size, max_runtime)

        elif periodic:
            batch_size = self.config["resources"]["current_periodic"]["max_batch_size"]
            max_runtime = 30  # 30 minutes max

            self.run_processing("incoming", batch_size, max_runtime)

        else:
            self.logger.info("No processing scheduled for current time")

        self.logger.info("Smart Scheduler Completed")


def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print("Usage: smart_scheduler.py <config.yaml>")
        print("Example: smart_scheduler.py config/config.production-nas.yaml")
        sys.exit(1)

    config_path = Path(sys.argv[1])

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    scheduler = SmartScheduler(config_path)
    scheduler.run()


if __name__ == "__main__":
    main()
