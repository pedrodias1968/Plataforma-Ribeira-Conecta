"""Unit tests for Soil Intelligence: sample points, lab analyses, agronomic formulas and API."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from ribeira_platform.service import RibeiraApplication
from ribeira_platform.soil import (
    SoilValidationError,
    compute_soil_derived_indices,
    validate_soil_sample_point,
)
from ribeira_platform.storage import SQLiteStore


PROPERTY_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-47.0, -24.0],
            [-46.98, -24.0],
            [-46.98, -24.02],
            [-47.0, -24.02],
            [-47.0, -24.0],
        ]
    ],
}

FIELD_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-46.995, -24.005],
            [-46.985, -24.005],
            [-46.985, -24.015],
            [-46.995, -24.015],
            [-46.995, -24.005],
        ]
    ],
}


class SoilUnitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.app = RibeiraApplication(self.store)
        self.tenant = self.app.create_tenant("Soil Test Tenant")
        self.property = self.app.create_property(
            self.tenant.id,
            "Fazenda Solo Teste",
            PROPERTY_GEOJSON,
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )

    def test_soil_derived_indices_calculation(self) -> None:
        # Ca=2.5, Mg=1.0, K=0.2 -> SB = 3.7

        result = compute_soil_derived_indices(
            calcium=2.5, magnesium=1.0, potassium=0.2, h_al=0.0
        )
        self.assertEqual(result["sum_of_bases"], 3.7)

        result = compute_soil_derived_indices(
            calcium=3.2, magnesium=1.1, potassium=0.3, h_al=2.4
        )
        self.assertAlmostEqual(result["cec"], 7.0, places=2)
        self.assertAlmostEqual(result["base_saturation_percent"], 65.71, places=2)

    def test_soil_derived_indices_missing_values(self) -> None:
        # Missing values default to zero
        result = compute_soil_derived_indices()
        self.assertEqual(result["sum_of_bases"], 0.0)
        self.assertEqual(result["cec"], 0.0)
        self.assertEqual(result["base_saturation_percent"], 0.0)

    def test_soil_sample_location_validation(self) -> None:
        valid_point = {"type": "Point", "coordinates": [-46.99, -24.01]}
        validate_soil_sample_point(valid_point, PROPERTY_GEOJSON, FIELD_GEOJSON)

        outside_field_point = {"type": "Point", "coordinates": [-46.998, -24.001]}
        validate_soil_sample_point(outside_field_point, PROPERTY_GEOJSON)

        with self.assertRaises(SoilValidationError):
            validate_soil_sample_point(outside_field_point, PROPERTY_GEOJSON, FIELD_GEOJSON)

        outside_prop_point = {"type": "Point", "coordinates": [-47.1, -24.5]}
        with self.assertRaises(SoilValidationError):
            validate_soil_sample_point(outside_prop_point, PROPERTY_GEOJSON)

        invalid_geojson = {"type": "Polygon", "coordinates": []}
        with self.assertRaises(SoilValidationError):
            validate_soil_sample_point(invalid_geojson, PROPERTY_GEOJSON)

        invalid_coordinates = {"type": "Point", "coordinates": [200.0, 0.0]}
        with self.assertRaises(SoilValidationError):
            validate_soil_sample_point(invalid_coordinates, PROPERTY_GEOJSON)

    def test_soil_sample_point_and_lab_analysis_lifecycle(self) -> None:
        field = self.app.fields.create(
            self.tenant.id,
            property_id=self.property.id,
            name="Talhão 01",
            status="ACTIVE",
            geometry_geojson=FIELD_GEOJSON,
            geometry_crs="EPSG:4326",
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )

        sample = self.app.register_soil_sample_point(
            self.tenant.id,
            self.property.id,
            sample_code="AMOSTRA-T1-01",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:30:00+00:00",
            collector_name="Carlos Agrônomo",
            location_geojson={"type": "Point", "coordinates": [-46.99, -24.01]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_GARMIN_64S",
            field_id=field.id,
            actor="agronomist@test.local",
        )
        self.assertEqual(sample.sample_code, "AMOSTRA-T1-01")
        self.assertEqual(sample.field_id, field.id)

        samples = self.app.list_soil_sample_points(self.tenant.id, self.property.id)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].id, sample.id)

        analysis = self.app.register_soil_lab_analysis(
            self.tenant.id,
            sample.id,
            lab_name="Lab AgroAnálise Registro",
            report_number="LAUDO-2026-9812",
            report_date="2026-09-24",
            ph_cacl2=5.2,
            organic_matter_g_dm3=28.0,
            phosphorus_mg_dm3=15.0,
            potassium_cmolc_dm3=0.3,
            calcium_cmolc_dm3=3.2,
            magnesium_cmolc_dm3=1.1,
            potential_acidity_h_al=2.4,
            clay_percent=35.0,
            silt_percent=25.0,
            sand_percent=40.0,
            actor="agronomist@test.local",
        )
        self.assertEqual(analysis.report_number, "LAUDO-2026-9812")
        self.assertAlmostEqual(analysis.cation_exchange_capacity_cec or 0, 7.0, places=2)
        self.assertAlmostEqual(analysis.base_saturation_percent or 0, 65.71, places=2)

        analyses = self.app.list_soil_lab_analyses(self.tenant.id, sample.id)
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0].id, analysis.id)

    def test_soil_api_endpoints_and_rbac(self) -> None:
        client_admin = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    "admin-token",
                    AuthContext("admin-user", self.tenant.id, roles=frozenset({"TENANT_ADMIN"})),
                ),
            )
        )
        client_operator = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    "operator-token",
                    AuthContext("operator-user", self.tenant.id, roles=frozenset({"OPERATOR"})),
                ),
            )
        )
        client_viewer = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    "viewer-token",
                    AuthContext("viewer-user", self.tenant.id, roles=frozenset({"VIEWER"})),
                ),
            )
        )

        headers_admin = {"Authorization": "Bearer admin-token"}
        headers_operator = {"Authorization": "Bearer operator-token"}
        headers_viewer = {"Authorization": "Bearer viewer-token"}

        payload_sample = {
            "sample_code": "SOLO-01",
            "depth_top_cm": 0.0,
            "depth_bottom_cm": 20.0,
            "collection_date": "2026-09-22T08:00:00+00:00",
            "collector_name": "João Técnico",
            "location_geojson": {"type": "Point", "coordinates": [-46.99, -24.01]},
            "source_reference": "CADERNETA_CAMPO",
            "classification": "MANUAL_CONFIRMED",
        }

        res_forbidden = client_viewer.post(
            f"/v1/tenants/{self.tenant.id}/properties/{self.property.id}/soil-samples",
            headers=headers_viewer,
            json=payload_sample,
        )
        self.assertEqual(res_forbidden.status_code, 403)

        res_create = client_admin.post(
            f"/v1/tenants/{self.tenant.id}/properties/{self.property.id}/soil-samples",
            headers=headers_admin,
            json=payload_sample,
        )
        self.assertEqual(res_create.status_code, 201)
        sample_id = res_create.json()["id"]
        self.assertIsNotNone(res_create.json()["evidence_id"])

        res_list = client_operator.get(
            f"/v1/tenants/{self.tenant.id}/properties/{self.property.id}/soil-samples",
            headers=headers_operator,
        )
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()["items"]), 1)

        payload_analysis = {
            "lab_name": "Lab Solo Vale",
            "report_number": "REP-2026-001",
            "report_date": "2026-09-23",
            "ph_h2o": 5.8,
            "organic_matter_g_dm3": 30.0,
            "calcium_cmolc_dm3": 4.0,
            "magnesium_cmolc_dm3": 1.5,
            "potassium_cmolc_dm3": 0.5,
            "potential_acidity_h_al": 2.0,
        }

        res_analysis_forbidden = client_viewer.post(
            f"/v1/tenants/{self.tenant.id}/soil-samples/{sample_id}/lab-analyses",
            headers=headers_viewer,
            json=payload_analysis,
        )
        self.assertEqual(res_analysis_forbidden.status_code, 403)

        res_analysis = client_admin.post(
            f"/v1/tenants/{self.tenant.id}/soil-samples/{sample_id}/lab-analyses",
            headers=headers_admin,
            json=payload_analysis,
        )
        self.assertEqual(res_analysis.status_code, 201)
        analysis_data = res_analysis.json()
        self.assertEqual(analysis_data["lab_name"], "Lab Solo Vale")
        self.assertAlmostEqual(analysis_data["base_saturation_percent"], 75.0, places=1)

        res_analysis_list = client_operator.get(
            f"/v1/tenants/{self.tenant.id}/soil-samples/{sample_id}/lab-analyses",
            headers=headers_operator,
        )
        self.assertEqual(res_analysis_list.status_code, 200)
        self.assertEqual(len(res_analysis_list.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()
