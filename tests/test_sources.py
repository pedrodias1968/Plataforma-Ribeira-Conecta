from __future__ import annotations

import json
import unittest
import urllib.error
from unittest.mock import patch

from ribeira_platform.epistemology import (
    DataClassification,
    IngestionStatus,
    QualityFlag,
)
from ribeira_platform.models import FetchResult, Observation, Property, Source
from ribeira_platform.providers import ProviderMetadata, ProviderRegistry
from ribeira_platform.security import SSRFBlocked
from ribeira_platform.sources import (
    HttpJsonSourceAdapter,
    SyntheticFixtureAdapter,
    _NoRedirectHandler,
    _parse_observations,
)


def _property(property_id: str = "prop-1", tenant_id: str = "tenant-1") -> Property:
    return Property(id=property_id, tenant_id=tenant_id, name="Property")


def _source(
    endpoint: str | None = "https://example.test/data",
    provider: str = "demo",
    tenant_id: str = "tenant-1",
) -> Source:
    return Source(
        id="src-1",
        tenant_id=tenant_id,
        name="Source",
        source_type="API",
        provider=provider,
        endpoint=endpoint,
    )


def _metadata(endpoint: str = "https://example.test/data") -> ProviderMetadata:
    return ProviderMetadata(
        provider_id="demo",
        name="Demo provider",
        category="TEST",
        authority="TEST",
        endpoint=endpoint,
        license=None,
        authentication_type="NONE",
        spatial_resolution=None,
        temporal_resolution=None,
        version=None,
        status="ACTIVE",
    )


def _valid_observation(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "metric": "rainfall",
        "value": 12.5,
        "unit": "mm",
        "observation_timestamp": "2026-09-11T10:59:10Z",
    }
    item.update(overrides)
    return item


class _AllowAllPolicy:
    def validate(self, url: str) -> None:
        return None


class _BlockingPolicy:
    def __init__(self, reason: str = "blocked") -> None:
        self.reason = reason

    def validate(self, url: str) -> None:
        raise SSRFBlocked(self.reason)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class _FakeOpener:
    def __init__(
        self, response: _FakeResponse | None = None, error: Exception | None = None
    ) -> None:
        self._response = response
        self._error = error
        self.last_request: object | None = None
        self.last_timeout: float | None = None

    def open(self, request: object, timeout: float | None = None) -> _FakeResponse:
        self.last_request = request
        self.last_timeout = timeout
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _adapter(
    *,
    policy: object | None = None,
    registry: ProviderRegistry | None = None,
    timeout: float = 10.0,
) -> HttpJsonSourceAdapter:
    return HttpJsonSourceAdapter(
        timeout_seconds=timeout,
        network_policy=policy or _AllowAllPolicy(),  # type: ignore[arg-type]
        provider_registry=registry or ProviderRegistry([_metadata()]),
    )


class ParseObservationsTests(unittest.TestCase):
    def test_parses_valid_observation_with_provenance_fields(self) -> None:
        payload = {
            "observations": [
                _valid_observation(
                    raw_data_reference="raw/ref.json",
                    dataset_version="v2",
                    spatial_resolution="30m",
                    temporal_resolution="daily",
                    crs="EPSG:4326",
                    checksum="abc123",
                )
            ]
        }
        observations = _parse_observations(payload, "tenant-1", _property(), _source())
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertIsInstance(observation, Observation)
        self.assertEqual(observation.tenant_id, "tenant-1")
        self.assertEqual(observation.property_id, "prop-1")
        self.assertEqual(observation.source_id, "src-1")
        self.assertEqual(observation.metric, "rainfall")
        self.assertEqual(observation.value, 12.5)
        self.assertEqual(observation.unit, "mm")
        self.assertEqual(observation.classification, DataClassification.OBSERVED)
        self.assertEqual(observation.observation_timestamp, "2026-09-11T10:59:10+00:00")
        self.assertEqual(
            observation.original_observation_timestamp, "2026-09-11T10:59:10Z"
        )
        self.assertEqual(observation.raw_data_reference, "raw/ref.json")
        self.assertEqual(observation.dataset_version, "v2")
        self.assertEqual(observation.spatial_resolution, "30m")
        self.assertEqual(observation.temporal_resolution, "daily")
        self.assertEqual(observation.crs, "EPSG:4326")
        self.assertEqual(observation.checksum, "abc123")

    def test_missing_observations_list_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "observations list"):
            _parse_observations({}, "tenant-1", _property(), _source())

    def test_non_list_observations_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "observations list"):
            _parse_observations(
                {"observations": {}}, "tenant-1", _property(), _source()
            )

    def test_non_object_observation_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be an object"):
            _parse_observations(
                {"observations": ["nope"]}, "tenant-1", _property(), _source()
            )

    def test_missing_required_fields_raises(self) -> None:
        payload = {"observations": [{"metric": "rainfall"}]}
        with self.assertRaisesRegex(ValueError, "missing fields"):
            _parse_observations(payload, "tenant-1", _property(), _source())

    def test_non_numeric_value_raises(self) -> None:
        payload = {"observations": [_valid_observation(value="12.5")]}
        with self.assertRaisesRegex(ValueError, "numeric or null"):
            _parse_observations(payload, "tenant-1", _property(), _source())

    def test_null_value_downgrades_valid_quality_to_unknown(self) -> None:
        payload = {
            "observations": [_valid_observation(value=None, quality_flag="VALID")]
        }
        observations = _parse_observations(payload, "tenant-1", _property(), _source())
        self.assertIsNone(observations[0].value)
        self.assertEqual(observations[0].quality_flag, QualityFlag.UNKNOWN)

    def test_null_value_preserves_non_valid_quality_flag(self) -> None:
        payload = {
            "observations": [_valid_observation(value=None, quality_flag="INVALID")]
        }
        observations = _parse_observations(payload, "tenant-1", _property(), _source())
        self.assertEqual(observations[0].quality_flag, QualityFlag.INVALID)

    def test_null_unit_is_preserved_as_none(self) -> None:
        payload = {"observations": [_valid_observation(unit=None)]}
        observations = _parse_observations(payload, "tenant-1", _property(), _source())
        self.assertIsNone(observations[0].unit)

    def test_naive_timestamp_is_rejected(self) -> None:
        payload = {
            "observations": [
                _valid_observation(observation_timestamp="2026-09-11T10:59:10")
            ]
        }
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            _parse_observations(payload, "tenant-1", _property(), _source())

    def test_invalid_quality_flag_raises(self) -> None:
        payload = {"observations": [_valid_observation(quality_flag="NOT_A_FLAG")]}
        with self.assertRaises(ValueError):
            _parse_observations(payload, "tenant-1", _property(), _source())


class SyntheticFixtureAdapterTests(unittest.TestCase):
    def test_marks_observations_and_result_as_simulated(self) -> None:
        adapter = SyntheticFixtureAdapter([_valid_observation()])
        result = adapter.fetch_property_observations("tenant-1", _property(), _source())
        self.assertEqual(result.status, IngestionStatus.INGESTED)
        self.assertEqual(result.source_classification, DataClassification.SIMULATED)
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(
            result.observations[0].classification, DataClassification.SIMULATED
        )
        self.assertEqual(result.observations[0].value, 12.5)
        self.assertIn("synthetic", result.message)

    def test_defaults_synthetic_data_flag_to_true(self) -> None:
        adapter = SyntheticFixtureAdapter([])
        self.assertTrue(adapter.synthetic_data)
        result = adapter.fetch_property_observations("tenant-1", _property(), _source())
        self.assertEqual(result.status, IngestionStatus.INGESTED)
        self.assertEqual(result.observations, [])


class NoRedirectHandlerTests(unittest.TestCase):
    def test_redirect_is_blocked(self) -> None:
        handler = _NoRedirectHandler()
        with self.assertRaises(SSRFBlocked):
            handler.redirect_request(
                object(), object(), 302, "Found", {}, "https://elsewhere.test"
            )


class HttpJsonSourceAdapterTests(unittest.TestCase):
    def test_missing_endpoint_returns_source_unavailable(self) -> None:
        result = _adapter().fetch_property_observations(
            "tenant-1", _property(), _source(endpoint=None)
        )
        self.assertIsInstance(result, FetchResult)
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("not configured", result.message)

    def test_disallowed_scheme_returns_source_unavailable(self) -> None:
        result = _adapter().fetch_property_observations(
            "tenant-1", _property(), _source(endpoint="ftp://example.test/data")
        )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("scheme", result.message)

    def test_missing_host_returns_source_unavailable(self) -> None:
        result = _adapter().fetch_property_observations(
            "tenant-1", _property(), _source(endpoint="http:///data")
        )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])

    def test_network_policy_block_returns_source_unavailable(self) -> None:
        result = _adapter(
            policy=_BlockingPolicy("private network")
        ).fetch_property_observations("tenant-1", _property(), _source())
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("network policy", result.message)
        self.assertIn("private network", result.message)

    def test_unregistered_provider_returns_source_unavailable(self) -> None:
        result = _adapter(registry=ProviderRegistry()).fetch_property_observations(
            "tenant-1", _property(), _source()
        )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("not allowlisted", result.message)

    def test_endpoint_outside_allowlist_returns_source_unavailable(self) -> None:
        registry = ProviderRegistry([_metadata("https://allowed.test/base")])
        result = _adapter(registry=registry).fetch_property_observations(
            "tenant-1", _property(), _source()
        )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("not allowlisted", result.message)

    def test_successful_response_is_ingested(self) -> None:
        body = json.dumps({"observations": [_valid_observation()]}).encode("utf-8")
        opener = _FakeOpener(response=_FakeResponse(body))
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter(timeout=4.0).fetch_property_observations(
                "tenant-1", _property(), _source()
            )
        self.assertEqual(result.status, IngestionStatus.INGESTED)
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(result.observations[0].value, 12.5)
        self.assertIn("ingested", result.message)
        self.assertEqual(opener.last_timeout, 4.0)
        request = opener.last_request
        self.assertIn("property_id=prop-1", request.full_url)  # type: ignore[attr-defined]
        self.assertEqual(request.get_header("Accept"), "application/json")  # type: ignore[attr-defined]

    def test_existing_query_string_uses_ampersand(self) -> None:
        body = json.dumps({"observations": []}).encode("utf-8")
        opener = _FakeOpener(response=_FakeResponse(body))
        endpoint = "https://example.test/data?token=abc"
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter(
                registry=ProviderRegistry([_metadata(endpoint)])
            ).fetch_property_observations(
                "tenant-1", _property(), _source(endpoint=endpoint)
            )
        self.assertEqual(result.status, IngestionStatus.INGESTED)
        self.assertEqual(result.observations, [])
        self.assertIn(
            "?token=abc&property_id=prop-1",
            opener.last_request.full_url,  # type: ignore[attr-defined]
        )

    def test_invalid_json_returns_invalid_payload(self) -> None:
        opener = _FakeOpener(response=_FakeResponse(b"not-json"))
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter().fetch_property_observations(
                "tenant-1", _property(), _source()
            )
        self.assertEqual(result.status, IngestionStatus.INVALID_PAYLOAD)
        self.assertEqual(result.observations, [])
        self.assertIn("invalid", result.message)

    def test_payload_missing_observations_returns_invalid_payload(self) -> None:
        opener = _FakeOpener(response=_FakeResponse(json.dumps({}).encode("utf-8")))
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter().fetch_property_observations(
                "tenant-1", _property(), _source()
            )
        self.assertEqual(result.status, IngestionStatus.INVALID_PAYLOAD)
        self.assertEqual(result.observations, [])

    def test_network_error_returns_source_unavailable(self) -> None:
        opener = _FakeOpener(error=urllib.error.URLError("connection refused"))
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter().fetch_property_observations(
                "tenant-1", _property(), _source()
            )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("provider unavailable", result.message)
        self.assertIn("URLError", result.message)

    def test_timeout_returns_source_unavailable(self) -> None:
        opener = _FakeOpener(error=TimeoutError("timed out"))
        with patch(
            "ribeira_platform.sources.urllib.request.build_opener",
            return_value=opener,
        ):
            result = _adapter().fetch_property_observations(
                "tenant-1", _property(), _source()
            )
        self.assertEqual(result.status, IngestionStatus.SOURCE_UNAVAILABLE)
        self.assertEqual(result.observations, [])
        self.assertIn("TimeoutError", result.message)


if __name__ == "__main__":
    unittest.main()
