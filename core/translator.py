"""
Translation service for OCR results.
Optimized to prevent UI blocking with timeout and length limits.
"""

import logging
from typing import Optional
import re
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Translator(QObject):
    """Simple translator using googletrans with timeout protection."""

    # Maximum text length to translate (to prevent blocking)
    MAX_TRANSLATE_LENGTH = 500

    # Translation timeout in seconds
    TRANSLATE_TIMEOUT = 2

    def __init__(self):
        super().__init__()
        self._translator = None
        self._enabled = False
        self._source_lang = 'auto'
        self._target_lang = 'zh-cn'
        self._last_error_time = None
        self._error_count = 0
        self._max_errors = 3  # Disable after N consecutive errors
        self._error_reset_time = timedelta(minutes=5)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable translation."""
        self._enabled = enabled
        self._error_count = 0  # Reset error count when toggling
        logger.info(f"Translation {'enabled' if enabled else 'disabled'}")

    def translate(self, text: str) -> str:
        """
        Translate text to Chinese with timeout protection.

        Args:
            text: Text to translate

        Returns:
            Translated text or original if translation fails/times out
        """
        # Quick checks
        if not self._enabled:
            return text

        if not text or not text.strip():
            return text

        # Check if we've had too many recent errors
        if self._error_count >= self._max_errors:
            if self._last_error_time:
                # Check if enough time has passed to reset errors
                if datetime.now() - self._last_error_time < self._error_reset_time:
                    logger.debug("Translation disabled due to too many errors")
                    return text
                else:
                    # Reset error count after cooldown period
                    self._error_count = 0
                    logger.info("Resetting translation error count")

        # Check if text is mostly Chinese
        if self._is_mostly_chinese(text):
            return text

        # Truncate text if too long
        if len(text) > self.MAX_TRANSLATE_LENGTH:
            text = text[:self.MAX_TRANSLATE_LENGTH] + "..."
            logger.debug(f"Text truncated to {self.MAX_TRANSLATE_LENGTH} chars")

        # Perform translation with timeout
        try:
            return self._translate_with_timeout(text)
        except Exception as e:
            self._error_count += 1
            self._last_error_time = datetime.now()
            logger.error(f"Translation error (count={self._error_count}): {e}")

            # Auto-disable after too many errors
            if self._error_count >= self._max_errors:
                logger.warning("Translation auto-disabled due to repeated errors")

            return text

    def _translate_with_timeout(self, text: str) -> str:
        """
        Translate with timeout protection using threading.

        Args:
            text: Text to translate

        Returns:
            Translated text or original if timeout/error
        """
        import threading
        import queue

        result_queue = queue.Queue()

        def worker():
            try:
                result = self._translate_sync(text)
                result_queue.put((True, result))
            except Exception as e:
                result_queue.put((False, str(e)))

        # Start translation in background thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # Wait for result with timeout
        try:
            success, result = result_queue.get(timeout=self.TRANSLATE_TIMEOUT)
            if success:
                # Reset error count on success
                self._error_count = 0
                return result
            else:
                raise Exception(result)
        except queue.Empty:
            logger.warning(f"Translation timeout after {self.TRANSLATE_TIMEOUT}s")
            raise Exception("Translation timeout")
        except Exception as e:
            raise e

    def _translate_sync(self, text: str) -> str:
        """
        Internal synchronous translation method.

        Args:
            text: Text to translate

        Returns:
            Translated text or original if translation fails
        """
        try:
            # Lazy import to avoid slow startup
            if self._translator is None:
                logger.info("Initializing Google Translator...")
                from googletrans import Translator as GoogleTranslator
                self._translator = GoogleTranslator()
                logger.info("Google Translator initialized")

            logger.debug(f"Translating: {text[:100]}...")

            # Set socket timeout
            import socket
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(self.TRANSLATE_TIMEOUT)

            try:
                result = self._translator.translate(
                    text,
                    src=self._source_lang,
                    dest=self._target_lang
                )
            finally:
                socket.setdefaulttimeout(old_timeout)

            if result and result.text:
                return result.text
            else:
                logger.warning("Translation returned empty result")

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

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

            response = requests.get(url, params=params, timeout=5)
            result = response.json()

            if 'trans_result' in result:
                translations = [item['dst'] for item in result['trans_result']]
                return '\n'.join(translations)
            else:
                logger.warning(f"Baidu translation error: {result}")

        except Exception as e:
            logger.warning(f"Baidu translation failed: {e}")

        return text
