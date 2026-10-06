"""PostgreSQL/PostGIS integration tests for Soil Intelligence: spatial guard, evidence, RLS."""

from __future__ import annotations

import os
import unittest

from shapely.geometry import Polygon, mapping

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.service import RibeiraApplication
from ribeira_platform.soil import SoilValidationError


DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class SoilPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = PostgresStore(DATABASE_URL)  # type: ignore[arg-type]
        self.application = RibeiraApplication(self.store)
        self.store.connection.execute("BEGIN")

    def tearDown(self) -> None:
        self.store.connection.rollback()
        self.store.close()

    def tenant(self, name: str):
        return self.application.create_tenant(name)

    @staticmethod
    def polygon(west: float, south: float, east: float, north: float) -> dict:
        return mapping(
            Polygon(
                [
                    (west, south),
                    (east, south),
                    (east, north),
                    (west, north),
                    (west, south),
                ]
            )
        )

    def test_soil_sample_postgis_containment_and_rls_isolation(self) -> None:
        tenant_a = self.tenant("Soil Postgres Tenant A")
        tenant_b = self.tenant("Soil Postgres Tenant B")

        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda A",
            self.polygon(-47.0, -24.02, -46.98, -24.0),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )

        field_a = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão A1",
            geometry_geojson=self.polygon(-46.995, -24.015, -46.985, -24.005),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )

        # 1. Valid sample point inside property and field
        sample_a = self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-A1",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-46.99, -24.01]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.assertEqual(sample_a.sample_code, "SOLO-A1")

        # 2. Rejection of point outside property boundary
        with self.assertRaises(SoilValidationError):
            self.application.register_soil_sample_point(
                tenant_a.id,
                prop_a.id,
                sample_code="SOLO-OUTSIDE",
                depth_top_cm=0.0,
                depth_bottom_cm=20.0,
                collection_date="2026-09-21T09:00:00+00:00",
                collector_name="Agrônomo A",
                location_geojson={"type": "Point", "coordinates": [-47.1, -24.5]},
                classification=DataClassification.MANUAL_CONFIRMED,
                source_reference="GPS_PRO",
                actor="agronomist@test.local",
            )

        # 3. Lab analysis creation
        analysis_a = self.application.register_soil_lab_analysis(
            tenant_a.id,
            sample_a.id,
            lab_name="Laboratório Vale",
            report_number="LAUDO-2026-01",
            report_date="2026-09-23",
            ph_h2o=6.0,
            organic_matter_g_dm3=35.0,
            calcium_cmolc_dm3=4.5,
            magnesium_cmolc_dm3=1.8,
            potassium_cmolc_dm3=0.4,
            potential_acidity_h_al=1.8,
            actor="agronomist@test.local",
        )
        # SB = 4.5 + 1.8 + 0.4 = 6.7
        # CTC = 6.7 + 1.8 = 8.5
        # V% = (6.7 / 8.5) * 100 = 78.82%
        self.assertAlmostEqual(analysis_a.base_saturation_percent or 0, 78.82, places=2)

        # 4. RLS isolation: Tenant B cannot see Tenant A's sample points or lab analyses
        samples_tenant_b = self.application.soil.list_sample_points(tenant_b.id, prop_a.id)
        self.assertEqual(len(samples_tenant_b), 0)

        analyses_tenant_b = self.application.soil.list_lab_analyses(tenant_b.id, sample_a.id)
        self.assertEqual(len(analyses_tenant_b), 0)

    def test_field_scoped_sample_point_queries(self) -> None:
        tenant_a = self.tenant("Soil Field Queries Tenant")
        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda Query Test",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        field_a = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão Query A",
            geometry_geojson=self.polygon(-47.095, -24.115, -47.085, -24.105),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        field_b = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão Query B",
            geometry_geojson=self.polygon(-47.099, -24.119, -47.091, -24.111),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-FIELD-A",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-47.093, -24.112]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-FIELD-B",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo B",
            location_geojson={"type": "Point", "coordinates": [-47.095, -24.117]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_b.id,
            actor="agronomist@test.local",
        )
        samples_by_field_a = self.application.soil.list_sample_points(tenant_a.id, prop_a.id, field_id=field_a.id)
        samples_by_field_b = self.application.soil.list_sample_points(tenant_a.id, prop_a.id, field_id=field_b.id)
        self.assertEqual(len(samples_by_field_a), 1)
        self.assertEqual(samples_by_field_a[0].sample_code, "SOLO-FIELD-A")
        self.assertEqual(len(samples_by_field_b), 1)
        self.assertEqual(samples_by_field_b[0].sample_code, "SOLO-FIELD-B")

    def test_cross_tenant_lab_analysis_isolation(self) -> None:
        tenant_a = self.tenant("Soil Lab Tenant A")
        tenant_b = self.tenant("Soil Lab Tenant B")
        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda Lab A",
            self.polygon(-47.2, -24.22, -47.18, -24.2),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        field_a = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão Lab A1",
            geometry_geojson=self.polygon(-47.195, -24.215, -47.185, -24.205),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        sample_a = self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-LAB-A",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-47.19, -24.21]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.application.register_soil_lab_analysis(
            tenant_a.id,
            sample_a.id,
            ph_water=5.6,
            ph_cacl2=4.9,
            ho3p=12.5,
            k=1.8,
            ca=4.5,
            mg=2.1,
            al=0.0,
            h_al=1.8,
            ctc_ph7=10.0,
            ctc_ph7_1=8.2,
            v_percent=78.0,
            summary={"aluminum_saturation_percent": 22.0, "base_saturation_percent": 78.0},
            analysis_date="2026-09-25T14:00:00+00:00",
            laboratory="Lab Teste S.A.",
            analysis_method="EMBRAPA",
            actor="lab@test.local",
        )
        analyses_tenant_b = self.application.soil.list_lab_analyses(tenant_b.id, sample_a.id)
        self.assertEqual(len(analyses_tenant_b), 0)
        with self.assertRaises(SoilValidationError):
            self.application.register_soil_lab_analysis(
                tenant_b.id,
                sample_a.id,
                ph_water=6.0,
                ph_cacl2=5.3,
                ho3p=10.0,
                k=1.5,
                ca=4.0,
                mg=2.0,
                al=0.0,
                h_al=2.0,
                ctc_ph7=10.0,
                ctc_ph7_1=8.0,
                v_percent=80.0,
                summary={"aluminum_saturation_percent": 20.0, "base_saturation_percent": 80.0},
                analysis_date="2026-09-26T14:00:00+00:00",
                laboratory="Lab Teste S.A.",
                analysis_method="EMBRAPA",
                actor="lab@test.local",
            )

    def test_cross_property_sample_isolation_within_same_tenant(self) -> None:
        tenant_a = self.tenant("Soil Cross Property Tenant")
        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda Cross A",
            self.polygon(-47.3, -24.32, -47.28, -24.3),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        prop_b = self.application.create_property(
            tenant_a.id,
            "Fazenda Cross B",
            self.polygon(-47.4, -24.42, -47.38, -24.4),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        field_a = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão Cross A1",
            geometry_geojson=self.polygon(-47.295, -24.315, -47.285, -24.305),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        field_b = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_b.id,
            name="Talhão Cross B1",
            geometry_geojson=self.polygon(-47.395, -24.415, -47.385, -24.405),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-PROP-A",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-47.29, -24.31]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.application.register_soil_sample_point(
            tenant_a.id,
            prop_b.id,
            sample_code="SOLO-PROP-B",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo B",
            location_geojson={"type": "Point", "coordinates": [-47.39, -24.41]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_b.id,
            actor="agronomist@test.local",
        )
        samples_prop_a = self.application.soil.list_sample_points(tenant_a.id, prop_a.id)
        samples_prop_b = self.application.soil.list_sample_points(tenant_a.id, prop_b.id)
        self.assertEqual(len(samples_prop_a), 1)
        self.assertEqual(samples_prop_a[0].sample_code, "SOLO-PROP-A")
        self.assertEqual(len(samples_prop_b), 1)
        self.assertEqual(samples_prop_b[0].sample_code, "SOLO-PROP-B")

    def test_error_handling_invalid_geojson(self) -> None:
        tenant_a = self.tenant("Soil Invalid GeoJSON Tenant")
        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda Invalid GeoJSON",
            self.polygon(-47.5, -24.52, -47.48, -24.5),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        with self.assertRaises(SoilValidationError):
            self.application.register_soil_sample_point(
                tenant_a.id,
                prop_a.id,
                sample_code="SOLO-INVALID",
                depth_top_cm=0.0,
                depth_bottom_cm=20.0,
                collection_date="2026-09-21T09:00:00+00:00",
                collector_name="Agrônomo A",
                location_geojson={"type": "Point", "coordinates": "not_a_list"},
                classification=DataClassification.MANUAL_CONFIRMED,
                source_reference="GPS_PRO",
                actor="agronomist@test.local",
            )
        with self.assertRaises(SoilValidationError):
            self.application.register_soil_sample_point(
                tenant_a.id,
                prop_a.id,
                sample_code="SOLO-INVALID-TYPE",
                depth_top_cm=0.0,
                depth_bottom_cm=20.0,
                collection_date="2026-09-21T09:00:00+00:00",
                collector_name="Agrônomo A",
                location_geojson={"type": "InvalidType", "coordinates": [-47.49, -24.51]},
                classification=DataClassification.MANUAL_CONFIRMED,
                source_reference="GPS_PRO",
                actor="agronomist@test.local",
            )
        with self.assertRaises(SoilValidationError):
            self.application.register_soil_sample_point(
                tenant_a.id,
                prop_a.id,
                sample_code="SOLO-EMPTY",
                depth_top_cm=0.0,
                depth_bottom_cm=20.0,
                collection_date="2026-09-21T09:00:00+00:00",
                collector_name="Agrônomo A",
                location_geojson={},
                classification=DataClassification.MANUAL_CONFIRMED,
                source_reference="GPS_PRO",
                actor="agronomist@test.local",
            )

    def test_boundary_precision_edge_cases(self) -> None:
        tenant_a = self.tenant("Soil Boundary Edge Tenant")
        prop_a = self.application.create_property(
            tenant_a.id,
            "Fazenda Boundary Edge",
            self.polygon(-47.6, -24.62, -47.58, -24.6),
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )
        field_a = self.application.fields.create_field(
            tenant_a.id,
            property_id=prop_a.id,
            name="Talhão Edge A1",
            geometry_geojson=self.polygon(-47.595, -24.615, -47.585, -24.605),
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )
        sample_on_north_boundary = self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-NORTH-EDGE",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-47.59, -24.605]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.assertEqual(sample_on_north_boundary.sample_code, "SOLO-NORTH-EDGE")
        sample_on_east_boundary = self.application.register_soil_sample_point(
            tenant_a.id,
            prop_a.id,
            sample_code="SOLO-EAST-EDGE",
            depth_top_cm=0.0,
            depth_bottom_cm=20.0,
            collection_date="2026-09-21T09:00:00+00:00",
            collector_name="Agrônomo A",
            location_geojson={"type": "Point", "coordinates": [-47.585, -24.61]},
            classification=DataClassification.MANUAL_CONFIRMED,
            source_reference="GPS_PRO",
            field_id=field_a.id,
            actor="agronomist@test.local",
        )
        self.assertEqual(sample_on_east_boundary.sample_code, "SOLO-EAST-EDGE")


if __name__ == "__main__":
    unittest.main()
