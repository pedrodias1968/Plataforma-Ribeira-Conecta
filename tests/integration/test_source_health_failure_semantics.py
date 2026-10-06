from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import unittest
from uuid import uuid4

from ribeira_platform.postgres import PostgresStore


UTC = timezone.utc
DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(
    DATABASE_URL,
    "RIBEIRA_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)
class SourceHealthFailureSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = PostgresStore(DATABASE_URL)  # type: ignore[arg-type]
        self.provider = f"TEST_SOURCE_HEALTH_{uuid4().hex}"
        self.station_id = str(uuid4())
        self.observation_id = str(uuid4())

    def tearDown(self) -> None:
        try:
            with self.store.transaction():
                self.store.connection.execute(
                    "DELETE FROM hydrological_observation WHERE provider=%s",
                    (self.provider,),
                )
                self.store.connection.execute(
                    "DELETE FROM hydrological_station WHERE provider=%s",
                    (self.provider,),
                )
                self.store.connection.execute(
                    "DELETE FROM source_health WHERE provider=%s",
                    (self.provider,),
                )
        finally:
            self.store.close()

    def test_degraded_health_preserves_prior_success_and_observations(self) -> None:
        success_at = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
        observation_at = success_at - timedelta(minutes=5)
        failure_at = success_at + timedelta(minutes=10)

        with self.store.transaction():
            self.store.connection.execute(
                """
                INSERT INTO hydrological_station(
                    id,
                    provider,
                    provider_station_id,
                    name,
                    station_type,
                    latitude,
                    longitude,
                    active_status,
                    metadata
                )
                VALUES (%s,%s,%s,%s,'SYNOP',-24.0,-48.0,'ACTIVE','{}'::jsonb)
                """,
                (
                    self.station_id,
                    self.provider,
                    f"station-{uuid4().hex}",
                    "Source health regression fixture",
                ),
            )

            self.store.connection.execute(
                """
                INSERT INTO hydrological_observation(
                    id,
                    station_id,
                    provider,
                    variable,
                    observed_at,
                    received_at,
                    value,
                    unit,
                    quality_flag,
                    classification,
                    raw_reference,
                    source_fetched_at
                )
                VALUES (
                    %s,%s,%s,'RAINFALL',%s,%s,12.5,'mm',
                    'VALID','OFFICIAL_SOURCE',%s,%s
                )
                """,
                (
                    self.observation_id,
                    self.station_id,
                    self.provider,
                    observation_at,
                    observation_at,
                    "https://example.invalid/source-health-regression",
                    success_at,
                ),
            )

            self.store.upsert_source_health(
                self.provider,
                "AVAILABLE",
                last_attempt=success_at.isoformat(),
                last_success=success_at.isoformat(),
                last_observation=observation_at.isoformat(),
            )

            self.store.upsert_source_health(
                self.provider,
                "DEGRADED",
                last_attempt=failure_at.isoformat(),
                latency_seconds=5.0,
                failure_code="ConnectionError",
                failure_detail_sanitized="bounded provider request failed",
            )

            health = self.store.connection.execute(
                """
                SELECT status,last_success,last_observation,failure_code
                  FROM source_health
                 WHERE provider=%s
                """,
                (self.provider,),
            ).fetchone()

            observation_count = self.store.connection.execute(
                """
                SELECT count(*) AS count
                  FROM hydrological_observation
                 WHERE id=%s AND provider=%s
                """,
                (self.observation_id, self.provider),
            ).fetchone()

        self.assertIsNotNone(health)
        assert health is not None
        self.assertEqual(health["status"], "DEGRADED")
        self.assertEqual(health["last_success"], success_at)
        self.assertEqual(health["last_observation"], observation_at)
        self.assertEqual(health["failure_code"], "ConnectionError")

        self.assertIsNotNone(observation_count)
        assert observation_count is not None
        self.assertEqual(
            int(observation_count["count"]),
            1,
            "a degraded source-health update must not remove prior observations",
        )


if __name__ == "__main__":
    unittest.main()
