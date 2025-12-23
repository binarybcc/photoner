"""
Logging System for Photoner
Provides structured logging with JSON format, file rotation, and performance tracking.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import time


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format for easier parsing and analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add thread information if available
        if hasattr(record, "threadName"):
            log_data["thread"] = record.threadName

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra parameter
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class PhotonerLogger:
    """
    Centralized logging system for Photoner with support for:
    - Console and file logging
    - JSON structured logging
    - Log rotation
    - Performance metrics tracking
    - Daily summary reports
    """

    def __init__(self, config: Dict[str, Any], name: str = "photoner"):
        """
        Initialize the logging system.

        Args:
            config: Configuration dictionary from config.yaml
            name: Logger name (default: "photoner")
        """
        self.config = config
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config["logging"]["level"]))

        # Prevent duplicate handlers if logger already configured
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Performance tracking
        self.metrics = {
            "images_processed": 0,
            "images_failed": 0,
            "total_processing_time": 0.0,
            "batch_start_time": None,
            "errors": [],
        }
        self.metrics_lock = threading.Lock()

        # Set up logging handlers
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configure console and file logging handlers."""
        log_config = self.config["logging"]

        # Console handler
        if log_config.get("console_enabled", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_config.get("console_level", "INFO")))

            if log_config.get("json_format", False):
                console_handler.setFormatter(JSONFormatter())
            else:
                console_format = "%(asctime)s [%(levelname)s] %(message)s"
                console_handler.setFormatter(logging.Formatter(console_format))

            self.logger.addHandler(console_handler)

        # File handler with rotation
        if log_config.get("file_enabled", True):
            # Ensure log directory exists
            log_dir = Path(self.config["paths"]["logs"])
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / "processing.log"
            max_bytes = log_config.get("max_log_size_mb", 100) * 1024 * 1024
            backup_count = log_config.get("backup_count", 5)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setLevel(getattr(logging, log_config.get("file_level", "DEBUG")))

            if log_config.get("json_format", True):
                file_handler.setFormatter(JSONFormatter())
            else:
                file_format = "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
                file_handler.setFormatter(logging.Formatter(file_format))

            self.logger.addHandler(file_handler)

            # Separate error log file
            error_log_file = log_dir / "errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(JSONFormatter() if log_config.get("json_format", True) else logging.Formatter(file_format))
            self.logger.addHandler(error_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message and track in metrics."""
        self.logger.error(message, extra=kwargs)
        with self.metrics_lock:
            self.metrics["errors"].append({"timestamp": datetime.utcnow().isoformat(), "message": message, **kwargs})

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with stack trace."""
        self.logger.exception(message, extra=kwargs)

    def log_processing_start(self, image_path: str) -> float:
        """
        Log start of image processing and return start time.

        Args:
            image_path: Path to image being processed

        Returns:
            Start time (for calculating duration)
        """
        start_time = time.time()
        self.info(f"Starting processing: {image_path}", image_path=str(image_path))
        return start_time

    def log_processing_complete(
        self, image_path: str, output_path: str, start_time: float, adjustments: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log successful image processing completion.

        Args:
            image_path: Input image path
            output_path: Output image path
            start_time: Processing start time
            adjustments: Dictionary of adjustments made
        """
        processing_time = time.time() - start_time

        with self.metrics_lock:
            self.metrics["images_processed"] += 1
            self.metrics["total_processing_time"] += processing_time

        log_data = {
            "input_file": str(image_path),
            "output_file": str(output_path),
            "processing_time_sec": round(processing_time, 2),
            "status": "success",
        }

        if adjustments:
            log_data["adjustments"] = adjustments

        self.info(f"Processing complete: {image_path} ({processing_time:.2f}s)", **log_data)

    def log_processing_error(self, image_path: str, error: Exception, start_time: Optional[float] = None) -> None:
        """
        Log image processing error.

        Args:
            image_path: Path to image that failed
            error: The exception that occurred
            start_time: Processing start time (optional)
        """
        with self.metrics_lock:
            self.metrics["images_failed"] += 1

        log_data = {
            "input_file": str(image_path),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "status": "failed",
        }

        if start_time:
            log_data["processing_time_sec"] = round(time.time() - start_time, 2)

        self.error(f"Processing failed: {image_path}", **log_data)

    def start_batch(self, batch_size: int, batch_type: str = "unknown") -> None:
        """
        Log start of batch processing.

        Args:
            batch_size: Number of images in batch
            batch_type: Type of batch (incoming/archive)
        """
        with self.metrics_lock:
            self.metrics["batch_start_time"] = time.time()

        self.info(f"Starting batch processing: {batch_size} images", batch_size=batch_size, batch_type=batch_type)

    def end_batch(self) -> Dict[str, Any]:
        """
        Log end of batch processing and return metrics.

        Returns:
            Dictionary of batch processing metrics
        """
        with self.metrics_lock:
            batch_time = time.time() - self.metrics["batch_start_time"] if self.metrics["batch_start_time"] else 0
            total_images = self.metrics["images_processed"] + self.metrics["images_failed"]

            metrics = {
                "total_images": total_images,
                "successful": self.metrics["images_processed"],
                "failed": self.metrics["images_failed"],
                "error_rate": (self.metrics["images_failed"] / total_images * 100) if total_images > 0 else 0,
                "batch_time_sec": round(batch_time, 2),
                "avg_time_per_image": (
                    round(self.metrics["total_processing_time"] / self.metrics["images_processed"], 2)
                    if self.metrics["images_processed"] > 0
                    else 0
                ),
                "throughput_images_per_hour": (
                    round((total_images / batch_time) * 3600, 2) if batch_time > 0 else 0
                ),
            }

            # Reset metrics for next batch
            self.metrics = {
                "images_processed": 0,
                "images_failed": 0,
                "total_processing_time": 0.0,
                "batch_start_time": None,
                "errors": [],
            }

        self.info("Batch processing complete", **metrics)
        return metrics

    def generate_summary_report(self, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate summary report of processing metrics.

        Args:
            output_file: Optional path to save report

        Returns:
            Dictionary containing summary report
        """
        with self.metrics_lock:
            report = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "images_processed": self.metrics["images_processed"],
                "images_failed": self.metrics["images_failed"],
                "recent_errors": self.metrics["errors"][-10:],  # Last 10 errors
            }

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            self.info(f"Summary report saved: {output_file}")

        return report


def setup_logger(config: Dict[str, Any], name: str = "photoner") -> PhotonerLogger:
    """
    Factory function to create and configure logger.

    Args:
        config: Configuration dictionary from config.yaml
        name: Logger name

    Returns:
        Configured PhotonerLogger instance
    """
    return PhotonerLogger(config, name)
