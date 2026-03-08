"""
Translation service for OCR results.
Supports multiple translation backends.
"""

import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)


class Translator:
    """Simple translator using googletrans or fallback."""

    def __init__(self):
        self._translator = None
        self._enabled = False
        self._source_lang = 'auto'
        self._target_lang = 'zh-cn'

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable translation."""
        self._enabled = enabled
        logger.info(f"Translation {'enabled' if enabled else 'disabled'}")

    def translate(self, text: str) -> str:
        """
        Translate text to Chinese.

        Args:
            text: Text to translate

        Returns:
            Translated text or original if translation fails
        """
        if not self._enabled or not text or not text.strip():
            return text

        # Don't translate if text is mostly Chinese already
        if self._is_mostly_chinese(text):
            return text

        try:
            # Lazy import to avoid slow startup
            if self._translator is None:
                from googletrans import Translator as GoogleTranslator
                self._translator = GoogleTranslator()

            result = self._translator.translate(
                text,
                src=self._source_lang,
                dest=self._target_lang
            )

            if result and result.text:
                return result.text

        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            # Return original text with a marker
            return text

        return text

    def _is_mostly_chinese(self, text: str) -> bool:
        """Check if text is mostly Chinese characters."""
        if not text:
            return False

        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.replace(' ', ''))

        if total_chars == 0:
            return False

        # If more than 30% Chinese, consider it Chinese text
        return (chinese_chars / total_chars) > 0.3


class BaiduTranslator:
    """Baidu translation API (requires appid and key)."""

    def __init__(self, appid: str = None, appkey: str = None):
        self.appid = appid
        self.appkey = appkey
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled and self.appid and self.appkey

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def translate(self, text: str) -> str:
        """Translate using Baidu API."""
        if not self.enabled or not text:
            return text

        try:
            import hashlib
            import random
            import requests

            salt = random.randint(32768, 65536)
            sign_str = self.appid + text + str(salt) + self.appkey
            sign = hashlib.md5(sign_str.encode()).hexdigest()

            url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
            params = {
                'q': text,
                'from': 'auto',
                'to': 'zh',
                'appid': self.appid,
                'salt': salt,
                'sign': sign
            }

            response = requests.get(url, params=params, timeout=10)
            result = response.json()

            if 'trans_result' in result:
                translations = [item['dst'] for item in result['trans_result']]
                return '\n'.join(translations)
            else:
                logger.warning(f"Baidu translation error: {result}")

        except Exception as e:
            logger.warning(f"Baidu translation failed: {e}")

        return text
