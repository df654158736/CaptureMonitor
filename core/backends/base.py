"""翻译后端抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TranslationResult:
    src_text: str
    dst_text: str
    segments: List[Dict[str, str]] = field(default_factory=list)  # [{src, dst, rect}]


class TranslationBackend(ABC):
    @abstractmethod
    def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
