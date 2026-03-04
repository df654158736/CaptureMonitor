"""
OCR engines for CaptureMonitor.
"""

from .base import BaseOCREngine
from .paddle_ocr import PaddleOCREngine
from .windows_ocr import WindowsOCREngine

__all__ = ['BaseOCREngine', 'PaddleOCREngine', 'WindowsOCREngine']
