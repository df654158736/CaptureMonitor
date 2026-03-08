"""
Tesseract OCR engine implementation.
Requires: pip install pytesseract
And Tesseract OCR installed on system
"""

import logging
import platform
import os
from PIL import Image
from .base import BaseOCREngine

logger = logging.getLogger(__name__)

# Common Tesseract installation paths on Windows
WINDOWS_TESSERACT_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'D:\Tesseract-OCR\tesseract.exe',
    r'E:\Tesseract-OCR\tesseract.exe',
]


class TesseractOCREngine(BaseOCREngine):
    """Tesseract OCR engine implementation."""

    def __init__(self):
        self._available = None
        self._tesseract_cmd = None

    def _find_tesseract(self) -> str:
        """Find Tesseract executable path."""
        import pytesseract

        # First check if it's already in PATH
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract found in PATH, version: {version}")
            return None  # Use default
        except:
            pass

        # On Windows, check common installation paths
        if platform.system() == 'Windows':
            for path in WINDOWS_TESSERACT_PATHS:
                if os.path.isfile(path):
                    logger.info(f"Found Tesseract at: {path}")
                    return path

        return None

    def _check_availability(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract

            # Try to find and set Tesseract path
            tesseract_path = self._find_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self._tesseract_cmd = tesseract_path

            # Try to get version
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            return True

        except ImportError:
            logger.warning("pytesseract not installed. Run: pip install pytesseract")
            return False
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            return False

    def recognize(self, image: Image.Image) -> str:
        """
        Recognize text in an image using Tesseract OCR.

        Args:
            image: PIL Image to process

        Returns:
            Recognized text as a string
        """
        try:
            import pytesseract

            # Set path if we found it
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

            # Try Chinese+English first, fallback to English only
            try:
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            except:
                # Fallback to English if Chinese language pack not installed
                text = pytesseract.image_to_string(image, lang='eng')

            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR recognition failed: {e}")
            return ""

    @property
    def name(self) -> str:
        return "Tesseract OCR"

    @property
    def is_available(self) -> bool:
        """Check if Tesseract OCR is available."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available
