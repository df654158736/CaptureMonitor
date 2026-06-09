"""全局热键封装(keyboard 库)。游戏占焦点时仍能触发(独占全屏可能失效)。"""

import logging

logger = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self):
        self._registered = None

    def register(self, hotkey: str, callback) -> bool:
        self.unregister()
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, callback)
            self._registered = hotkey
            logger.info(f"已注册全局热键: {hotkey}")
            return True
        except Exception as e:
            logger.warning(f"注册全局热键失败 ({hotkey}): {e}")
            return False

    def unregister(self):
        if self._registered:
            try:
                import keyboard
                keyboard.remove_hotkey(self._registered)
            except Exception:
                pass
            self._registered = None
