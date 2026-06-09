# tests/test_youdao_image.py
import base64
import pytest
from core.backends.base import TranslationResult
from core.backends.youdao_image import YoudaoImageTranslate, YoudaoImageError, build_sign


def test_build_sign_known_vector():
    q = base64.b64encode(b"hello world").decode("utf-8")  # aGVsbG8gd29ybGQ=
    sign = build_sign("youdaoAppKey", q, "FIXED-SALT", "youdaoAppSecret")
    assert sign == "5d4db2cbc1155719ba0d894e5caadd03"


def test_parse_success():
    payload = {
        "errorCode": "0",
        "lanFrom": "en", "lanTo": "zh-CHS",
        "resRegions": [
            {"context": "Hello", "tranContent": "你好", "boundingBox": "0,0,50,20"},
            {"context": "World", "tranContent": "世界", "boundingBox": "0,20,50,20"},
        ],
    }
    result = YoudaoImageTranslate._parse(payload)
    assert isinstance(result, TranslationResult)
    assert result.src_text == "Hello\nWorld"
    assert result.dst_text == "你好\n世界"
    assert result.segments[0] == {"src": "Hello", "dst": "你好", "rect": "0,0,50,20"}


def test_parse_error_code_raises():
    with pytest.raises(YoudaoImageError):
        YoudaoImageTranslate._parse({"errorCode": "108"})  # 108 = 应用ID不存在


def test_translate_without_creds_raises():
    backend = YoudaoImageTranslate(app_key="", app_secret="")
    with pytest.raises(YoudaoImageError):
        backend.translate_image(b"img", "en", "zh-CHS")


def test_translate_image_posts_correct_sign(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"errorCode": "0", "resRegions": [
                {"context": "Hi", "tranContent": "嗨", "boundingBox": "0,0,1,1"}]}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResp()

    monkeypatch.setattr("core.backends.youdao_image.requests.post", fake_post)

    backend = YoudaoImageTranslate(app_key="AK", app_secret="SK", salt_fn=lambda: "555")
    image = b"IMAGEBYTES"
    result = backend.translate_image(image, "en", "zh-CHS")

    q = base64.b64encode(image).decode("utf-8")
    expected_sign = build_sign("AK", q, "555", "SK")
    assert captured["url"] == "https://openapi.youdao.com/ocrtransapi"
    assert captured["data"]["sign"] == expected_sign
    assert captured["data"]["q"] == q
    assert captured["data"]["from"] == "en"
    assert captured["data"]["to"] == "zh-CHS"
    assert captured["data"]["type"] == "1"
    assert captured["data"]["appKey"] == "AK"
    assert result.dst_text == "嗨"
