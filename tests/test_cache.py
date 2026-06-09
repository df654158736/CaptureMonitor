# tests/test_cache.py
from core.cache import LRUCache


def test_put_get():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    assert c.get("a") == 1


def test_miss_returns_none():
    assert LRUCache().get("missing") is None


def test_eviction_beyond_capacity():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)          # 淘汰最久未用的 a
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_access_refreshes_lru_order():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1  # a 变最近使用
    c.put("c", 3)           # 淘汰 b 而不是 a
    assert c.get("a") == 1
    assert c.get("b") is None
