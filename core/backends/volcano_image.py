"""火山引擎 · 图片翻译(TranslateImage,OCR + 翻译合一)客户端。

文档:https://www.volcengine.com/docs/4640/65105
鉴权由 volcengine SDK 处理(AccessKey/SecretKey + 区域 cn-north-1)。
volcengine SDK 延迟导入:不用火山引擎时无需安装该依赖。
"""

import base64
import json
import logging

from .base import TranslationBackend, TranslationResult

logger = logging.getLogger(__name__)

API_HOST = "translate.volcengineapi.com"
ACTION = "TranslateImage"
VERSION = "2020-07-01"

# 中性语言码 → 火山语言码
_LANG_MAP = {
    "zh": "zh", "zh-CHS": "zh", "zh-CN": "zh",
    "en": "en", "ja": "ja", "jp": "ja",
    "auto": "",  # 火山:源语言留空即自动检测
}


def _map_lang(code: str) -> str:
    return _LANG_MAP.get(code, code or "")


class VolcanoImageError(Exception):
    pass


class VolcanoImageTranslate(TranslationBackend):
    def __init__(self, access_key: str, secret_key: str,
                 region: str = "cn-north-1", timeout: int = 5):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout
        self._service = None

    @property
    def name(self) -> str:
        return "Volcano Image Translate"

    def _get_service(self):
        if self._service is None:
            from volcengine.ApiInfo import ApiInfo
            from volcengine.Credentials import Credentials
            from volcengine.ServiceInfo import ServiceInfo
            from volcengine.base.Service import Service

            service_info = ServiceInfo(
                API_HOST,
                {"Content-Type": "application/json"},
                Credentials(self.access_key, self.secret_key, "translate", self.region),
                self.timeout, self.timeout,
            )
            api_info = {
                "translate": ApiInfo("POST", "/", {"Action": ACTION, "Version": VERSION}, {}, {})
            }
            self._service = Service(service_info, api_info)
        return self._service

    def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult:
        if not self.access_key or not self.secret_key:
            raise VolcanoImageError("火山 access_key/secret_key 未配置")

        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        body = {"Image": img_b64, "TargetLanguage": _map_lang(dst) or "zh"}
        source = _map_lang(src)
        if source:
            body["SourceLanguage"] = source

        try:
            raw = self._get_service().json("translate", {}, json.dumps(body))
        except ImportError as e:
            raise VolcanoImageError(
                "未安装 volcengine SDK,请执行: pip install volcengine"
            ) from e
        except Exception as e:
            raise VolcanoImageError(f"火山调用失败: {e}") from e
        return self._parse(raw)

    @staticmethod
    def _parse(raw) -> TranslationResult:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            raw = json.loads(raw)

        meta = raw.get("ResponseMetadata", {}) if isinstance(raw, dict) else {}
        if isinstance(meta, dict) and meta.get("Error"):
            err = meta["Error"]
            raise VolcanoImageError(f"火山返回错误 {err.get('Code')}: {err.get('Message')}")

        blocks = raw.get("TextBlocks")
        if blocks is None and isinstance(raw.get("Result"), dict):
            blocks = raw["Result"].get("TextBlocks")
        blocks = blocks or []

        segments = [
            {
                "src": b.get("Text", ""),
                "dst": b.get("Translation", ""),
                "rect": str(b.get("Points", "")),
            }
            for b in blocks
        ]
        src_text = "\n".join(s["src"] for s in segments)
        dst_text = "\n".join(s["dst"] for s in segments)
        if not blocks:
            logger.info("火山 TranslateImage 未解析到 TextBlocks,原始响应: %s", str(raw)[:600])
        return TranslationResult(src_text=src_text, dst_text=dst_text, segments=segments)
