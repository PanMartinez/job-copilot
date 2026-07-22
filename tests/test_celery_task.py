"""Tests the Celery task's sync/async bridge in isolation.

Deliberately a plain `def test_...`, not `async def`: pytest-asyncio's `auto`
mode only wraps async tests in a running event loop. `task.apply(...)` runs the
task body synchronously in-process, which calls `asyncio.run()` internally
(see app/tasks/ingestion.py) - that would raise "asyncio.run() cannot be
called from a running event loop" if this test itself were async.
"""

from app.tasks import ingestion


def test_ingest_document_task_delegates_to_async_ingestion(monkeypatch) -> None:
    calls = []

    async def _fake_run(document_id: int) -> int:
        calls.append(document_id)
        return 3

    monkeypatch.setattr(ingestion, "_run", _fake_run)

    result = ingestion.ingest_document.apply(args=(42,))

    assert result.result == 3
    assert calls == [42]
