"""
PaddleOCR engine implementation.
"""

import logging
import os
from PIL import Image
import numpy as np
from .base import BaseOCREngine

logger = logging.getLogger(__name__)


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR engine implementation."""

    def __init__(self):
        self._ocr = None
        self._initialized = False
        # 禁用 MKLDNN 以避免 Windows 上的兼容性问题
        os.environ['FLAGS_use_mkldnn'] = '0'

    def _initialize(self):
        """Lazy initialization of PaddleOCR."""
        if not self._initialized:
            try:
                from paddleocr import PaddleOCR
                # 使用最小配置，禁用 MKLDNN 以避免兼容性问题
                self._ocr = PaddleOCR(
                    lang='ch',           # 中文
                    enable_mkldnn=False  # 禁用 MKLDNN
                )
                self._initialized = True
                logger.info("PaddleOCR initialized successfully with MKLDNN disabled")
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

            # 使用 predict 方法（新版本推荐）
            result = self._ocr.predict(img_array)

            # 处理返回结果
            if result and len(result) > 0:
                texts = []
                for item in result:
                    # 新版本返回格式可能有所不同，需要适配
                    if hasattr(item, 'rec_texts'):
                        # PaddleX 格式
                        texts.extend(item.rec_texts)
                    elif isinstance(item, dict) and 'rec_texts' in item:
                        texts.extend(item['rec_texts'])
                    elif isinstance(item, list):
                        # 旧格式或其他格式
                        for line in item:
                            if isinstance(line, (list, tuple)) and len(line) >= 2:
                                if isinstance(line[1], (list, tuple)) and len(line[1]) >= 1:
                                    texts.append(line[1][0])
                                elif isinstance(line[1], str):
                                    texts.append(line[1])

                return '\n'.join(texts) if texts else ""
            return ""
        except Exception as e:
            logger.error(f"PaddleOCR recognition failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
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
