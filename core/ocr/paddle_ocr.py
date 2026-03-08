"""
PaddleOCR engine implementation.
"""

import logging
from PIL import Image
import numpy as np
from .base import BaseOCREngine

logger = logging.getLogger(__name__)


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR engine implementation."""

    def __init__(self):
        self._ocr = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of PaddleOCR."""
        if not self._initialized:
            try:
                from paddleocr import PaddleOCR
                # Use minimal parameters for compatibility
                self._ocr = PaddleOCR()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {e}")
                raise

    def recognize(self, image: Image.Image) -> str:
        """
        Recognize text in an image using PaddleOCR.

        Args:
            image: PIL Image to process

        Returns:
            Recognized text as a string
        """
        try:
            self._initialize()
            # Convert PIL Image to numpy array
            img_array = np.array(image)
            result = self._ocr.ocr(img_array)

            if result and result[0]:
                texts = [line[1][0] for line in result[0]]
                return '\n'.join(texts)
            return ""
        except Exception as e:
            logger.error(f"PaddleOCR recognition failed: {e}")
            return ""

    @property
    def name(self) -> str:
        return "PaddleOCR"

    @property
    def is_available(self) -> bool:
        """Check if PaddleOCR is available."""
        try:
            from paddleocr import PaddleOCR
            return True
        except ImportError:
            return False
