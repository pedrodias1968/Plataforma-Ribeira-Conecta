import type { CostSummary } from "./costs";
import type { SalesSummary } from "./sales";

export interface AccountantReport {
  property_id: string;
  date_from: string;
  date_to: string;
  as_of: string;
  classification: string;
  sales: SalesSummary;
  costs: CostSummary;
  limitations: string[];
}

export class AccountantApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class AccountantApi {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  async report(tenantId: string, propertyId: string, dateFrom: string, dateTo: string): Promise<AccountantReport> {
    const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
    const url = `${this.baseUrl}/v1/tenants/${encodeURIComponent(tenantId)}/properties/${encodeURIComponent(propertyId)}/accountant-report?${query.toString()}`;
    const response = await fetch(url, { headers: { Authorization: `Bearer ${this.token}` } });
    if (!response.ok) {
      throw new AccountantApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<AccountantReport>;
  }
}
