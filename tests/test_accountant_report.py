from __future__ import annotations

import unittest

from ribeira_platform.sales import SalesValidationError
from tests.test_sales import SalesTestBase


class AccountantReportTests(SalesTestBase):
    def test_combines_sales_and_costs_without_inventing_a_result(self) -> None:
        sale = self.sale()
        self.pay(sale.id, 1000)
        self.sale(total_amount_brl=None, buyer_name="Costa")
        self.app.register_cost_entry(
            self.tenant.id,
            self.property.id,
            field_id=None,
            entry_date="2026-10-03",
            category="FUEL",
            description="Diesel",
            amount_brl=200,
            recorded_by="Gerente",
            source_reference="nota",
        )
        report = self.app.accountant_report(
            self.tenant.id,
            self.property.id,
            date_from="2026-10-01",
            date_to="2026-10-31",
            as_of="2026-10-20",
        )
        self.assertEqual(report["sales"]["outstanding_brl"], 2000.0)
        self.assertEqual(report["sales"]["sales_without_total"], 1)
        self.assertEqual(report["costs"]["unallocated_cost"]["total"], 200.0)
        self.assertNotIn("result", report)
        self.assertNotIn("margin", report)
        self.assertEqual(report["classification"], "CALCULATED")

    def test_requires_period(self) -> None:
        with self.assertRaises(SalesValidationError):
            self.app.accountant_report(
                self.tenant.id, self.property.id, date_from="", date_to="2026-10-31"
            )


if __name__ == "__main__":
    unittest.main()
