from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import patch

from ribeira_platform.hydrology import (
    AnaHidroWebAdapter,
    HydroFetchStatus,
    HydroObservationInput,
    HydroStationInput,
    HydroVariable,
    SaispPublicAdapter,
    SPAguaSIBHAdapter,
    observation_deduplication_key,
    observation_quality_issues,
    parse_copel_capivari_notice,
    parse_noaa_cpc_enso,
    rate_of_rise,
    river_stage_deltas,
    station_quality_issues,
)


UTC = timezone.utc


class HydrologyCoreTests(unittest.TestCase):
    def observation(
        self, variable: HydroVariable, observed_at: datetime, value: float, unit: str
    ) -> HydroObservationInput:
        return HydroObservationInput(
            "station-1", "TEST", variable, observed_at, value, unit
        )

    def test_station_identity_and_coordinate_quality(self) -> None:
        valid = HydroStationInput("ANA", "123", "Station", "TELEMETRIC", -24.0, -48.0)
        invalid = HydroStationInput("ANA", "123", "Station", "TELEMETRIC", 99.0, -48.0)
        self.assertEqual(station_quality_issues(valid), frozenset())
        self.assertIn("INVALID_COORDINATE", station_quality_issues(invalid))

    def test_observation_deduplication_and_quality_markers(self) -> None:
        now = datetime(2026, 9, 21, tzinfo=UTC)
        item = self.observation(HydroVariable.RAINFALL, now, -1.0, "mm")
        self.assertEqual(observation_deduplication_key(item)[0], "station-1")
        issues = observation_quality_issues(
            item, now=now, stale_after=timedelta(hours=1), conflicting_provider=True
        )
        self.assertEqual(issues, frozenset({"NEGATIVE_RAINFALL", "PROVIDER_CONFLICT"}))
        unsupported = self.observation(HydroVariable.DISCHARGE, now, 2.0, "mm")
        self.assertIn(
            "UNSUPPORTED_UNIT", observation_quality_issues(unsupported, now=now)
        )
        future = self.observation(
            HydroVariable.RAINFALL, now + timedelta(hours=1), 5.0, "mm"
        )
        self.assertIn(
            "FUTURE_TIMESTAMP", observation_quality_issues(future, now=now)
        )

    def test_river_stage_deltas_computes_change_correctly(self) -> None:
        now = datetime(2026, 9, 21, tzinfo=UTC)
        end = datetime(2026, 9, 21, 1, tzinfo=UTC)
        samples = [
            HydroObservationInput(
                "station-1", "TEST", HydroVariable.RIVER_STAGE, now, 2.0, "m"
            ),
            HydroObservationInput(
                "station-1",
                "TEST",
                HydroVariable.RIVER_STAGE,
                now + timedelta(minutes=30),
                2.2,
                "m",
            ),
            HydroObservationInput(
                "station-1",
                "TEST",
                HydroVariable.RIVER_STAGE,
                now + timedelta(hours=1),
                2.4,
                "m",
            ),
        ]
        delta = river_stage_deltas(samples, end_at=end)
        self.assertAlmostEqual(delta["1h"] or 0, 0.4)
        self.assertIsNone(delta["3h"])
        self.assertAlmostEqual(
            rate_of_rise(delta["1h"], timedelta(hours=1)) or 0, 0.4 / 3600
        )
        self.assertIsNone(rate_of_rise(None, timedelta(hours=1)))

    def test_auth_and_unavailable_adapters_do_not_fabricate_data(self) -> None:
        self.assertEqual(
            AnaHidroWebAdapter().list_stations().status, HydroFetchStatus.AUTH_REQUIRED
        )
        self.assertEqual(
            SaispPublicAdapter().fetch_observations().status,
            HydroFetchStatus.SOURCE_UNAVAILABLE,
        )

    def test_copel_parser_only_keeps_explicit_gate_fact(self) -> None:
        notice = """{"datePublished":"2026-09-11T10:00:00-03:00"}
        A usina de Capivari aumentou a abertura das comportas."""
        event = parse_copel_capivari_notice(
            notice, "https://www.copel.com/site/noticias/example/"
        )
        self.assertEqual(event.event_type, "GATE_OPENING")
        self.assertIsNone(event.numeric_value)
        self.assertEqual(event.classification, "OFFICIAL_SOURCE")

    def test_noaa_parser_keeps_climate_as_context(self) -> None:
        text = "Issued on 10 September 2026. El Niño has a 90% chance during ASO 2026 and may be very strong."
        context = parse_noaa_cpc_enso(
            text, "https://www.cpc.ncep.noaa.gov/products/example"
        )
        self.assertEqual(context.enso_state, "EL_NINO")
        self.assertEqual(context.probability, 90.0)
        self.assertEqual(context.valid_window, "ASO 2026")

    def test_spagua_sibh_provider_structure(self) -> None:
        adapter = SPAguaSIBHAdapter()
        self.assertEqual(
            adapter.stations_endpoint,
            "https://apps.spaguas.sp.gov.br/sibh/api/v2/stations",
        )
        self.assertEqual(
            adapter.measurements_endpoint,
            "https://apps.spaguas.sp.gov.br/sibh/api/v2/measurements",
        )

    def test_spagua_sibh_health_check_reaches_endpoint(self) -> None:
        adapter = SPAguaSIBHAdapter()
        result = adapter.health_check()
        self.assertIn(
            result.status,
            (HydroFetchStatus.SUCCESS, HydroFetchStatus.SOURCE_UNAVAILABLE),
        )

    def test_spagua_sibh_list_stations_reaches_endpoint(self) -> None:
        adapter = SPAguaSIBHAdapter()
        result = adapter.list_stations()
        self.assertIn(
            result.status,
            (HydroFetchStatus.SUCCESS, HydroFetchStatus.SOURCE_UNAVAILABLE),
        )

    def test_spagua_sibh_fetch_observations_reaches_endpoint(self) -> None:
        adapter = SPAguaSIBHAdapter()
        now = datetime(2026, 9, 15, tzinfo=UTC)
        start = now - timedelta(hours=24)
        result = adapter.fetch_observations(
            start_date=start, end_date=now, group_type="hour"
        )
        self.assertIn(
            result.status,
            (HydroFetchStatus.SUCCESS, HydroFetchStatus.SOURCE_UNAVAILABLE),
        )

    def test_spagua_sibh_observations_preserve_river_stage_without_fabrication(
        self,
    ) -> None:
        adapter = SPAguaSIBHAdapter()
        now = datetime(2026, 9, 15, tzinfo=UTC)
        start = now - timedelta(hours=24)

        mock_response = json.dumps(
            [
                {
                    "timestamp": "2026-09-15T10:00:00+00:00",
                    "value": 2.45,
                    "metric": "level",
                    "station_id": "SIBH-123",
                },
                {
                    "timestamp": "2026-09-15T11:00:00+00:00",
                    "value": 2.48,
                    "metric": "level",
                    "station_id": "SIBH-123",
                },
            ]
        )

        with patch(
            "ribeira_platform.hydrology._fetch_text", return_value=mock_response
        ):
            result = adapter.fetch_observations(
                start_date=start,
                end_date=now,
                group_type="hour",
                variable=HydroVariable.RIVER_STAGE,
            )

        self.assertEqual(result.status, HydroFetchStatus.SUCCESS)
        self.assertEqual(len(result.items), 2)
        self.assertIsInstance(result.items[0], dict)
        self.assertEqual(result.items[0]["value"], 2.45)
        self.assertEqual(result.items[1]["value"], 2.48)

    def test_spagua_sibh_observations_preserve_discharge_without_fabrication(
        self,
    ) -> None:
        adapter = SPAguaSIBHAdapter()
        now = datetime(2026, 9, 15, tzinfo=UTC)
        start = now - timedelta(hours=24)

        mock_response = json.dumps(
            [
                {
                    "timestamp": "2026-09-15T10:00:00+00:00",
                    "value": 12.5,
                    "metric": "flow",
                    "station_id": "SIBH-456",
                },
                {
                    "timestamp": "2026-09-15T11:00:00+00:00",
                    "value": 15.2,
                    "metric": "flow",
                    "station_id": "SIBH-456",
                },
            ]
        )

        with patch(
            "ribeira_platform.hydrology._fetch_text", return_value=mock_response
        ):
            result = adapter.fetch_observations(
                start_date=start,
                end_date=now,
                group_type="hour",
                variable=HydroVariable.DISCHARGE,
            )

        self.assertEqual(result.status, HydroFetchStatus.SUCCESS)
        self.assertEqual(len(result.items), 2)
        self.assertIsInstance(result.items[0], dict)
        self.assertEqual(result.items[0]["value"], 12.5)
        self.assertEqual(result.items[1]["value"], 15.2)

    def test_spagua_sibh_empty_response_does_not_fabricate_observations(self) -> None:
        adapter = SPAguaSIBHAdapter()
        now = datetime(2026, 9, 15, tzinfo=UTC)
        start = now - timedelta(hours=24)

        mock_response = json.dumps([])

        with patch(
            "ribeira_platform.hydrology._fetch_text", return_value=mock_response
        ):
            result = adapter.fetch_observations(
                start_date=start,
                end_date=now,
                group_type="hour",
                variable=HydroVariable.RIVER_STAGE,
            )

        self.assertEqual(result.status, HydroFetchStatus.SUCCESS)
        self.assertEqual(len(result.items), 0)

    def test_spagua_sibh_null_value_response_preserves_null(self) -> None:
        adapter = SPAguaSIBHAdapter()
        now = datetime(2026, 9, 15, tzinfo=UTC)
        start = now - timedelta(hours=24)

        mock_response = json.dumps(
            [
                {
                    "timestamp": "2026-09-15T10:00:00+00:00",
                    "value": None,
                    "metric": "level",
                    "station_id": "SIBH-789",
                }
            ]
        )

        with patch(
            "ribeira_platform.hydrology._fetch_text", return_value=mock_response
        ):
            result = adapter.fetch_observations(
                start_date=start,
                end_date=now,
                group_type="hour",
                variable=HydroVariable.RIVER_STAGE,
            )

        self.assertEqual(result.status, HydroFetchStatus.SUCCESS)
        self.assertEqual(len(result.items), 1)
        self.assertIsNone(result.items[0]["value"])


if __name__ == "__main__":
    unittest.main()
