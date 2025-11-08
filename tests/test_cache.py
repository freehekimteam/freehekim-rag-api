"""Cache behavior tests for RAG pipeline"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from rag import pipeline  # noqa E402


def _reset_cache(monkeypatch):
    """Clear cache and zero metrics for an isolated test run."""
    pipeline.flush_cache()
    monkeypatch.setattr(
        pipeline,
        "_cache_metrics",
        {"hit": 0, "miss": 0, "expired": 0, "evicted": 0},
        raising=False,
    )


def test_cache_hit_updates_stats(monkeypatch):
    _reset_cache(monkeypatch)
    monkeypatch.setattr(pipeline.settings, "cache_ttl_seconds", 60.0, raising=False)
    monkeypatch.setattr(pipeline.settings, "cache_max_entries", 4, raising=False)

    payload = {"question": "q", "answer": "a"}
    pipeline._cache_set("key_hit", payload)
    cached = pipeline._cache_get("key_hit")

    assert cached == payload

    stats = pipeline.cache_stats()
    assert stats["size"] == 1
    assert stats["metrics"]["hit"] == 1
    assert stats["metrics"]["miss"] == 0

    flushed = pipeline.flush_cache()
    assert flushed == 1
    assert pipeline.cache_stats()["size"] == 0


def test_cache_eviction_respects_max_entries(monkeypatch):
    _reset_cache(monkeypatch)
    monkeypatch.setattr(pipeline.settings, "cache_ttl_seconds", 60.0, raising=False)
    monkeypatch.setattr(pipeline.settings, "cache_max_entries", 1, raising=False)

    pipeline._cache_set("first", {"answer": "one"})
    pipeline._cache_set("second", {"answer": "two"})

    assert pipeline.cache_stats()["size"] == 1
    assert pipeline._cache_get("first") is None

    metrics = pipeline.cache_stats()["metrics"]
    assert metrics["evicted"] == 1
    assert metrics["miss"] == 1


def test_cache_entry_expires_on_ttl(monkeypatch):
    _reset_cache(monkeypatch)
    monkeypatch.setattr(pipeline.settings, "cache_ttl_seconds", 0.01, raising=False)
    monkeypatch.setattr(pipeline.settings, "cache_max_entries", 4, raising=False)

    pipeline._cache_set("ttl", {"answer": "value"})
    time.sleep(0.02)
    assert pipeline._cache_get("ttl") is None

    metrics = pipeline.cache_stats()["metrics"]
    assert metrics["expired"] >= 1
