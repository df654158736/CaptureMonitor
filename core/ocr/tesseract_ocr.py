"""
Tesseract OCR engine implementation.
Requires: pip install pytesseract
And Tesseract OCR installed on system
"""

import logging
from PIL import Image
from .base import BaseOCREngine

logger = logging.getLogger(__name__)


class TesseractOCREngine(BaseOCREngine):
    """Tesseract OCR engine implementation."""

    def __init__(self):
        self._available = None
        self._tesseract_cmd = None

    def _check_availability(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            # Try to get version
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            return True
        except ImportError:
            logger.warning("pytesseract not installed")
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

            # Use Chinese and English language support
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
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
