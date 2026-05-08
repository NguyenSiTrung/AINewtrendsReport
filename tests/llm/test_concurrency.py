"""Tests for LLM concurrency cap."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from ainews.llm.concurrency import (
    configure,
    get_semaphore,
    get_threading_semaphore,
    limited_invoke,
    limited_invoke_sync,
)


class MockLLM:
    """Mock LLM that tracks concurrent invocations."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.concurrent = 0
        self.max_concurrent = 0
        self._lock = threading.Lock()

    async def ainvoke(self, *args, **kwargs):
        with self._lock:
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
        await asyncio.sleep(self.delay)
        with self._lock:
            self.concurrent -= 1
        return "response"

    def invoke(self, *args, **kwargs):
        with self._lock:
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
        time.sleep(self.delay)
        with self._lock:
            self.concurrent -= 1
        return "response"


class TestConfigure:
    def test_configure_sets_semaphore(self) -> None:
        configure(max_concurrency=3)
        sem = get_semaphore()
        assert sem._value == 3  # type: ignore[attr-defined]

    def test_reconfigure_resets(self) -> None:
        configure(max_concurrency=5)
        configure(max_concurrency=2)
        sem = get_semaphore()
        assert sem._value == 2  # type: ignore[attr-defined]


class TestAsyncLimitedInvoke:
    @pytest.mark.asyncio
    async def test_limits_concurrency(self) -> None:
        configure(max_concurrency=2)
        llm = MockLLM(delay=0.1)

        # Launch 5 concurrent tasks
        tasks = [limited_invoke(llm, "test") for _ in range(5)]
        await asyncio.gather(*tasks)

        assert llm.max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_returns_response(self) -> None:
        configure(max_concurrency=2)
        llm = MockLLM()
        result = await limited_invoke(llm, "test")
        assert result == "response"


class TestSyncLimitedInvoke:
    def test_limits_concurrency_sync(self) -> None:
        configure(max_concurrency=2)
        llm = MockLLM(delay=0.1)

        threads = []
        for _ in range(5):
            t = threading.Thread(target=limited_invoke_sync, args=(llm, "test"))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert llm.max_concurrent <= 2

    def test_returns_response_sync(self) -> None:
        configure(max_concurrency=2)
        llm = MockLLM()
        result = limited_invoke_sync(llm, "test")
        assert result == "response"


class TestGetSemaphore:
    def test_lazy_creation(self) -> None:
        configure(max_concurrency=4)
        sem = get_semaphore()
        assert sem is not None
        tsem = get_threading_semaphore()
        assert tsem is not None
