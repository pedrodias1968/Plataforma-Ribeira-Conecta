"""Unit tests for ribeira_platform.runtime_health.

Covers the probe aggregation logic of check() and the HTTP probe helper _http
using local fakes and mocks. No real database, network or external provider is
required. The only real filesystem access is a temporary directory used as an
object-storage root, which is deterministic and self-contained.
"""

from __future__ import annotations

import os
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from ribeira_platform import runtime_health


class HttpProbeTests(unittest.TestCase):
    def test_returns_true_on_200(self) -> None:
        response = MagicMock()
        response.status = 200
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        with patch.object(
            runtime_health.urllib.request, "urlopen", return_value=response
        ):
            self.assertTrue(runtime_health._http("http://127.0.0.1/health/live"))

    def test_returns_false_on_url_error(self) -> None:
        with patch.object(
            runtime_health.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("refused"),
        ):
            self.assertFalse(runtime_health._http("http://127.0.0.1/health/live"))


class CheckTargetTests(unittest.TestCase):
    def test_api_target_only_probes_api(self) -> None:
        with patch.object(runtime_health, "_http", return_value=True) as http:
            result = runtime_health.check("api")
        self.assertEqual(
            set(result["checks"]),
            {"api_liveness", "api_readiness"},
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(http.call_count, 2)

    def test_frontend_target_probes_frontend_endpoints(self) -> None:
        with patch.object(runtime_health, "_http", return_value=True):
            result = runtime_health.check("frontend")
        self.assertEqual(
            set(result["checks"]),
            {"frontend_liveness", "frontend_readiness"},
        )
        self.assertEqual(result["status"], "ready")

    def test_worker_target_probes_metrics(self) -> None:
        with patch.object(runtime_health, "_http", return_value=True):
            result = runtime_health.check("worker")
        self.assertEqual(set(result["checks"]), {"worker_metrics"})
        self.assertEqual(result["status"], "ready")

    def test_status_degraded_when_any_probe_fails(self) -> None:
        with patch.object(runtime_health, "_http", side_effect=[True, False]):
            result = runtime_health.check("api")
        self.assertEqual(result["checks"]["api_liveness"], True)
        self.assertEqual(result["checks"]["api_readiness"], False)
        self.assertEqual(result["status"], "degraded")


class DatabaseQueueCheckTests(unittest.TestCase):
    def test_no_dsn_marks_database_and_queue_degraded(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = runtime_health.check("database")
        self.assertEqual(
            result["checks"],
            {"database_readiness": False, "queue_readiness": False},
        )
        self.assertEqual(result["status"], "degraded")
        self.assertNotIn("queue", result)

    def test_dsn_with_store_reports_queue_counts(self) -> None:
        rows = [
            {"status": "PENDING", "count": 2},
            {"status": "DONE", "count": 5},
        ]
        execute_result = MagicMock()
        execute_result.fetchall.return_value = rows
        connection = MagicMock()
        connection.execute.return_value = execute_result
        transaction = MagicMock()
        transaction.__enter__ = MagicMock(return_value=transaction)
        transaction.__exit__ = MagicMock(return_value=False)
        store = MagicMock()
        store.ready.return_value = True
        store.connection = connection
        store.tenant_transaction.return_value = transaction
        with patch.dict(os.environ, {"RIBEIRA_DATABASE_URL": "postgresql://x/y"}):
            with patch.object(runtime_health, "PostgresStore", return_value=store):
                result = runtime_health.check("queue")
        self.assertEqual(result["checks"]["database_readiness"], True)
        self.assertEqual(result["checks"]["queue_readiness"], True)
        self.assertEqual(result["queue"], {"PENDING": 2, "DONE": 5})
        self.assertEqual(result["status"], "ready")
        store.close.assert_called_once()
        store.tenant_transaction.assert_called_once_with(None, platform_admin=True)

    def test_dsn_store_failure_marks_both_degraded(self) -> None:
        with patch.dict(os.environ, {"RIBEIRA_DATABASE_URL": "postgresql://x/y"}):
            with patch.object(
                runtime_health,
                "PostgresStore",
                side_effect=RuntimeError("cannot connect"),
            ):
                result = runtime_health.check("queue")
        self.assertEqual(result["checks"]["database_readiness"], False)
        self.assertEqual(result["checks"]["queue_readiness"], False)
        self.assertNotIn("queue", result)
        self.assertEqual(result["status"], "degraded")


class ObjectStorageCheckTests(unittest.TestCase):
    def test_writable_directory_is_ready(self) -> None:
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"RIBEIRA_OBJECT_STORAGE_ROOT": directory}):
                result = runtime_health.check("storage")
        self.assertEqual(result["checks"], {"object_storage_ready": True})
        self.assertEqual(result["status"], "ready")

    def test_missing_directory_is_degraded(self) -> None:
        with TemporaryDirectory() as directory:
            missing = str(Path(directory, "does-not-exist"))
            with patch.dict(os.environ, {"RIBEIRA_OBJECT_STORAGE_ROOT": missing}):
                result = runtime_health.check("storage")
        self.assertEqual(result["checks"], {"object_storage_ready": False})
        self.assertEqual(result["status"], "degraded")

    def test_default_storage_root_used_when_env_absent(self) -> None:
        captured: dict[str, str] = {}
        real_path = runtime_health.Path

        def fake_path(value: str) -> Path:
            captured["value"] = value
            return real_path(value)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(runtime_health, "Path", side_effect=fake_path):
                runtime_health.check("storage")
        self.assertEqual(captured["value"], ".local/object-storage")


class AllTargetTests(unittest.TestCase):
    def test_all_ready_when_every_component_ready(self) -> None:
        rows: list[dict[str, object]] = []
        execute_result = MagicMock()
        execute_result.fetchall.return_value = rows
        connection = MagicMock()
        connection.execute.return_value = execute_result
        transaction = MagicMock()
        transaction.__enter__ = MagicMock(return_value=transaction)
        transaction.__exit__ = MagicMock(return_value=False)
        store = MagicMock()
        store.ready.return_value = True
        store.connection = connection
        store.tenant_transaction.return_value = transaction
        with TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "RIBEIRA_DATABASE_URL": "postgresql://x/y",
                    "RIBEIRA_OBJECT_STORAGE_ROOT": directory,
                },
            ):
                with patch.object(runtime_health, "_http", return_value=True):
                    with patch.object(
                        runtime_health, "PostgresStore", return_value=store
                    ):
                        result = runtime_health.check("all")
        self.assertEqual(result["status"], "ready")
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["queue"], {})

    def test_all_degraded_when_http_probe_fails(self) -> None:
        with TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {"RIBEIRA_OBJECT_STORAGE_ROOT": directory},
                clear=True,
            ):
                with patch.object(runtime_health, "_http", return_value=False):
                    result = runtime_health.check("all")
        self.assertEqual(result["status"], "degraded")


class MainTests(unittest.TestCase):
    def test_main_exits_zero_when_ready(self) -> None:
        result = {"status": "ready", "checks": {}}
        with patch("sys.argv", ["runtime_health", "api"]):
            with patch.object(runtime_health, "check", return_value=result):
                with patch.object(runtime_health, "print"):
                    with self.assertRaises(SystemExit) as ctx:
                        runtime_health.main()
        self.assertEqual(ctx.exception.code, 0)

    def test_main_exits_one_when_degraded_without_wait(self) -> None:
        result = {"status": "degraded", "checks": {}}
        with patch("sys.argv", ["runtime_health", "api", "--wait-seconds", "0"]):
            with patch.object(runtime_health, "check", return_value=result):
                with patch.object(runtime_health, "print"):
                    with self.assertRaises(SystemExit) as ctx:
                        runtime_health.main()
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
