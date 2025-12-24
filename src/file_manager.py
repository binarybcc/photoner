"""
File Manager for Photoner
Handles directory scanning, file validation, safe file operations, and duplicate detection.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import hashlib


class FileManager:
    """
    Manages all file operations with safety checks and validation.
    Ensures originals are never modified and operations are atomic.
    """

    def __init__(self, config: Dict[str, Any], logger):
        """
        Initialize the file manager.

        Args:
            config: Configuration dictionary from config.yaml
            logger: PhotonerLogger instance
        """
        self.config = config
        self.logger = logger
        self.paths = config["paths"]
        self.file_types = config["file_types"]

        # Track processed files to avoid duplicates
        self.processed_files: Set[str] = set()

        # Ensure critical directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        critical_dirs = [
            self.paths["enhanced"],
            self.paths["logs"],
            self.paths.get("temp", "./temp"),
        ]

        # Add backup directory if enabled
        if self.paths.get("backup") and self.config["processing"].get("create_backups", False):
            critical_dirs.append(self.paths["backup"])

        for dir_path in critical_dirs:
            if dir_path:  # Skip if None or empty
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Ensured directory exists: {dir_path}")

    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        Scan directory for processable image files.

        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories

        Returns:
            List of image file paths

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        self.logger.info(f"Scanning directory: {directory}", recursive=recursive)

        image_files = []
        supported_extensions = self._get_supported_extensions()

        # Scan directory
        pattern = "**/*" if recursive else "*"
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                # Skip already processed files if in a "processed" subdirectory
                if "processed" not in str(file_path):
                    image_files.append(file_path)

        self.logger.info(f"Found {len(image_files)} images in {directory}", count=len(image_files))
        return image_files

    def _get_supported_extensions(self) -> Set[str]:
        """Get set of all supported file extensions."""
        extensions = set()

        for file_type, config in self.file_types.items():
            if config.get("enabled", True):
                extensions.update([ext.lower() for ext in config["extensions"]])

        return extensions

    def build_processing_queue(
        self, directories: List[Path], priority: str = "oldest_first", max_size: Optional[int] = None
    ) -> List[Path]:
        """
        Build a prioritized queue of files to process.

        Args:
            directories: List of directories to scan
            priority: Queue ordering ("oldest_first", "newest_first", "largest_first")
            max_size: Maximum queue size (None for unlimited)

        Returns:
            Ordered list of file paths
        """
        self.logger.info(f"Building processing queue from {len(directories)} directories", priority=priority)

        # Collect all files
        all_files = []
        for directory in directories:
            try:
                files = self.scan_directory(directory)
                all_files.extend(files)
            except FileNotFoundError as e:
                self.logger.warning(f"Skipping directory: {e}")

        # Filter out already processed files
        if self.config["processing"].get("skip_existing", True):
            all_files = self._filter_already_processed(all_files)

        # Apply priority sorting
        if priority == "oldest_first":
            all_files.sort(key=lambda p: p.stat().st_mtime)
        elif priority == "newest_first":
            all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        elif priority == "largest_first":
            all_files.sort(key=lambda p: p.stat().st_size, reverse=True)

        # Apply max size limit
        if max_size:
            all_files = all_files[:max_size]

        self.logger.info(f"Processing queue built: {len(all_files)} files", queue_size=len(all_files))
        return all_files

    def _filter_already_processed(self, files: List[Path]) -> List[Path]:
        """
        Filter out files that have already been processed.

        Args:
            files: List of input files

        Returns:
            List of unprocessed files
        """
        unprocessed = []

        for file_path in files:
            # Generate expected output path
            output_path = self._generate_output_path(file_path)

            # Check if output exists
            if output_path.exists():
                # Check timestamps if configured
                if self.config["processing"].get("check_timestamp", True):
                    input_mtime = file_path.stat().st_mtime
                    output_mtime = output_path.stat().st_mtime

                    # Re-process if input is newer
                    if input_mtime > output_mtime:
                        self.logger.debug(f"Input newer than output, re-processing: {file_path}")
                        unprocessed.append(file_path)
                    else:
                        self.logger.debug(f"Skipping already processed: {file_path}")
                else:
                    self.logger.debug(f"Skipping existing output: {file_path}")
            else:
                unprocessed.append(file_path)

        removed_count = len(files) - len(unprocessed)
        if removed_count > 0:
            self.logger.info(f"Filtered {removed_count} already-processed files", removed=removed_count)

        return unprocessed

    def _generate_output_path(self, input_path: Path) -> Path:
        """
        Generate output path for enhanced image.
        If replace_with_enhanced is True, uses temp directory for processing,
        otherwise uses enhanced directory structure.

        Args:
            input_path: Input image path

        Returns:
            Output path for enhanced image
        """
        replace_with_enhanced = self.config["processing"].get("replace_with_enhanced", False)

        if replace_with_enhanced:
            # Create temp file that will replace the original
            temp_dir = Path(self.paths["temp"])
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Use same filename as input (will replace original location)
            output_filename = input_path.name
            output_path = temp_dir / f"enhanced_{input_path.name}"

            return output_path
        else:
            # Original behavior: create in separate enhanced/ directory
            input_str = str(input_path.resolve())
            enhanced_base = Path(self.paths["enhanced"])

            # Preserve directory structure relative to source
            if self.paths.get("incoming") and str(Path(self.paths["incoming"]).resolve()) in input_str:
                relative_path = input_path.relative_to(Path(self.paths["incoming"]).resolve())
                output_dir = enhanced_base / "incoming" / relative_path.parent
            elif self.paths.get("archive") and str(Path(self.paths["archive"]).resolve()) in input_str:
                relative_path = input_path.relative_to(Path(self.paths["archive"]).resolve())
                output_dir = enhanced_base / "archive" / relative_path.parent
            else:
                # Fallback: use same relative structure
                output_dir = enhanced_base / input_path.parent.name

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename (add _enhanced suffix)
            stem = input_path.stem
            output_filename = f"{stem}_enhanced.jpg"  # Always output as JPEG

        return output_dir / output_filename

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that file is processable.

        Args:
            file_path: Path to file

        Returns:
            True if file is valid, False otherwise
        """
        try:
            # Check file exists
            if not file_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return False

            # Check file is readable
            if not os.access(file_path, os.R_OK):
                self.logger.warning(f"File not readable: {file_path}")
                return False

            # Check file size (not empty, not too large)
            file_size = file_path.stat().st_size
            if file_size == 0:
                self.logger.warning(f"File is empty: {file_path}")
                return False

            # Check for corruption (basic check - can we open it?)
            try:
                from PIL import Image

                with Image.open(file_path) as img:
                    img.verify()
            except Exception as e:
                self.logger.warning(f"File appears corrupted: {file_path}", error=str(e))
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating file: {file_path}", error=str(e))
            return False

    def safe_write(self, image_data: Any, output_path: Path, write_func) -> bool:
        """
        Safely write file using atomic operation (write to temp, then move).

        Args:
            image_data: Image data to write
            output_path: Final output path
            write_func: Function to perform the actual write (receives temp_path and image_data)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary file in same directory (for atomic move)
            temp_dir = output_path.parent
            temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, suffix=".tmp")
            os.close(temp_fd)
            temp_path = Path(temp_path)

            try:
                # Execute write function
                write_func(temp_path, image_data)

                # Verify write succeeded
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise IOError("Write produced empty file")

                # Atomic move to final location
                shutil.move(str(temp_path), str(output_path))

                self.logger.debug(f"File safely written: {output_path}")
                return True

            except Exception as e:
                # Clean up temp file on failure
                if temp_path.exists():
                    temp_path.unlink()
                raise e

        except Exception as e:
            self.logger.error(f"Failed to write file: {output_path}", error=str(e))
            return False

    def move_to_originals(self, file_path: Path) -> Optional[Path]:
        """
        Move original file to 'originals' subdirectory.

        Args:
            file_path: File to move

        Returns:
            Path to moved file, or None if failed
        """
        if not self.config["processing"].get("move_processed_originals", True):
            return None  # Feature disabled

        try:
            # Get originals folder name from config
            originals_folder = self.config["processing"].get("originals_folder_name", "originals")

            # Create originals subdirectory
            originals_dir = file_path.parent / originals_folder
            originals_dir.mkdir(exist_ok=True)

            # Move file
            destination = originals_dir / file_path.name
            shutil.move(str(file_path), str(destination))

            self.logger.debug(f"Moved to originals: {file_path} -> {destination}")
            return destination

        except Exception as e:
            self.logger.error(f"Failed to move file: {file_path}", error=str(e))
            return None

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup copy of file before processing.

        Args:
            file_path: File to backup

        Returns:
            Path to backup file, or None if failed
        """
        if not self.config["processing"].get("create_backups", False):
            return None

        if not self.paths.get("backup"):
            return None

        try:
            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(self.paths["backup"]) / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Preserve relative path structure
            backup_path = backup_dir / file_path.name
            shutil.copy2(str(file_path), str(backup_path))

            self.logger.debug(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {file_path}", error=str(e))
            return None

    def check_disk_space(self) -> Dict[str, Any]:
        """
        Check available disk space.

        Returns:
            Dictionary with disk space information
        """
        enhanced_path = Path(self.paths["enhanced"])
        stat = shutil.disk_usage(enhanced_path)

        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        percent_used = (stat.used / stat.total) * 100

        disk_info = {
            "free_gb": round(free_gb, 2),
            "used_gb": round(used_gb, 2),
            "total_gb": round(total_gb, 2),
            "percent_used": round(percent_used, 2),
        }

        # Check against minimum threshold
        min_free_gb = self.config["advanced"].get("min_free_space_gb", 10)
        if free_gb < min_free_gb:
            self.logger.warning(
                f"Low disk space: {free_gb:.2f}GB free (minimum: {min_free_gb}GB)",
                **disk_info
            )
            disk_info["warning"] = True
        else:
            disk_info["warning"] = False

        return disk_info

    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files.

        Returns:
            Number of files cleaned up
        """
        temp_dir = Path(self.paths.get("temp", "./temp"))
        if not temp_dir.exists():
            return 0

        count = 0
        for temp_file in temp_dir.glob("*.tmp"):
            try:
                temp_file.unlink()
                count += 1
            except Exception as e:
                self.logger.debug(f"Could not delete temp file: {temp_file}", error=str(e))

        if count > 0:
            self.logger.info(f"Cleaned up {count} temporary files", count=count)

        return count
