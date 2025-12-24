"""
Image Processor for Photoner
Core enhancement engine using OpenCV with EXIF preservation.
Handles JPEG, RAW, and TIFF files with newspaper-appropriate adjustments.
"""

import cv2
import numpy as np
import piexif
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import io

try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False


class ImageProcessor:
    """
    Handles image enhancement using OpenCV algorithms while preserving
    EXIF metadata and original quality.
    """

    def __init__(self, config: Dict[str, Any], logger):
        """
        Initialize the image processor.

        Args:
            config: Configuration dictionary from config.yaml
            logger: PhotonerLogger instance
        """
        self.config = config
        self.logger = logger
        self.enhancement_config = config["enhancement"]
        self.profile = config["enhancement"]["profile"]

        # Apply profile presets
        self._apply_profile()

    def _apply_profile(self) -> None:
        """Apply enhancement profile presets to override default settings."""
        profiles = self.config.get("profiles", {})
        if self.profile in profiles:
            profile_settings = profiles[self.profile]
            self.logger.info(f"Applying enhancement profile: {self.profile}", profile=self.profile)

            # Override settings from profile
            if "clahe_clip_limit" in profile_settings:
                self.enhancement_config["clahe"]["clip_limit"] = profile_settings["clahe_clip_limit"]
            if "saturation_boost" in profile_settings:
                self.enhancement_config["saturation"]["boost_factor"] = profile_settings["saturation_boost"]
            if "sharpening_amount" in profile_settings:
                self.enhancement_config["sharpening"]["amount"] = profile_settings["sharpening_amount"]
            if "brightness_percentile" in profile_settings:
                self.enhancement_config["brightness"]["target_percentile"] = profile_settings["brightness_percentile"]
            if "brightness_strength" in profile_settings:
                self.enhancement_config["brightness"]["strength"] = profile_settings["brightness_strength"]
            if "brightness_enabled" in profile_settings:
                self.enhancement_config["brightness"]["enabled"] = profile_settings["brightness_enabled"]

    def process_image(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """
        Main entry point for processing an image.

        Args:
            input_path: Path to input image
            output_path: Path to save enhanced image

        Returns:
            Dictionary containing processing results and metrics

        Raises:
            Exception: If processing fails
        """
        self.logger.debug(f"Processing image: {input_path}", input=str(input_path))

        # Determine file type and load image
        if self._is_raw_file(input_path):
            image_bgr, exif_data = self._load_raw_image(input_path)
        else:
            image_bgr, exif_data = self._load_standard_image(input_path)

        # Store original dimensions
        original_height, original_width = image_bgr.shape[:2]

        # Track adjustments made
        adjustments = {}

        # Apply enhancement pipeline
        enhanced_image = self._apply_enhancement_pipeline(image_bgr, exif_data, adjustments)

        # Verify dimensions unchanged (as per requirement)
        if enhanced_image.shape[:2] != (original_height, original_width):
            raise ValueError(
                f"Image dimensions changed during processing: "
                f"{original_width}x{original_height} -> {enhanced_image.shape[1]}x{enhanced_image.shape[0]}"
            )

        # Save enhanced image with EXIF preservation
        self._save_image_with_exif(enhanced_image, output_path, exif_data)

        return {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "original_dimensions": f"{original_width}x{original_height}",
            "adjustments": adjustments,
            "profile": self.profile,
        }

    def _is_raw_file(self, file_path: Path) -> bool:
        """Check if file is a RAW format."""
        raw_extensions = self.config["file_types"]["raw"]["extensions"]
        return file_path.suffix.lower() in [ext.lower() for ext in raw_extensions]

    def _load_raw_image(self, file_path: Path) -> Tuple[np.ndarray, Optional[bytes]]:
        """
        Load and convert RAW image to BGR format.

        Args:
            file_path: Path to RAW image

        Returns:
            Tuple of (BGR image array, EXIF data bytes)

        Raises:
            ImportError: If rawpy is not available
            Exception: If RAW decoding fails
        """
        if not RAWPY_AVAILABLE:
            raise ImportError("rawpy library not installed. Cannot process RAW files.")

        self.logger.debug(f"Loading RAW file: {file_path}")

        try:
            with rawpy.imread(str(file_path)) as raw:
                # Process RAW with camera white balance and color profile
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    use_auto_wb=False,
                    output_bps=16,  # 16-bit processing for quality
                    no_auto_bright=True,  # We'll handle brightness ourselves
                )

            # Convert RGB to BGR for OpenCV
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            # Convert from 16-bit to 8-bit
            bgr = (bgr / 256).astype(np.uint8)

            # Try to extract EXIF from RAW (may not be available)
            exif_data = None
            try:
                with Image.open(file_path) as pil_img:
                    if "exif" in pil_img.info:
                        exif_data = pil_img.info["exif"]
            except Exception as e:
                self.logger.warning(f"Could not extract EXIF from RAW: {e}", file=str(file_path))

            return bgr, exif_data

        except Exception as e:
            self.logger.error(f"Failed to load RAW file: {e}", file=str(file_path))
            raise

    def _load_standard_image(self, file_path: Path) -> Tuple[np.ndarray, Optional[bytes]]:
        """
        Load JPEG or TIFF image.

        Args:
            file_path: Path to image

        Returns:
            Tuple of (BGR image array, EXIF data bytes)
        """
        # Load with OpenCV
        image_bgr = cv2.imread(str(file_path), cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise ValueError(f"Failed to load image: {file_path}")

        # Extract EXIF data using Pillow (more reliable than OpenCV)
        exif_data = None
        try:
            with Image.open(file_path) as pil_img:
                if "exif" in pil_img.info:
                    exif_data = pil_img.info["exif"]
        except Exception as e:
            self.logger.warning(f"Could not extract EXIF: {e}", file=str(file_path))

        return image_bgr, exif_data

    def _apply_enhancement_pipeline(
        self, image: np.ndarray, exif_data: Optional[bytes], adjustments: Dict[str, Any]
    ) -> np.ndarray:
        """
        Apply full enhancement pipeline to image.

        Args:
            image: Input image in BGR format
            exif_data: EXIF metadata (used for ISO detection)
            adjustments: Dictionary to store adjustment metrics

        Returns:
            Enhanced image in BGR format
        """
        enhanced = image.copy()

        # 1. CLAHE - Contrast enhancement
        if self.enhancement_config["clahe"]["enabled"]:
            enhanced = self._apply_clahe(enhanced, adjustments)

        # 2. White balance correction
        if self.enhancement_config["white_balance"]["enabled"]:
            enhanced = self._apply_white_balance(enhanced, adjustments)

        # 3. Brightness/Exposure correction
        if self.enhancement_config["brightness"]["enabled"]:
            enhanced = self._apply_brightness_correction(enhanced, adjustments)

        # 4. Saturation enhancement
        if self.enhancement_config["saturation"]["enabled"]:
            enhanced = self._apply_saturation_boost(enhanced, adjustments)

        # 5. Noise reduction (conditional on ISO)
        if self.enhancement_config["noise_reduction"]["enabled"]:
            iso = self._extract_iso_from_exif(exif_data)
            if iso and iso > self.enhancement_config["noise_reduction"]["iso_threshold"]:
                enhanced = self._apply_noise_reduction(enhanced, adjustments)

        # 6. Sharpening (last step)
        if self.enhancement_config["sharpening"]["enabled"]:
            enhanced = self._apply_sharpening(enhanced, adjustments)

        return enhanced

    def _apply_clahe(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply Contrast Limited Adaptive Histogram Equalization.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            Enhanced image
        """
        clip_limit = self.enhancement_config["clahe"]["clip_limit"]
        tile_size = self.enhancement_config["clahe"]["tile_grid_size"]

        # Convert to LAB color space for better results
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply CLAHE to L channel only
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        l_enhanced = clahe.apply(l_channel)

        # Calculate contrast increase
        contrast_delta = float(np.std(l_enhanced)) / float(np.std(l_channel)) - 1.0
        adjustments["contrast_delta"] = f"+{contrast_delta:.2%}"

        # Merge back
        lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
        result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        self.logger.debug(f"CLAHE applied: clip_limit={clip_limit}, contrast_delta={contrast_delta:.2%}")
        return result

    def _apply_white_balance(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply automatic white balance using gray world assumption.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            White-balanced image
        """
        # Gray world assumption: average color should be gray
        avg_b = np.mean(image[:, :, 0])
        avg_g = np.mean(image[:, :, 1])
        avg_r = np.mean(image[:, :, 2])

        # Calculate scaling factors
        avg_gray = (avg_b + avg_g + avg_r) / 3
        scale_b = avg_gray / avg_b if avg_b > 0 else 1.0
        scale_g = avg_gray / avg_g if avg_g > 0 else 1.0
        scale_r = avg_gray / avg_r if avg_r > 0 else 1.0

        # Apply scaling with clipping
        result = image.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * scale_b, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * scale_g, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * scale_r, 0, 255)

        adjustments["white_balance"] = {
            "scale_b": f"{scale_b:.3f}",
            "scale_g": f"{scale_g:.3f}",
            "scale_r": f"{scale_r:.3f}",
        }

        self.logger.debug(f"White balance applied: R={scale_r:.3f}, G={scale_g:.3f}, B={scale_b:.3f}")
        return result.astype(np.uint8)

    def _apply_brightness_correction(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply automatic brightness/exposure correction.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            Brightness-corrected image
        """
        # Convert to HSV for brightness adjustment
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        v_channel = hsv[:, :, 2]

        # Calculate current brightness distribution
        target_percentile = self.enhancement_config["brightness"]["target_percentile"]
        current_low = np.percentile(v_channel, target_percentile[0])
        current_high = np.percentile(v_channel, target_percentile[1])

        # Target: spread histogram to match percentile range
        target_low = 255 * (target_percentile[0] / 100.0)
        target_high = 255 * (target_percentile[1] / 100.0)

        # Get brightness strength (default 1.0 = full adjustment)
        brightness_strength = self.enhancement_config["brightness"].get("strength", 1.0)

        # Calculate scaling
        current_range = current_high - current_low
        target_range = target_high - target_low

        if current_range > 0:
            scale = target_range / current_range
            offset = target_low - (current_low * scale)

            # Apply brightness adjustment with strength modifier
            # strength=1.0 means full adjustment, strength=0.5 means 50% adjustment
            scale_adjusted = 1.0 + (scale - 1.0) * brightness_strength
            offset_adjusted = offset * brightness_strength

            v_channel = np.clip(v_channel * scale_adjusted + offset_adjusted, 0, 255)

            brightness_delta = (np.mean(v_channel) - np.mean(hsv[:, :, 2])) / 255.0
            adjustments["brightness_delta"] = f"{brightness_delta:+.2%}"

            hsv[:, :, 2] = v_channel
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

            self.logger.debug(f"Brightness adjusted: delta={brightness_delta:+.2%}")
            return result

        return image

    def _apply_saturation_boost(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply subtle saturation boost.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            Saturation-enhanced image
        """
        boost_factor = self.enhancement_config["saturation"]["boost_factor"]

        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        s_channel = hsv[:, :, 1]

        # Apply boost with clipping
        s_channel = np.clip(s_channel * boost_factor, 0, 255)
        hsv[:, :, 1] = s_channel

        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        adjustments["saturation_boost"] = f"{(boost_factor - 1.0) * 100:.0f}%"
        self.logger.debug(f"Saturation boosted by {(boost_factor - 1.0) * 100:.0f}%")

        return result

    def _apply_noise_reduction(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply noise reduction while preserving edges.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            Noise-reduced image
        """
        strength = self.enhancement_config["noise_reduction"]["strength"]

        # Non-local means denoising (preserves edges)
        result = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=strength,
            hColor=strength,
            templateWindowSize=7,
            searchWindowSize=21,
        )

        adjustments["noise_reduction"] = f"strength={strength}"
        self.logger.debug(f"Noise reduction applied: strength={strength}")

        return result

    def _apply_sharpening(self, image: np.ndarray, adjustments: Dict[str, Any]) -> np.ndarray:
        """
        Apply unsharp mask sharpening.

        Args:
            image: Input BGR image
            adjustments: Dictionary to record adjustments

        Returns:
            Sharpened image
        """
        radius = self.enhancement_config["sharpening"]["radius"]
        amount = self.enhancement_config["sharpening"]["amount"]

        # Create Gaussian blur
        blurred = cv2.GaussianBlur(image, (0, 0), radius)

        # Unsharp mask: original + amount * (original - blurred)
        result = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)

        adjustments["sharpening"] = f"radius={radius}, amount={amount}"
        self.logger.debug(f"Sharpening applied: radius={radius}, amount={amount}")

        return result

    def _extract_iso_from_exif(self, exif_data: Optional[bytes]) -> Optional[int]:
        """
        Extract ISO value from EXIF data.

        Args:
            exif_data: EXIF metadata bytes

        Returns:
            ISO value or None if not found
        """
        if not exif_data:
            return None

        try:
            exif_dict = piexif.load(exif_data)
            if piexif.ExifIFD.ISOSpeedRatings in exif_dict.get("Exif", {}):
                iso = exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings]
                return int(iso) if isinstance(iso, (int, float)) else None
        except Exception as e:
            self.logger.debug(f"Could not extract ISO from EXIF: {e}")

        return None

    def _save_image_with_exif(self, image: np.ndarray, output_path: Path, exif_data: Optional[bytes]) -> None:
        """
        Save image with EXIF preservation and added processing tags.

        Args:
            image: BGR image to save
            output_path: Output file path
            exif_data: Original EXIF data
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get JPEG quality from config
        jpeg_quality = self.config["processing"]["jpeg_quality"]

        # Convert BGR to RGB for Pillow
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # Prepare EXIF data
        save_kwargs = {}

        if exif_data and self.config["advanced"]["preserve_all_exif"]:
            try:
                # Load existing EXIF
                exif_dict = piexif.load(exif_data)

                # Add processing software tag
                if self.config["advanced"]["add_processing_tag"]:
                    software_name = self.config["advanced"]["processing_software_name"]
                    exif_dict["0th"][piexif.ImageIFD.Software] = software_name.encode("utf-8")

                    # Add processing date
                    from datetime import datetime

                    process_date = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
                    exif_dict["0th"][piexif.ImageIFD.DateTime] = process_date.encode("utf-8")

                # Dump EXIF back to bytes
                exif_bytes = piexif.dump(exif_dict)
                save_kwargs["exif"] = exif_bytes

            except Exception as e:
                self.logger.warning(f"Could not preserve EXIF: {e}", output=str(output_path))

        # Save image
        pil_image.save(output_path, "JPEG", quality=jpeg_quality, optimize=True, **save_kwargs)

        self.logger.debug(f"Image saved: {output_path}", quality=jpeg_quality, exif_preserved=bool(exif_data))
