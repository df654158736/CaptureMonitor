"""有道智云 · 图片翻译(ocrtransapi,OCR + 翻译合一)客户端。

文档:https://ai.youdao.com/DOCSIRMA/html/trans/api/tpfy/index.html
签名(v1):q = base64(image);sign = MD5(appKey + q + salt + appSecret)。
注意:此处用完整 q(不 truncate),无 curtime/signType —— 与 OCR 接口不同。
"""

import base64
import hashlib
import uuid
import requests

from .base import TranslationBackend, TranslationResult

API_URL = "https://openapi.youdao.com/ocrtransapi"


class YoudaoImageError(Exception):
    pass


def build_sign(app_key: str, q: str, salt: str, app_secret: str) -> str:
    sign_str = app_key + q + salt + app_secret
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


class YoudaoImageTranslate(TranslationBackend):
    def __init__(self, app_key: str, app_secret: str, timeout: float = 5.0, salt_fn=None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.timeout = timeout
        self._salt_fn = salt_fn or (lambda: str(uuid.uuid1()))

    @property
    def name(self) -> str:
        return "Youdao Image Translate"

    def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult:
        if not self.app_key or not self.app_secret:
            raise YoudaoImageError("有道 app_key/app_secret 未配置")

        q = base64.b64encode(image_bytes).decode("utf-8")
        salt = self._salt_fn()
        sign = build_sign(self.app_key, q, salt, self.app_secret)
        data = {
            "from": src, "to": dst, "type": "1", "q": q,
            "appKey": self.app_key, "salt": salt, "sign": sign,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            resp = requests.post(API_URL, data=data, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as e:
            raise YoudaoImageError(f"网络错误: {e}") from e
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> TranslationResult:
        code = str(payload.get("errorCode", ""))
        if code != "0":
            raise YoudaoImageError(f"有道返回错误 {code}")
        regions = payload.get("resRegions") or []
        segments = [
            {
                "src": r.get("context", ""),
                "dst": r.get("tranContent", ""),
                "rect": r.get("boundingBox", ""),
            }
            for r in regions
        ]
        src_text = "\n".join(s["src"] for s in segments)
        dst_text = "\n".join(s["dst"] for s in segments)
        return TranslationResult(src_text=src_text, dst_text=dst_text, segments=segments)
