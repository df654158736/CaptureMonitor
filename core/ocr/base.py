"""
OCR base class defining the interface for OCR engines.
"""

from abc import ABC, abstractmethod
from PIL import Image


class BaseOCREngine(ABC):
    """Base class for OCR engines."""

    @abstractmethod
    def recognize(self, image: Image.Image) -> str:
        """
        Recognize text in an image.

        Args:
            image: PIL Image to process

        Returns:
            Recognized text as a string
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the OCR engine."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR engine is available."""
        pass
