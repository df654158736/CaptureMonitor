# tests/test_pipeline.py
import numpy as np
from core.pipeline import TranslationPipeline
from core.backends.base import TranslationResult

BLACK = np.zeros((32, 32, 3), dtype=np.uint8)
WHITE = np.full((32, 32, 3), 255, dtype=np.uint8)


class FakeBackend:
    def __init__(self):
        self.calls = 0

    @property
    def name(self):
        return "fake"

    def translate_image(self, image_bytes, src, dst):
        self.calls += 1
        return TranslationResult(src_text=f"src{self.calls}", dst_text=f"dst{self.calls}")


def make_pipeline(backend):
    return TranslationPipeline(backend, src="en", dst="zh-CHS", to_png=lambda f: b"png")


def test_no_translation_until_stable():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    assert pipe.process_frame(BLACK, now=0.0) is None   # 首帧 CHANGING
    assert backend.calls == 0


def test_translate_on_stable_change():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    pipe.process_frame(BLACK, now=0.0)
    result = pipe.process_frame(BLACK, now=0.5)         # STABLE_CHANGED
    assert result is not None
    assert result.dst_text == "dst1"
    assert backend.calls == 1


def test_cache_hit_skips_backend():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    pipe.process_frame(BLACK, now=0.0)
    pipe.process_frame(BLACK, now=0.5)                  # 翻译并缓存
    again = pipe.process_frame(BLACK, now=0.6, force=True)  # 同帧强制 → 命中缓存
    assert again.dst_text == "dst1"
    assert backend.calls == 1                           # 没有再调后端


def test_force_translates_immediately():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    result = pipe.process_frame(WHITE, now=0.0, force=True)  # 首帧强制
    assert result is not None
    assert backend.calls == 1
