"""翻译后端:抽象接口 + 按配置创建具体后端。"""

from .base import TranslationBackend, TranslationResult
from .youdao_image import YoudaoImageTranslate
from .volcano_image import VolcanoImageTranslate

__all__ = [
    "TranslationBackend",
    "TranslationResult",
    "YoudaoImageTranslate",
    "VolcanoImageTranslate",
    "create_backend",
]


def create_backend(config: dict) -> TranslationBackend:
    """按 config['backend'] 创建对应的翻译后端。"""
    name = config.get("backend", "youdao")
    if name == "volcano":
        v = config["volcano"]
        return VolcanoImageTranslate(
            v.get("access_key", ""), v.get("secret_key", ""),
            v.get("region", "cn-north-1"),
        )
    y = config["youdao"]
    return YoudaoImageTranslate(y.get("app_key", ""), y.get("app_secret", ""))
