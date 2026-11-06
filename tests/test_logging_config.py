"""Unit tests for ribeira_platform.logging_config.

Covers the pure/deterministic parts of the structured logging module:

* the ``SENSITIVE_KEYS`` redaction set;
* ``JsonFormatter.format`` payload construction, context propagation and
  sensitive-value redaction (no database, network or external provider);
* ``configure_structured_logging`` root-logger wiring, which only touches the
  in-process ``logging`` root logger and is fully restored in ``tearDown``.

Everything here is local and deterministic; no infrastructure path needs to be
skipped.
"""

from __future__ import annotations

import json
import logging
import unittest
from unittest import mock

from ribeira_platform import logging_config
from ribeira_platform.audit_context import request_context
from ribeira_platform.logging_config import (
    SENSITIVE_KEYS,
    JsonFormatter,
    configure_structured_logging,
)


def _make_record(
    msg: str = "hello",
    level: int = logging.INFO,
    name: str = "ribeira.test",
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class SensitiveKeysTests(unittest.TestCase):
    def test_sensitive_keys_is_a_set_of_lowercase_names(self) -> None:
        self.assertIsInstance(SENSITIVE_KEYS, set)
        for key in SENSITIVE_KEYS:
            self.assertEqual(key, key.lower())

    def test_expected_sensitive_names_present(self) -> None:
        for expected in ("password", "token", "secret", "authorization"):
            self.assertIn(expected, SENSITIVE_KEYS)


class JsonFormatterPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.formatter = JsonFormatter()

    def test_basic_payload_fields(self) -> None:
        record = _make_record(msg="formatted message")
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "ribeira.test")
        self.assertEqual(payload["message"], "formatted message")
        self.assertIn("timestamp", payload)

    def test_message_args_are_interpolated(self) -> None:
        record = _make_record()
        record.msg = "value=%s"
        record.args = ("x",)
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["message"], "value=x")

    def test_optional_record_attributes_are_included(self) -> None:
        record = _make_record(
            tenant_id="tenant-1",
            job_id="job-9",
            status="SUCCEEDED",
            failure_code="NONE",
        )
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["tenant_id"], "tenant-1")
        self.assertEqual(payload["job_id"], "job-9")
        self.assertEqual(payload["status"], "SUCCEEDED")
        self.assertEqual(payload["failure_code"], "NONE")

    def test_absent_optional_attributes_are_omitted(self) -> None:
        record = _make_record()
        payload = json.loads(self.formatter.format(record))
        for key in ("tenant_id", "job_id", "status", "failure_code"):
            self.assertNotIn(key, payload)

    def test_output_is_valid_json(self) -> None:
        record = _make_record()
        text = self.formatter.format(record)
        self.assertEqual(text, json.dumps(json.loads(text), ensure_ascii=False))


class JsonFormatterContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.formatter = JsonFormatter()

    def test_context_ids_injected_when_absent(self) -> None:
        record = _make_record()
        with request_context("req-1", "corr-1"):
            payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["correlation_id"], "corr-1")

    def test_explicit_record_context_takes_precedence(self) -> None:
        record = _make_record(request_id="explicit-req", correlation_id="explicit-corr")
        with request_context("ctx-req", "ctx-corr"):
            payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["request_id"], "explicit-req")
        self.assertEqual(payload["correlation_id"], "explicit-corr")

    def test_no_context_omits_ids(self) -> None:
        record = _make_record()
        payload = json.loads(self.formatter.format(record))
        self.assertNotIn("request_id", payload)
        self.assertNotIn("correlation_id", payload)


class JsonFormatterRedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.formatter = JsonFormatter()

    def test_sensitive_attribute_is_redacted(self) -> None:
        record = _make_record(password="super-secret")
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["password"], "[REDACTED]")

    def test_sensitive_matching_is_case_insensitive_substring(self) -> None:
        record = _make_record(API_Token="abc123")
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["API_Token"], "[REDACTED]")

    def test_non_sensitive_attributes_are_not_redacted_or_added(self) -> None:
        # Redaction only rewrites keys matching SENSITIVE_KEYS; non-sensitive
        # extras are neither redacted nor copied into the payload.
        record = _make_record(property_id="prop-42", amount=7)
        payload = json.loads(self.formatter.format(record))
        self.assertNotIn("property_id", payload)
        self.assertNotIn("amount", payload)

    def test_plain_message_is_not_redacted_by_key_scan(self) -> None:
        record = _make_record(msg="token rotation complete")
        payload = json.loads(self.formatter.format(record))
        self.assertEqual(payload["message"], "token rotation complete")


class ConfigureStructuredLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = logging.getLogger()
        self._saved_handlers = list(self.root.handlers)
        self._saved_level = self.root.level
        self._had_flag = hasattr(self.root, "_ribeira_structured")
        self._saved_flag = getattr(self.root, "_ribeira_structured", None)
        self.addCleanup(self._restore_root)

    def _restore_root(self) -> None:
        self.root.handlers = self._saved_handlers
        self.root.setLevel(self._saved_level)
        if self._had_flag:
            self.root._ribeira_structured = self._saved_flag  # type: ignore[attr-defined]
        else:
            try:
                del self.root._ribeira_structured  # type: ignore[attr-defined]
            except AttributeError:
                pass

    def _reset(self) -> None:
        self.root.handlers = []
        self.root.setLevel(logging.WARNING)
        if hasattr(self.root, "_ribeira_structured"):
            del self.root._ribeira_structured  # type: ignore[attr-defined]

    def test_configures_root_with_json_stream_handler(self) -> None:
        self._reset()
        configure_structured_logging()
        self.assertEqual(len(self.root.handlers), 1)
        handler = self.root.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIsInstance(handler.formatter, JsonFormatter)
        self.assertEqual(self.root.level, logging.INFO)
        self.assertTrue(getattr(self.root, "_ribeira_structured"))

    def test_is_idempotent(self) -> None:
        self._reset()
        configure_structured_logging()
        first_handler = self.root.handlers[0]
        configure_structured_logging()
        self.assertEqual(len(self.root.handlers), 1)
        self.assertIs(self.root.handlers[0], first_handler)

    def test_uses_stdout_stream(self) -> None:
        self._reset()
        with mock.patch.object(logging_config.sys, "stdout") as fake_stdout:
            configure_structured_logging()
        self.assertEqual(len(self.root.handlers), 1)
        self.assertIs(self.root.handlers[0].stream, fake_stdout)

    def test_returns_none(self) -> None:
        self._reset()
        self.assertIsNone(configure_structured_logging())


if __name__ == "__main__":
    unittest.main()
