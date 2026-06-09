"""按 dHash 缓存翻译结果的 LRU。"""

from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self._data: "OrderedDict[str, Any]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
