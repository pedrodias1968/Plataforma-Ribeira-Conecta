"""API tests for the read-only sampling grid preview (F-AGRO-003)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import Polygon, mapping

from ribeira_platform.api import Settings, create_app
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from ribeira_platform.service import RibeiraApplication
from ribeira_platform.storage import SQLiteStore

_CENTER_LON = -47.9
_CENTER_LAT = -24.5
_CRS = "EPSG:31983"


def _square_lonlat(half_metres: float = 100.0) -> dict:
    """Return a ~200x200 m square around lon/lat computed with pyproj.

    The square is built in the projected SIRGAS 2000 / UTM 23S CRS and
    reprojected to EPSG:4326, so the geometry is a genuine metric field.
    """
    to_projected = Transformer.from_crs("EPSG:4326", _CRS, always_xy=True)
    to_lonlat = Transformer.from_crs(_CRS, "EPSG:4326", always_xy=True)
    easting, northing = to_projected.transform(_CENTER_LON, _CENTER_LAT)
    corners = [
        (easting - half_metres, northing - half_metres),
        (easting + half_metres, northing - half_metres),
        (easting + half_metres, northing + half_metres),
        (easting - half_metres, northing + half_metres),
        (easting - half_metres, northing - half_metres),
    ]
    return mapping(Polygon([to_lonlat.transform(x, y) for x, y in corners]))


class SamplingPreviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.application = RibeiraApplication(self.store)
        self.tenant = self.application.create_tenant("Synthetic sampling tenant")
        self.other_tenant = self.application.create_tenant("Other sampling tenant")
        self.property = self.application.create_property(
            self.tenant.id,
            "TEST_SAMPLING_PROPERTY",
            _square_lonlat(500.0),
            "EPSG:4326",
        )
        self.other_property = self.application.create_property(
            self.tenant.id,
            "TEST_SAMPLING_OTHER_PROPERTY",
            _square_lonlat(500.0),
            "EPSG:4326",
        )
        settings = Settings("test", "sqlite", None, (), "development", 1_000_000)
        self.client = TestClient(
            create_app(
                self.application,
                DevelopmentIdentityProvider(
                    "admin",
                    AuthContext(
                        "admin",
                        None,
                        roles=frozenset({"PLATFORM_ADMIN"}),
                        is_platform_admin=True,
                    ),
                ),
                settings=settings,
            )
        )
        self.viewer_client = TestClient(
            create_app(
                self.application,
                DevelopmentIdentityProvider(
                    "viewer",
                    AuthContext("viewer", self.tenant.id, roles=frozenset({"VIEWER"})),
                ),
                settings=settings,
            )
        )

    def tearDown(self) -> None:
        self.store.close()

    def _field_payload(self) -> dict:
        return {
            "name": "TEST_SAMPLING_FIELD",
            "status": "ACTIVE",
            "geometry_geojson": _square_lonlat(100.0),
            "geometry_crs": "EPSG:4326",
            "source_reference": "synthetic_test_data field walk",
            "observed_at": "2026-09-24T12:00:00+00:00",
            "classification": "MANUAL_CONFIRMED",
        }

    def _create_field(self, property_id: str) -> str:
        path = f"/v1/tenants/{self.tenant.id}/properties/{property_id}/fields"
        response = self.client.post(
            path, headers={"Authorization": "Bearer admin"}, json=self._field_payload()
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def _preview_path(self, property_id: str, field_id: str, spacing_m: float) -> str:
        return (
            f"/v1/tenants/{self.tenant.id}/properties/{property_id}"
            f"/fields/{field_id}/sampling/grid-preview?spacing_m={spacing_m}"
        )

    def test_preview_returns_derived_grid_without_persisting(self) -> None:
        field_id = self._create_field(self.property.id)
        response = self.client.get(
            self._preview_path(self.property.id, field_id, 50.0),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["field_id"], field_id)
        self.assertEqual(body["property_id"], self.property.id)
        self.assertEqual(body["status"], "PREVIEW_NOT_PERSISTED")
        self.assertEqual(body["projected_crs"], _CRS)
        self.assertEqual(body["derivation_method"], "REGULAR_GRID")
        self.assertEqual(body["spacing_m"], 50.0)
        self.assertEqual(body["points"]["type"], "FeatureCollection")
        self.assertGreater(len(body["points"]["features"]), 0)

        listed = self.client.get(
            f"/v1/tenants/{self.tenant.id}/properties/{self.property.id}/soil-samples",
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["items"], [])

    def test_preview_requires_soil_read_permission(self) -> None:
        field_id = self._create_field(self.property.id)
        denied = self.viewer_client.get(
            self._preview_path(self.property.id, field_id, 50.0),
            headers={"Authorization": "Bearer viewer"},
        )
        self.assertEqual(denied.status_code, 403)

    def test_preview_missing_field_returns_404(self) -> None:
        response = self.client.get(
            self._preview_path(self.property.id, "does-not-exist", 50.0),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(response.status_code, 404)

    def test_preview_field_of_other_property_returns_404(self) -> None:
        other_field_id = self._create_field(self.other_property.id)
        response = self.client.get(
            self._preview_path(self.property.id, other_field_id, 50.0),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(response.status_code, 404)

    def test_preview_rejects_non_positive_spacing(self) -> None:
        field_id = self._create_field(self.property.id)
        response = self.client.get(
            self._preview_path(self.property.id, field_id, 0.0),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(response.status_code, 422)

    def test_preview_rejects_oversized_grid(self) -> None:
        field_id = self._create_field(self.property.id)
        response = self.client.get(
            self._preview_path(self.property.id, field_id, 0.01),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(response.status_code, 422)

    def test_preview_does_not_persist_soil_samples(self) -> None:
        field_id = self._create_field(self.property.id)
        preview = self.client.get(
            self._preview_path(self.property.id, field_id, 50.0),
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertGreater(len(preview.json()["points"]["features"]), 0)

        listed = self.client.get(
            f"/v1/tenants/{self.tenant.id}/properties/{self.property.id}/soil-samples",
            headers={"Authorization": "Bearer admin"},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["items"], [])

    def test_preview_denies_viewer_of_other_tenant(self) -> None:
        field_id = self._create_field(self.property.id)
        settings = Settings("test", "sqlite", None, (), "development", 1_000_000)
        other_client = TestClient(
            create_app(
                self.application,
                DevelopmentIdentityProvider(
                    "other-viewer",
                    AuthContext(
                        "other-viewer", self.other_tenant.id, roles=frozenset({"VIEWER"})
                    ),
                ),
                settings=settings,
            )
        )
        denied = other_client.get(
            self._preview_path(self.property.id, field_id, 50.0),
            headers={"Authorization": "Bearer other-viewer"},
        )
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
