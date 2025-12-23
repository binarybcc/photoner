"""
Photoner - Automated Newspaper Photo Enhancement System

A professional photo enhancement pipeline for batch processing newspaper archives
and incoming photographs on Synology NAS infrastructure.
"""

__version__ = "1.0.0"
__author__ = "UpstateToday.com"

from .logger import setup_logger, PhotonerLogger
from .processor import ImageProcessor
from .file_manager import FileManager
from .photo_enhancer import PhotoEnhancer

__all__ = [
    "setup_logger",
    "PhotonerLogger",
    "ImageProcessor",
    "FileManager",
    "PhotoEnhancer",
]
