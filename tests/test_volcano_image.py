"""火山图片翻译后端:响应解析 + 语言码映射(不触网,SDK 调用属集成)。"""

import json

import pytest

from core.backends.base import TranslationResult
from core.backends.volcano_image import VolcanoImageTranslate, VolcanoImageError, _map_lang


def test_map_lang_neutral_to_volcano():
    assert _map_lang("zh") == "zh"
    assert _map_lang("zh-CHS") == "zh"      # 兼容有道风格的中性码
    assert _map_lang("en") == "en"
    assert _map_lang("ja") == "ja"
    assert _map_lang("auto") == ""          # 火山:源语言留空即自动


def test_parse_success_from_dict():
    raw = {
        "ResponseMetadata": {"RequestId": "x"},
        "TextBlocks": [
            {"Text": "Hello", "Translation": "你好", "Points": [[0, 0], [10, 0]]},
            {"Text": "World", "Translation": "世界", "Points": []},
        ],
    }
    r = VolcanoImageTranslate._parse(raw)
    assert isinstance(r, TranslationResult)
    assert r.src_text == "Hello\nWorld"
    assert r.dst_text == "你好\n世界"
    assert r.segments[0]["src"] == "Hello"
    assert r.segments[0]["dst"] == "你好"


def test_parse_accepts_json_string():
    raw = json.dumps({"TextBlocks": [{"Text": "Hi", "Translation": "嗨", "Points": []}]})
    r = VolcanoImageTranslate._parse(raw)
    assert r.dst_text == "嗨"


def test_parse_error_metadata_raises():
    raw = {"ResponseMetadata": {"Error": {"Code": "AccessDenied", "Message": "bad key"}}}
    with pytest.raises(VolcanoImageError):
        VolcanoImageTranslate._parse(raw)


def test_translate_without_creds_raises():
    backend = VolcanoImageTranslate(access_key="", secret_key="")
    with pytest.raises(VolcanoImageError):
        backend.translate_image(b"img", "en", "zh")
