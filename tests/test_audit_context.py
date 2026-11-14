"""Unit tests for ribeira_platform.audit_context.

Covers the pure request/correlation context helpers. No database, network or
external provider is required; every case here is deterministic and local.
"""

from __future__ import annotations

import asyncio
import contextvars
import unittest

from ribeira_platform.audit_context import current_context, request_context


class CurrentContextDefaultTests(unittest.TestCase):
    def test_default_context_is_unset(self) -> None:
        self.assertEqual(current_context(), (None, None))

    def test_default_is_outside_active_context(self) -> None:
        request_id, correlation_id = current_context()
        self.assertIsNone(request_id)
        self.assertIsNone(correlation_id)


class RequestContextTests(unittest.TestCase):
    def test_sets_context_inside_block(self) -> None:
        with request_context("req-1", "corr-1"):
            self.assertEqual(current_context(), ("req-1", "corr-1"))

    def test_resets_context_after_block(self) -> None:
        with request_context("req-1", "corr-1"):
            pass
        self.assertEqual(current_context(), (None, None))

    def test_resets_context_after_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with request_context("req-1", "corr-1"):
                self.assertEqual(current_context(), ("req-1", "corr-1"))
                raise RuntimeError("boom")
        self.assertEqual(current_context(), (None, None))

    def test_nested_contexts_restore_previous_values(self) -> None:
        with request_context("outer-req", "outer-corr"):
            self.assertEqual(current_context(), ("outer-req", "outer-corr"))
            with request_context("inner-req", "inner-corr"):
                self.assertEqual(current_context(), ("inner-req", "inner-corr"))
            self.assertEqual(current_context(), ("outer-req", "outer-corr"))
        self.assertEqual(current_context(), (None, None))

    def test_context_values_are_not_shared_between_blocks(self) -> None:
        with request_context("first", "first-corr"):
            first = current_context()
        with request_context("second", "second-corr"):
            second = current_context()
        self.assertNotEqual(first, second)
        self.assertEqual(first, ("first", "first-corr"))
        self.assertEqual(second, ("second", "second-corr"))


class ContextVarIsolationTests(unittest.TestCase):
    def test_context_is_isolated_per_contextvars_context(self) -> None:
        def run_in_isolated_context() -> tuple[str | None, str | None]:
            with request_context("isolated-req", "isolated-corr"):
                return current_context()

        ctx = contextvars.copy_context()
        observed = ctx.run(run_in_isolated_context)
        self.assertEqual(observed, ("isolated-req", "isolated-corr"))
        self.assertEqual(current_context(), (None, None))

    def test_context_is_isolated_between_async_tasks(self) -> None:
        async def worker(
            request_id: str, results: dict[str, tuple[str | None, str | None]]
        ) -> None:
            with request_context(request_id, f"{request_id}-corr"):
                await asyncio.sleep(0)
                results[request_id] = current_context()

        async def main() -> dict[str, tuple[str | None, str | None]]:
            results: dict[str, tuple[str | None, str | None]] = {}
            await asyncio.gather(worker("a", results), worker("b", results))
            return results

        results = asyncio.run(main())
        self.assertEqual(results["a"], ("a", "a-corr"))
        self.assertEqual(results["b"], ("b", "b-corr"))


if __name__ == "__main__":
    unittest.main()
