"""Unit and API tests for input stock: movements, balances, corrections, RBAC."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from ribeira_platform.stock import StockConflict, StockValidationError
from tests.test_harvest import HarvestTestBase

AS_OF = "2026-10-20"


class StockTestBase(HarvestTestBase):
    def move(self, movement_type="IN", quantity=100, **overrides):
        values = {
            "movement_date": "2026-10-01",
            "movement_type": movement_type,
            "item_name": "Ureia",
            "unit": "KG",
            "quantity": quantity,
        }
        values.update(overrides)
        return self.app.register_stock_movement(
            self.tenant.id,
            self.property.id,
            recorded_by="Encarregado",
            source_reference="caderno do estoque",
            actor="manager@test.local",
            **values,
        )

    def summary(self, **kwargs):
        return self.app.stock_summary(
            self.tenant.id, self.property.id, as_of=kwargs.pop("as_of", AS_OF)
        )


class StockUnitTest(StockTestBase):
    def test_balance_is_entries_minus_exits_per_item_and_unit(self) -> None:
        self.move("IN", 100)
        self.move("OUT", 30, movement_date="2026-10-05")
        self.move("IN", 10, item_name="  ureia ", unit="L")
        row = {
            (r["item_name"].strip().casefold(), r["unit"]): r
            for r in self.summary()["items"]
        }
        self.assertEqual(row[("ureia", "KG")]["balance"], 70.0)
        self.assertEqual(row[("ureia", "L")]["balance"], 10.0)
        self.assertEqual(len(row), 2)

    def test_item_name_groups_case_insensitively(self) -> None:
        self.move("IN", 50)
        self.move("OUT", 20, item_name="UREIA")
        items = self.summary()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["balance"], 30.0)

    def test_negative_balance_is_reported_not_clamped(self) -> None:
        self.move("OUT", 15)
        summary = self.summary()
        self.assertEqual(summary["items"][0]["balance"], -15.0)
        self.assertTrue(summary["items"][0]["negative_balance"])
        self.assertEqual(summary["items_with_negative_balance"], 1)

    def test_as_of_ignores_later_movements(self) -> None:
        self.move("IN", 100)
        self.move("OUT", 40, movement_date="2026-10-15")
        early = self.app.stock_summary(
            self.tenant.id, self.property.id, as_of="2026-10-10"
        )
        self.assertEqual(early["items"][0]["balance"], 100.0)

    def test_no_movements_means_no_items_not_zero_rows(self) -> None:
        self.assertEqual(self.summary()["items"], [])

    def test_correction_replaces_the_movement_in_the_balance(self) -> None:
        wrong = self.move("IN", 1000)
        fixed = self.app.correct_stock_movement(
            self.tenant.id,
            wrong.id,
            correction_reason="digitei 1000",
            movement_date="2026-10-01",
            movement_type="IN",
            item_name="Ureia",
            unit="KG",
            quantity=100,
            recorded_by="Encarregado",
            source_reference="nota",
        )
        self.assertEqual(fixed.supersedes_id, wrong.id)
        self.assertEqual(self.summary()["items"][0]["balance"], 100.0)
        with self.assertRaises(StockConflict):
            self.app.correct_stock_movement(
                self.tenant.id,
                wrong.id,
                correction_reason="outra",
                movement_date="2026-10-01",
                movement_type="IN",
                item_name="Ureia",
                unit="KG",
                quantity=1,
                recorded_by="x",
                source_reference="x",
            )

    def test_validation(self) -> None:
        for overrides in (
            {"quantity": 0},
            {"quantity": -1},
            {"quantity": True},
            {"quantity": float("nan")},
            {"unit": "TON"},
            {"movement_type": "MOVE"},
            {"item_name": "  "},
            {"movement_date": "2999-01-01"},
            {"classification": DataClassification.INFERRED},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.move(**overrides)
        with self.assertRaises(StockValidationError):
            self.move(unit="BAG")

    def test_evidence_is_created_with_limitations(self) -> None:
        item = self.move("IN", 5)
        evidence = self.store.evidence_for_reference(self.tenant.id, item.id)
        self.assertEqual(evidence.evidence_type, "STOCK_MOVEMENT")

    def test_other_tenant_cannot_see_or_use_property(self) -> None:
        other = self.app.create_tenant("Outro")
        with self.assertRaises(LookupError):
            self.app.stock_summary(other.id, self.property.id, as_of=AS_OF)


class StockApiTest(StockTestBase):
    def client(self, role: str) -> tuple[TestClient, dict[str, str]]:
        token = f"{role.lower()}-token"
        client = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    token,
                    AuthContext(
                        f"{role.lower()}-user",
                        self.tenant.id,
                        roles=frozenset({role}),
                    ),
                ),
            )
        )
        return client, {"Authorization": f"Bearer {token}"}

    def base(self) -> str:
        return f"/v1/tenants/{self.tenant.id}"

    def payload(self, **overrides):
        values = {
            "movement_date": "2026-10-01",
            "movement_type": "IN",
            "item_name": "Ureia",
            "unit": "KG",
            "quantity": 100,
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
        }
        values.update(overrides)
        return values

    def test_operator_can_record_and_read_but_analyst_only_reads(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/stock-movements"
        operator, op_headers = self.client("OPERATOR")
        created = operator.post(url, json=self.payload(), headers=op_headers)
        self.assertEqual(created.status_code, 201)
        self.assertIsNotNone(created.json()["evidence_id"])
        self.assertEqual(operator.get(url, headers=op_headers).status_code, 200)
        analyst, an_headers = self.client("ANALYST")
        self.assertEqual(analyst.get(url, headers=an_headers).status_code, 200)
        self.assertEqual(
            analyst.post(url, json=self.payload(), headers=an_headers).status_code, 403
        )
        viewer, v_headers = self.client("VIEWER")
        self.assertEqual(viewer.get(url, headers=v_headers).status_code, 403)

    def test_summary_correction_and_conflict_over_http(self) -> None:
        client, headers = self.client("MANAGER")
        url = f"{self.base()}/properties/{self.property.id}/stock-movements"
        first = client.post(url, json=self.payload(), headers=headers).json()
        correction = self.payload(quantity=80, correction_reason="contagem")
        path = f"{self.base()}/stock-movements/{first['id']}/corrections"
        self.assertEqual(
            client.post(path, json=correction, headers=headers).status_code, 201
        )
        again = client.post(path, json=correction, headers=headers)
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["error"]["code"], "STOCK_CONFLICT")
        summary = client.get(
            f"{self.base()}/properties/{self.property.id}/stock-summary",
            params={"as_of": AS_OF},
            headers=headers,
        ).json()
        self.assertEqual(summary["items"][0]["balance"], 80.0)

    def test_rejects_non_positive_quantity_and_unknown_fields(self) -> None:
        client, headers = self.client("MANAGER")
        url = f"{self.base()}/properties/{self.property.id}/stock-movements"
        self.assertEqual(
            client.post(
                url, json=self.payload(quantity=0), headers=headers
            ).status_code,
            422,
        )
        self.assertEqual(
            client.post(url, json=self.payload(extra=1), headers=headers).status_code,
            422,
        )
