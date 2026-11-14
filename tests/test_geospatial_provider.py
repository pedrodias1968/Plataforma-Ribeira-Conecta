"""Unit tests for ribeira_platform.geospatial_provider.

Covers the pure/deterministic parts of the CDSE STAC provider:

* ``StacProviderError`` code/message semantics;
* ``CopernicusStacConfig`` defaults and immutability;
* ``default_copernicus_registry`` provider metadata and allowlisting;
* ``_geojson_bbox`` envelope extraction and validation;
* ``CopernicusStacAdapter._url`` allowlist/SSRF handling;
* ``CopernicusStacAdapter.asset_href_allowed`` scheme/host rules;
* ``CopernicusStacAdapter.search`` pagination, limits and error mapping using
  an in-memory fake transport (no network, database or external provider).

Network-facing helpers (``_request_json`` and the redirect handler) are
exercised only through fakes; the real HTTP transport is not contacted.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from typing import Any

from ribeira_platform.geospatial import (
    SatelliteSearchRequest,
    SceneSelectionPolicy,
)
from ribeira_platform.geospatial_provider import (
    CopernicusStacAdapter,
    CopernicusStacConfig,
    StacProviderError,
    _geojson_bbox,
    default_copernicus_registry,
)
from ribeira_platform.providers import ProviderRegistry
from ribeira_platform.security import SSRFBlocked


class _AllowAllPolicy:
    """Network policy fake that never resolves DNS or blocks a URL."""

    def validate(self, url: str) -> None:
        return None


class _BlockingPolicy:
    def validate(self, url: str) -> None:
        raise SSRFBlocked("blocked by test policy")


def _request(
    *,
    max_candidates: int = 100,
    cloud_cover_limit: Any = None,
) -> SatelliteSearchRequest:
    return SatelliteSearchRequest(
        property_id="property-1",
        collection_id="sentinel-2-l2a",
        datetime_start="2026-09-01T00:00:00Z",
        datetime_end="2026-09-30T00:00:00Z",
        selection_policy=SceneSelectionPolicy(
            cloud_cover_limit=cloud_cover_limit,
            max_candidates=max_candidates,
        ),
    )


class StacProviderErrorTests(unittest.TestCase):
    def test_code_and_message_are_preserved(self) -> None:
        error = StacProviderError("INVALID_PAYLOAD", "bad payload")
        self.assertEqual(error.code, "INVALID_PAYLOAD")
        self.assertEqual(str(error), "bad payload")
        self.assertIsInstance(error, RuntimeError)


class CopernicusStacConfigTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = CopernicusStacConfig()
        self.assertEqual(config.provider_id, "COPERNICUS_CDSE")
        self.assertEqual(
            config.catalog_endpoint, "https://stac.dataspace.copernicus.eu/v1/"
        )
        self.assertEqual(config.collection_id, "sentinel-2-l2a")
        self.assertEqual(config.timeout_seconds, 30.0)
        self.assertEqual(config.max_pages, 10)

    def test_config_is_frozen(self) -> None:
        config = CopernicusStacConfig()
        with self.assertRaises(FrozenInstanceError):
            config.provider_id = "OTHER"  # type: ignore[misc]


class DefaultCopernicusRegistryTests(unittest.TestCase):
    def test_registry_contains_active_cdse_provider(self) -> None:
        registry = default_copernicus_registry()
        metadata = registry.get("COPERNICUS_CDSE")
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata.status, "ACTIVE")
        self.assertEqual(metadata.api_standard, "STAC")
        self.assertEqual(metadata.stac_version, "1.1.0")
        self.assertEqual(metadata.asset_bucket, "eodata")
        self.assertIn("eodata", metadata.asset_hosts)

    def test_catalog_endpoint_is_allowlisted(self) -> None:
        registry = default_copernicus_registry()
        self.assertTrue(
            registry.endpoint_allowed(
                "COPERNICUS_CDSE",
                "https://stac.dataspace.copernicus.eu/v1/search",
            )
        )
        self.assertFalse(
            registry.endpoint_allowed(
                "COPERNICUS_CDSE", "https://evil.example.com/v1/search"
            )
        )

    def test_custom_config_is_used(self) -> None:
        config = CopernicusStacConfig(
            provider_id="CUSTOM",
            catalog_endpoint="https://catalog.example.com/stac/",
        )
        registry = default_copernicus_registry(config)
        metadata = registry.get("CUSTOM")
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata.catalog_endpoint, "https://catalog.example.com/stac/")
        self.assertIn("catalog.example.com", metadata.asset_hosts)

    def test_endpoint_without_hostname_is_rejected(self) -> None:
        config = CopernicusStacConfig(catalog_endpoint="not-a-url")
        with self.assertRaises(ValueError):
            default_copernicus_registry(config)


class GeojsonBboxTests(unittest.TestCase):
    def test_polygon_envelope(self) -> None:
        aoi = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-48.0, -24.0],
                    [-47.0, -24.0],
                    [-47.0, -23.0],
                    [-48.0, -23.0],
                    [-48.0, -24.0],
                ]
            ],
        }
        self.assertEqual(_geojson_bbox(aoi), (-48.0, -24.0, -47.0, -23.0))

    def test_nested_multipolygon_envelope(self) -> None:
        aoi = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-50.0, -25.0], [-49.0, -25.0], [-49.0, -24.0]]],
                [[[-48.0, -23.0], [-47.5, -23.0], [-47.5, -22.5]]],
            ],
        }
        self.assertEqual(_geojson_bbox(aoi), (-50.0, -25.0, -47.5, -22.5))

    def test_missing_coordinates_are_rejected(self) -> None:
        with self.assertRaises(StacProviderError) as ctx:
            _geojson_bbox({"type": "Polygon"})
        self.assertEqual(ctx.exception.code, "INVALID_AOI")

    def test_empty_coordinates_are_rejected(self) -> None:
        with self.assertRaises(StacProviderError) as ctx:
            _geojson_bbox({"type": "Polygon", "coordinates": []})
        self.assertEqual(ctx.exception.code, "INVALID_AOI")

    def test_out_of_range_coordinate_is_rejected(self) -> None:
        aoi = {"type": "Point", "coordinates": [200.0, 0.0]}
        with self.assertRaises(StacProviderError) as ctx:
            _geojson_bbox(aoi)
        self.assertEqual(ctx.exception.code, "INVALID_AOI")


class AdapterUrlTests(unittest.TestCase):
    def _adapter(
        self, registry: ProviderRegistry | None = None, policy: Any = None
    ) -> CopernicusStacAdapter:
        return CopernicusStacAdapter(
            registry or default_copernicus_registry(),
            network_policy=policy or _AllowAllPolicy(),
        )

    def test_url_joins_catalog_endpoint(self) -> None:
        adapter = self._adapter()
        self.assertEqual(
            adapter._url("search"),
            "https://stac.dataspace.copernicus.eu/v1/search",
        )

    def test_url_strips_leading_slash(self) -> None:
        adapter = self._adapter()
        self.assertEqual(
            adapter._url("/collections/sentinel-2-l2a"),
            "https://stac.dataspace.copernicus.eu/v1/collections/sentinel-2-l2a",
        )

    def test_missing_provider_is_rejected(self) -> None:
        adapter = self._adapter(registry=ProviderRegistry([]))
        with self.assertRaises(StacProviderError) as ctx:
            adapter._url("search")
        self.assertEqual(ctx.exception.code, "PROVIDER_NOT_CONFIGURED")

    def test_non_allowlisted_endpoint_is_rejected(self) -> None:
        from ribeira_platform.providers import ProviderMetadata

        registry = ProviderRegistry(
            [
                ProviderMetadata(
                    provider_id="COPERNICUS_CDSE",
                    name="Inactive CDSE",
                    category="EARTH_OBSERVATION",
                    authority="COPERNICUS",
                    endpoint="https://stac.dataspace.copernicus.eu/v1/",
                    license="other",
                    authentication_type="NOT_DETERMINED",
                    spatial_resolution=None,
                    temporal_resolution=None,
                    version="STAC 1.1.0",
                    status="INACTIVE",
                    catalog_endpoint="https://stac.dataspace.copernicus.eu/v1/",
                )
            ]
        )
        adapter = CopernicusStacAdapter(registry, network_policy=_AllowAllPolicy())
        with self.assertRaises(StacProviderError) as ctx:
            adapter._url("search")
        self.assertEqual(ctx.exception.code, "PROVIDER_ENDPOINT_NOT_ALLOWED")

    def test_ssrf_blocked_is_mapped(self) -> None:
        adapter = self._adapter(policy=_BlockingPolicy())
        with self.assertRaises(StacProviderError) as ctx:
            adapter._url("search")
        self.assertEqual(ctx.exception.code, "SSRF_BLOCKED")


class AssetHrefTests(unittest.TestCase):
    def _adapter(self) -> CopernicusStacAdapter:
        return CopernicusStacAdapter(
            default_copernicus_registry(), network_policy=_AllowAllPolicy()
        )

    def test_allowlisted_https_host(self) -> None:
        adapter = self._adapter()
        self.assertTrue(
            adapter.asset_href_allowed(
                "https://stac.dataspace.copernicus.eu/foo.tif"
            )
        )

    def test_s3_scheme_with_allowlisted_host(self) -> None:
        adapter = self._adapter()
        self.assertTrue(adapter.asset_href_allowed("s3://eodata/foo.tif"))

    def test_unknown_host_is_rejected(self) -> None:
        adapter = self._adapter()
        self.assertFalse(adapter.asset_href_allowed("https://evil.example.com/foo.tif"))

    def test_unsupported_scheme_is_rejected(self) -> None:
        adapter = self._adapter()
        self.assertFalse(adapter.asset_href_allowed("ftp://eodata/foo.tif"))

    def test_missing_hostname_is_rejected(self) -> None:
        adapter = self._adapter()
        self.assertFalse(adapter.asset_href_allowed("https:///foo.tif"))


class _FakeAdapter(CopernicusStacAdapter):
    """Adapter with an in-memory transport; never touches the network."""

    def __init__(self, pages: list[dict[str, Any]]) -> None:
        super().__init__(
            default_copernicus_registry(), network_policy=_AllowAllPolicy()
        )
        self.pages = pages
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def _url(self, suffix: str) -> str:
        return "https://stac.dataspace.copernicus.eu/v1/" + suffix.lstrip("/")

    def _request_json(
        self, method: str, url: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.calls.append((method, url, payload))
        return self.pages.pop(0)


class SearchTests(unittest.TestCase):
    def test_single_page_returns_items(self) -> None:
        adapter = _FakeAdapter(
            [{"features": [{"id": "scene-1"}, {"id": "scene-2"}], "links": []}]
        )
        result = adapter.search(_request(), {"type": "Point", "coordinates": [0, 0]})
        self.assertEqual([item["id"] for item in result.items], ["scene-1", "scene-2"])
        self.assertEqual(len(result.raw_pages), 1)
        method, url, payload = adapter.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/search"))
        assert payload is not None
        self.assertEqual(payload["collections"], ["sentinel-2-l2a"])
        self.assertEqual(payload["limit"], 100)
        self.assertNotIn("query", payload)

    def test_cloud_cover_limit_adds_query(self) -> None:
        adapter = _FakeAdapter([{"features": [], "links": []}])
        adapter.search(
            _request(cloud_cover_limit=20),
            {"type": "Point", "coordinates": [0, 0]},
        )
        _, _, payload = adapter.calls[0]
        assert payload is not None
        self.assertEqual(payload["query"], {"eo:cloud_cover": {"lte": 20.0}})

    def test_max_candidates_caps_items(self) -> None:
        adapter = _FakeAdapter(
            [
                {
                    "features": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                    "links": [],
                }
            ]
        )
        result = adapter.search(
            _request(max_candidates=2),
            {"type": "Point", "coordinates": [0, 0]},
        )
        self.assertEqual([item["id"] for item in result.items], ["a", "b"])

    def test_next_link_is_followed(self) -> None:
        adapter = _FakeAdapter(
            [
                {
                    "features": [{"id": "a"}],
                    "links": [
                        {
                            "rel": "next",
                            "href": "https://stac.dataspace.copernicus.eu/v1/search?page=2",
                        }
                    ],
                },
                {"features": [{"id": "b"}], "links": []},
            ]
        )
        result = adapter.search(
            _request(), {"type": "Point", "coordinates": [0, 0]}
        )
        self.assertEqual([item["id"] for item in result.items], ["a", "b"])
        self.assertEqual(adapter.calls[1][0], "GET")
        self.assertIsNone(adapter.calls[1][2])

    def test_non_allowlisted_next_link_is_rejected(self) -> None:
        adapter = _FakeAdapter(
            [
                {
                    "features": [],
                    "links": [{"rel": "next", "href": "https://evil.example.com/x"}],
                }
            ]
        )
        with self.assertRaises(StacProviderError) as ctx:
            adapter.search(_request(), {"type": "Point", "coordinates": [0, 0]})
        self.assertEqual(ctx.exception.code, "PROVIDER_ENDPOINT_NOT_ALLOWED")

    def test_missing_features_is_invalid_payload(self) -> None:
        adapter = _FakeAdapter([{"links": []}])
        with self.assertRaises(StacProviderError) as ctx:
            adapter.search(_request(), {"type": "Point", "coordinates": [0, 0]})
        self.assertEqual(ctx.exception.code, "INVALID_PAYLOAD")

    def test_provider_error_is_propagated(self) -> None:
        class _FailingAdapter(_FakeAdapter):
            def _request_json(
                self, method: str, url: str, payload: dict[str, Any] | None = None
            ) -> dict[str, Any]:
                raise StacProviderError("RATE_LIMITED", "slow down")

        adapter = _FailingAdapter([])
        with self.assertRaises(StacProviderError) as ctx:
            adapter.search(_request(), {"type": "Point", "coordinates": [0, 0]})
        self.assertEqual(ctx.exception.code, "RATE_LIMITED")


if __name__ == "__main__":
    unittest.main()
