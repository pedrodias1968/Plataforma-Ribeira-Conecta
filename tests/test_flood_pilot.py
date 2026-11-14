"""Unit tests for ribeira_platform.flood_pilot.

Covers the pure/helper logic of the bounded Registro Sentinel-1 flood pilot
without a database, network or external provider. Database-backed queries are
driven through in-memory fakes. The infrastructure-heavy entry points that
require a live PostgreSQL connection or the Sentinel Hub Process API are
skipped with an explicit reason rather than faked into fabricated behaviour.
"""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest import mock

from ribeira_platform import flood_pilot

_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [
            [-124.75, 49.95],
            [-124.65, 49.95],
            [-124.65, 50.05],
            [-124.75, 50.05],
            [-124.75, 49.95],
        ]
    ],
}
_GEOMETRY_JSON = json.dumps(_GEOMETRY)
_CHECKSUM = "a" * 64


def _row(**overrides):
    row = {
        "municipality_id": "municipality-1",
        "event_id": "event-1",
        "geometry": _GEOMETRY_JSON,
        "source_reference": "official-registro-2025",
        "source_sha256": _CHECKSUM,
        "geometry_valid": True,
        "geometry_crs": 4674,
    }
    row.update(overrides)
    return row


class _FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, results):
        self._results = list(results)
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, statement, params=()):
        self.executed.append((statement, params))
        if not self._results:
            raise AssertionError("unexpected SQL execution in unit test")
        return _FakeResult(self._results.pop(0))


class _FakeStore:
    def __init__(self, results):
        self.connection = _FakeConnection(results)


class StoreFactoryTests(unittest.TestCase):
    def test_store_requires_database_url(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as caught:
                flood_pilot._store()

        self.assertIn("RIBEIRA_DATABASE_URL", str(caught.exception))

    def test_store_constructs_postgres_store_from_configured_dsn(self) -> None:
        sentinel = object()
        with mock.patch.dict(
            os.environ, {"RIBEIRA_DATABASE_URL": "postgresql://private/db"}
        ):
            with mock.patch.object(
                flood_pilot, "PostgresStore", return_value=sentinel
            ) as factory:
                result = flood_pilot._store()

        self.assertIs(result, sentinel)
        factory.assert_called_once_with("postgresql://private/db")


class RegistroAoiTests(unittest.TestCase):
    def test_valid_row_returns_geometry_and_provenance(self) -> None:
        store = _FakeStore([[_row()]])

        row, geometry, source = flood_pilot._registro_aoi(store)

        self.assertIs(row["municipality_id"], "municipality-1")
        self.assertEqual(geometry, _GEOMETRY)
        self.assertEqual(source["geometry_checksum"], _CHECKSUM)
        self.assertEqual(source["source_reference"], "official-registro-2025")
        self.assertEqual(len(store.connection.executed), 1)

    def test_missing_row_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            flood_pilot._registro_aoi(_FakeStore([[]]))

    def test_invalid_geometry_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            flood_pilot._registro_aoi(_FakeStore([[_row(geometry_valid=False)]]))

    def test_wrong_crs_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            flood_pilot._registro_aoi(_FakeStore([[_row(geometry_crs=4326)]]))

    def test_unavailable_checksum_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            flood_pilot._registro_aoi(_FakeStore([[_row(source_sha256="short")]]))


class SceneSelectionTests(unittest.TestCase):
    @staticmethod
    def _scene(acquired, **metadata):
        base = {
            "instrument_mode": "IW",
            "orbit_state": "DESCENDING",
            "relative_orbit": "53",
            "polarizations": ["VV", "VH"],
        }
        base.update(metadata)
        return {
            "id": f"scene-{acquired.date().isoformat()}",
            "provider_record_id": "provider-record",
            "acquired_at": acquired,
            "geometry": _GEOMETRY_JSON,
            "metadata": base,
        }

    def test_selects_exact_pre_and_event_pair(self) -> None:
        pre = self._scene(datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc))
        event = self._scene(datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc))

        result = flood_pilot._scenes(_FakeStore([[pre, event]]))

        self.assertEqual(set(result), {"PRE", "EVENT"})
        self.assertEqual(result["PRE"]["geometry"], _GEOMETRY)
        self.assertEqual(result["EVENT"]["id"], "scene-2026-09-13")

    def test_ignores_scenes_with_non_matching_metadata(self) -> None:
        pre = self._scene(
            datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc),
            instrument_mode="EW",
        )
        event = self._scene(
            datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc),
            orbit_state="ASCENDING",
        )

        with self.assertRaises(RuntimeError):
            flood_pilot._scenes(_FakeStore([[pre, event]]))

    def test_requires_both_roles_present(self) -> None:
        pre = self._scene(datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc))

        with self.assertRaises(RuntimeError):
            flood_pilot._scenes(_FakeStore([[pre]]))

    def test_ignores_acquired_dates_outside_known_roles(self) -> None:
        other = self._scene(datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

        with self.assertRaises(RuntimeError):
            flood_pilot._scenes(_FakeStore([[other]]))


class MainCommandTests(unittest.TestCase):
    def test_main_dispatches_prepare_and_prints_result(self) -> None:
        output = io.StringIO()
        with mock.patch("sys.argv", ["flood_pilot", "prepare"]):
            with mock.patch.object(
                flood_pilot, "prepare", return_value={"tiles": 2, "crs": "EPSG:31983"}
            ) as prepare:
                with redirect_stdout(output):
                    flood_pilot.main()

        prepare.assert_called_once_with()
        self.assertIn("TILES=2", output.getvalue())
        self.assertIn("CRS=EPSG:31983", output.getvalue())

    def test_main_dispatches_single_tile(self) -> None:
        with mock.patch("sys.argv", ["flood_pilot", "single-tile"]):
            with mock.patch.object(
                flood_pilot, "single_tile", return_value={"status": "VERIFIED"}
            ) as single_tile:
                with mock.patch.object(flood_pilot, "prepare") as prepare:
                    with redirect_stdout(io.StringIO()):
                        flood_pilot.main()

        single_tile.assert_called_once_with()
        prepare.assert_not_called()

    def test_main_rejects_unknown_command(self) -> None:
        with mock.patch("sys.argv", ["flood_pilot", "unknown"]):
            with self.assertRaises(SystemExit):
                flood_pilot.main()


class InfrastructurePathTests(unittest.TestCase):
    @unittest.skip(
        "prepare() requires a live PostgreSQL connection with RLS and the "
        "official Registro geometry; not exercised without a database."
    )
    def test_prepare_persists_aoi_and_tiles(self) -> None:
        flood_pilot.prepare()

    @unittest.skip(
        "single_tile() requires PostgreSQL, the Sentinel Hub Process API and "
        "private CDSE credentials; external provider calls are out of scope."
    )
    def test_single_tile_processes_scene_pair(self) -> None:
        flood_pilot.single_tile()

    @unittest.skip(
        "_to_cog() performs real rasterio/COG conversion and object-storage "
        "writes; this belongs to an integration test, not a unit test."
    )
    def test_to_cog_writes_cog_asset(self) -> None:
        flood_pilot._to_cog(
            storage=mock.Mock(),
            payload=b"",
            band=1,
            role="PRE",
            name="VV_RTC_LINEAR_POWER",
            tile=mock.Mock(),
        )


if __name__ == "__main__":
    unittest.main()
