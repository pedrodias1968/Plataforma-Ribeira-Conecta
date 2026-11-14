"""Unit tests for ribeira_platform.providers.

Covers the pure/deterministic provider catalogue primitives:

* the immutable ``ProviderMetadata`` dataclass and its defaults;
* ``ProviderRegistry`` registration and lookup semantics;
* ``endpoint_allowed`` allowlisting rules (status gating, exact vs. prefix
  matching, trailing-slash handling and the catalog endpoint);
* ``asset_host_allowed`` host matching and the ``asset_endpoint`` /
  ``asset_bucket`` accessors.

Everything here is local and deterministic; no database, network or external
provider is required or contacted.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from ribeira_platform.providers import ProviderMetadata, ProviderRegistry


def _metadata(**overrides: object) -> ProviderMetadata:
    base: dict[str, object] = {
        "provider_id": "sentinel-2",
        "name": "Sentinel-2",
        "category": "imagery",
        "authority": "ESA",
        "endpoint": "https://catalogue.example.com/stac",
        "license": "open",
        "authentication_type": "none",
        "spatial_resolution": "10m",
        "temporal_resolution": "5d",
        "version": "1",
        "status": "ACTIVE",
    }
    base.update(overrides)
    return ProviderMetadata(**base)  # type: ignore[arg-type]


class ProviderMetadataTests(unittest.TestCase):
    def test_required_fields_are_preserved(self) -> None:
        metadata = _metadata()
        self.assertEqual(metadata.provider_id, "sentinel-2")
        self.assertEqual(metadata.name, "Sentinel-2")
        self.assertEqual(metadata.category, "imagery")
        self.assertEqual(metadata.authority, "ESA")
        self.assertEqual(metadata.endpoint, "https://catalogue.example.com/stac")
        self.assertEqual(metadata.authentication_type, "none")
        self.assertEqual(metadata.status, "ACTIVE")

    def test_optional_fields_default_to_none_or_empty(self) -> None:
        metadata = _metadata()
        self.assertIsNone(metadata.last_success)
        self.assertIsNone(metadata.last_failure)
        self.assertIsNone(metadata.organization)
        self.assertIsNone(metadata.provider_type)
        self.assertIsNone(metadata.documentation_url)
        self.assertIsNone(metadata.catalog_endpoint)
        self.assertIsNone(metadata.api_standard)
        self.assertIsNone(metadata.stac_version)
        self.assertEqual(metadata.asset_hosts, frozenset())
        self.assertIsNone(metadata.asset_endpoint)
        self.assertIsNone(metadata.asset_bucket)

    def test_metadata_is_frozen(self) -> None:
        metadata = _metadata()
        with self.assertRaises(FrozenInstanceError):
            metadata.status = "INACTIVE"  # type: ignore[misc]


class ProviderRegistryRegistrationTests(unittest.TestCase):
    def test_empty_registry_returns_none(self) -> None:
        registry = ProviderRegistry()
        self.assertIsNone(registry.get("sentinel-2"))

    def test_constructing_with_providers_indexes_by_provider_id(self) -> None:
        first = _metadata(provider_id="alpha")
        second = _metadata(provider_id="beta")
        registry = ProviderRegistry([first, second])
        self.assertIs(registry.get("alpha"), first)
        self.assertIs(registry.get("beta"), second)

    def test_register_adds_and_overwrites(self) -> None:
        registry = ProviderRegistry()
        first = _metadata(provider_id="alpha", name="First")
        registry.register(first)
        self.assertIs(registry.get("alpha"), first)

        replacement = _metadata(provider_id="alpha", name="Second")
        registry.register(replacement)
        self.assertIs(registry.get("alpha"), replacement)
        self.assertEqual(registry.get("alpha").name, "Second")


class EndpointAllowedTests(unittest.TestCase):
    def test_unknown_provider_is_not_allowed(self) -> None:
        registry = ProviderRegistry()
        self.assertFalse(registry.endpoint_allowed("missing", "https://x.example/a"))

    def test_non_active_provider_is_not_allowed(self) -> None:
        metadata = _metadata(provider_id="alpha", status="INACTIVE")
        registry = ProviderRegistry([metadata])
        self.assertFalse(
            registry.endpoint_allowed("alpha", "https://catalogue.example.com/stac")
        )

    def test_exact_endpoint_is_allowed(self) -> None:
        registry = ProviderRegistry([_metadata(provider_id="alpha")])
        self.assertTrue(
            registry.endpoint_allowed("alpha", "https://catalogue.example.com/stac")
        )

    def test_child_path_of_endpoint_is_allowed(self) -> None:
        registry = ProviderRegistry([_metadata(provider_id="alpha")])
        self.assertTrue(
            registry.endpoint_allowed(
                "alpha", "https://catalogue.example.com/stac/collections/foo"
            )
        )

    def test_similar_prefix_without_separator_is_not_allowed(self) -> None:
        registry = ProviderRegistry([_metadata(provider_id="alpha")])
        self.assertFalse(
            registry.endpoint_allowed(
                "alpha", "https://catalogue.example.com/stac-evil/foo"
            )
        )

    def test_trailing_slash_on_base_does_not_break_child_paths(self) -> None:
        metadata = _metadata(
            provider_id="alpha", endpoint="https://catalogue.example.com/stac/"
        )
        registry = ProviderRegistry([metadata])
        self.assertTrue(
            registry.endpoint_allowed(
                "alpha", "https://catalogue.example.com/stac/collections"
            )
        )

    def test_catalog_endpoint_is_also_allowlisted(self) -> None:
        metadata = _metadata(
            provider_id="alpha",
            endpoint=None,
            catalog_endpoint="https://catalog.example.com/api",
        )
        registry = ProviderRegistry([metadata])
        self.assertTrue(
            registry.endpoint_allowed("alpha", "https://catalog.example.com/api/items")
        )
        self.assertTrue(registry.endpoint_allowed("alpha", "https://catalog.example.com/api"))

    def test_provider_without_endpoints_allows_none(self) -> None:
        metadata = _metadata(provider_id="alpha", endpoint=None, catalog_endpoint=None)
        registry = ProviderRegistry([metadata])
        self.assertFalse(registry.endpoint_allowed("alpha", "https://example.com"))


class AssetAccessorTests(unittest.TestCase):
    def test_asset_host_allowed_is_case_insensitive(self) -> None:
        metadata = _metadata(
            provider_id="alpha", asset_hosts=frozenset({"assets.example.com"})
        )
        registry = ProviderRegistry([metadata])
        self.assertTrue(registry.asset_host_allowed("alpha", "assets.example.com"))
        self.assertTrue(registry.asset_host_allowed("alpha", "ASSETS.EXAMPLE.COM"))

    def test_asset_host_not_in_set_is_rejected(self) -> None:
        metadata = _metadata(
            provider_id="alpha", asset_hosts=frozenset({"assets.example.com"})
        )
        registry = ProviderRegistry([metadata])
        self.assertFalse(registry.asset_host_allowed("alpha", "evil.example.com"))
        self.assertFalse(registry.asset_host_allowed("missing", "assets.example.com"))

    def test_asset_endpoint_and_bucket_return_configured_values(self) -> None:
        metadata = _metadata(
            provider_id="alpha",
            asset_endpoint="https://assets.example.com",
            asset_bucket="bucket-name",
        )
        registry = ProviderRegistry([metadata])
        self.assertEqual(registry.asset_endpoint("alpha"), "https://assets.example.com")
        self.assertEqual(registry.asset_bucket("alpha"), "bucket-name")

    def test_asset_endpoint_and_bucket_are_none_for_unknown_provider(self) -> None:
        registry = ProviderRegistry()
        self.assertIsNone(registry.asset_endpoint("missing"))
        self.assertIsNone(registry.asset_bucket("missing"))


if __name__ == "__main__":
    unittest.main()
