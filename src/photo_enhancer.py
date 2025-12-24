"""
Photo Enhancer - Main Orchestrator
Coordinates the photo enhancement pipeline with configuration management,
batch processing, error handling, and crash recovery.
"""

import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import time
from datetime import datetime

# Import our modules
from logger import setup_logger
from processor import ImageProcessor
from file_manager import FileManager


class PhotoEnhancer:
    """
    Main orchestrator for the photo enhancement system.
    Manages the complete processing pipeline from discovery to output.
    """

    def __init__(self, config_path: Path):
        """
        Initialize the photo enhancer.

        Args:
            config_path: Path to config.yaml file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize logger
        self.logger = setup_logger(self.config)
        self.logger.info("=" * 80)
        self.logger.info("Photoner - Automated Photo Enhancement System")
        self.logger.info("=" * 80)
        self.logger.info(f"Configuration loaded from: {config_path}")

        # Initialize components
        self.file_manager = FileManager(self.config, self.logger)
        self.processor = ImageProcessor(self.config, self.logger)

        # Processing statistics
        self.stats = {
            "session_start": datetime.utcnow().isoformat(),
            "total_processed": 0,
            "total_failed": 0,
            "total_skipped": 0,
        }

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load and validate configuration file.

        Args:
            config_path: Path to config.yaml

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate critical configuration
        required_sections = ["paths", "processing", "enhancement", "logging"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")

        return config

    def process_batch(
        self,
        mode: str = "test",
        input_dir: Optional[Path] = None,
        max_images: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of images.

        Args:
            mode: Processing mode ("test", "incoming", "archive")
            input_dir: Override input directory (None to use config)
            max_images: Maximum images to process (None for config default)

        Returns:
            Dictionary containing batch processing results
        """
        self.logger.info(f"Starting batch processing: mode={mode}", mode=mode)

        # Check disk space before starting
        if self.config["advanced"].get("check_space_before_batch", True):
            disk_info = self.file_manager.check_disk_space()
            if disk_info.get("warning"):
                self.logger.error(
                    f"Insufficient disk space: {disk_info['free_gb']}GB free",
                    **disk_info
                )
                return {"error": "insufficient_disk_space", "disk_info": disk_info}

        # Determine input directories based on mode
        input_directories = self._get_input_directories(mode, input_dir)

        # Build processing queue
        max_batch_size = max_images or self.config["processing"]["max_batch_size"]
        priority = "newest_first" if mode == "incoming" else "oldest_first"

        queue = self.file_manager.build_processing_queue(
            input_directories,
            priority=priority,
            max_size=max_batch_size
        )

        if not queue:
            self.logger.info("No images to process")
            return {"total_images": 0, "message": "No images found"}

        # Start batch processing
        self.logger.start_batch(len(queue), mode)

        # Process each image
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
        }

        consecutive_failures = 0
        max_consecutive = self.config["error_handling"]["max_consecutive_failures"]

        for i, image_path in enumerate(queue, 1):
            self.logger.info(f"Processing image {i}/{len(queue)}: {image_path.name}")

            try:
                # Validate file
                if not self.file_manager.validate_file(image_path):
                    self.logger.warning(f"Skipping invalid file: {image_path}")
                    results["skipped"].append(str(image_path))
                    self.stats["total_skipped"] += 1
                    continue

                # Create backup if enabled
                if self.config["processing"].get("create_backups", False):
                    self.file_manager.create_backup(image_path)

                # Generate output path
                output_path = self.file_manager._generate_output_path(image_path)

                # Process image
                start_time = self.logger.log_processing_start(str(image_path))

                result = self.processor.process_image(image_path, output_path)

                # Handle file organization based on config
                final_enhanced_path = output_path
                if self.config["processing"].get("replace_with_enhanced", False):
                    # Move original to /originals/ subfolder
                    originals_path = self.file_manager.move_to_originals(image_path)

                    # Move enhanced image to original location
                    if originals_path:
                        final_enhanced_path = originals_path.parent.parent / image_path.name
                        shutil.move(str(output_path), str(final_enhanced_path))
                        self.logger.debug(f"Replaced original with enhanced: {final_enhanced_path}")
                else:
                    # Original behavior: move to /processed subfolder
                    if self.config["processing"].get("move_processed_originals", False):
                        originals_path = self.file_manager.move_to_originals(image_path)

                self.logger.log_processing_complete(
                    str(image_path),
                    str(final_enhanced_path),
                    start_time,
                    result.get("adjustments")
                )

                results["successful"].append(str(image_path))
                self.stats["total_processed"] += 1
                consecutive_failures = 0  # Reset counter

            except Exception as e:
                self.logger.log_processing_error(image_path, e)
                results["failed"].append({"file": str(image_path), "error": str(e)})
                self.stats["total_failed"] += 1
                consecutive_failures += 1

                # Retry logic if configured
                if self.config["error_handling"].get("retry_failed_images", False):
                    if self._retry_processing(image_path):
                        results["failed"].pop()  # Remove from failed
                        results["successful"].append(str(image_path))
                        self.stats["total_failed"] -= 1
                        self.stats["total_processed"] += 1
                        consecutive_failures = 0
                        continue

                # Check for abort conditions
                if consecutive_failures >= max_consecutive:
                    self.logger.critical(
                        f"Aborting: {consecutive_failures} consecutive failures",
                        consecutive_failures=consecutive_failures
                    )
                    break

        # End batch and get metrics
        batch_metrics = self.logger.end_batch()

        # Clean up temp files
        self.file_manager.cleanup_temp_files()

        # Combine results
        final_results = {
            **results,
            "metrics": batch_metrics,
            "stats": self.stats,
        }

        self.logger.info("Batch processing complete", **batch_metrics)
        return final_results

    def _get_input_directories(self, mode: str, override_dir: Optional[Path]) -> List[Path]:
        """
        Get input directories based on processing mode.

        Args:
            mode: Processing mode
            override_dir: Override directory

        Returns:
            List of directories to scan
        """
        if override_dir:
            return [override_dir]

        if mode == "incoming":
            return [Path(self.config["paths"]["incoming"])]
        elif mode == "archive":
            return [Path(self.config["paths"]["archive"])]
        elif mode == "test":
            # For testing, check both if they exist
            dirs = []
            for key in ["incoming", "archive"]:
                path = Path(self.config["paths"].get(key, ""))
                if path.exists():
                    dirs.append(path)
            return dirs or [Path("./test_samples")]
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _retry_processing(self, image_path: Path) -> bool:
        """
        Retry processing a failed image.

        Args:
            image_path: Path to image

        Returns:
            True if retry succeeded, False otherwise
        """
        max_retries = self.config["error_handling"]["max_retries"]
        retry_delay = self.config["error_handling"]["retry_delay_seconds"]

        self.logger.info(f"Retrying: {image_path}")

        time.sleep(retry_delay)

        try:
            output_path = self.file_manager._generate_output_path(image_path)
            start_time = time.time()

            result = self.processor.process_image(image_path, output_path)

            self.logger.log_processing_complete(
                str(image_path),
                str(output_path),
                start_time,
                result.get("adjustments")
            )

            self.logger.info(f"Retry successful: {image_path}")
            return True

        except Exception as e:
            self.logger.error(f"Retry failed: {image_path}", error=str(e))
            return False

    def run_scheduled_task(self, mode: str) -> Dict[str, Any]:
        """
        Run as scheduled task (called by Synology Task Scheduler).

        Args:
            mode: "incoming" or "archive"

        Returns:
            Processing results
        """
        schedule_config = self.config["schedule"].get(mode, {})

        if not schedule_config.get("enabled", False):
            self.logger.info(f"Scheduled task disabled: {mode}")
            return {"message": f"{mode} processing is disabled"}

        # Check business hours for incoming
        if mode == "incoming" and schedule_config.get("business_hours_only", False):
            current_hour = datetime.now().hour
            start_hour = schedule_config.get("business_hours_start", 6)
            end_hour = schedule_config.get("business_hours_end", 22)

            if not (start_hour <= current_hour < end_hour):
                self.logger.info(
                    f"Outside business hours ({start_hour}-{end_hour}), skipping"
                )
                return {"message": "outside_business_hours"}

        # Get max images for this run
        if mode == "archive":
            max_images = schedule_config.get("daily_target_images", 3000)
        else:
            max_images = self.config["processing"]["max_batch_size"]

        # Process batch
        return self.process_batch(mode=mode, max_images=max_images)


def main():
    """Command-line interface for photo enhancer."""
    parser = argparse.ArgumentParser(
        description="Photoner - Automated Photo Enhancement System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("./config/config.yaml"),
        help="Path to configuration file (default: ./config/config.yaml)",
    )

    parser.add_argument(
        "--mode",
        choices=["test", "incoming", "archive"],
        default="test",
        help="Processing mode (default: test)",
    )

    parser.add_argument(
        "--input",
        type=Path,
        help="Override input directory",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        help="Override max batch size from config",
    )

    parser.add_argument(
        "--profile",
        choices=["conservative", "aggressive", "custom"],
        help="Override enhancement profile",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current processing status and exit",
    )

    args = parser.parse_args()

    try:
        # Initialize enhancer
        enhancer = PhotoEnhancer(args.config)

        # Override profile if specified
        if args.profile:
            enhancer.config["enhancement"]["profile"] = args.profile
            enhancer.processor.profile = args.profile
            enhancer.processor._apply_profile()

        # Show status and exit
        if args.status:
            disk_info = enhancer.file_manager.check_disk_space()
            print(f"\n{'=' * 60}")
            print("Photoner Status")
            print(f"{'=' * 60}")
            print(f"Configuration: {args.config}")
            print(f"Enhancement Profile: {enhancer.config['enhancement']['profile']}")
            print(f"Disk Free: {disk_info['free_gb']:.2f} GB ({disk_info['percent_used']:.1f}% used)")
            print(f"{'=' * 60}\n")
            return 0

        # Run processing
        results = enhancer.process_batch(
            mode=args.mode,
            input_dir=args.input,
            max_images=args.batch_size
        )

        # Print summary
        if "error" in results:
            print(f"\nError: {results['error']}")
            return 1

        print(f"\n{'=' * 60}")
        print("Processing Summary")
        print(f"{'=' * 60}")
        print(f"Successful: {len(results.get('successful', []))}")
        print(f"Failed: {len(results.get('failed', []))}")
        print(f"Skipped: {len(results.get('skipped', []))}")

        if "metrics" in results:
            metrics = results["metrics"]
            print(f"Error Rate: {metrics.get('error_rate', 0):.1f}%")
            print(f"Avg Time per Image: {metrics.get('avg_time_per_image', 0):.2f}s")
            print(f"Throughput: {metrics.get('throughput_images_per_hour', 0):.0f} images/hour")

        print(f"{'=' * 60}\n")

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130

    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
