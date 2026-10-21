export type SaleUnit = "BOXES" | "KG" | "BUNCHES";
export type SaleStatus = "AMOUNT_UNKNOWN" | "OPEN" | "PARTIAL" | "PAID" | "OVERPAID";

export interface SaleRow {
  sale_id: string;
  sale_date: string;
  buyer_name: string;
  quantity: number | null;
  quantity_unit: SaleUnit | null;
  unit_price_brl: number | null;
  price_unit: SaleUnit | null;
  total_amount_brl: number | null;
  expected_payment_date: string | null;
  received_brl: number;
  balance_brl: number | null;
  status: SaleStatus;
  overdue: boolean;
}

export interface SalesSummary {
  property_id: string;
  as_of: string;
  sale_count: number;
  sales: SaleRow[];
  total_known_brl: number | null;
  sales_without_total: number;
  received_on_known_total_brl: number;
  received_on_unknown_total_brl: number;
  outstanding_brl: number | null;
  overdue_brl: number | null;
  limitations: string[];
}

export interface SaleCreate {
  sale_date: string;
  buyer_name: string;
  quantity: number | null;
  quantity_unit: SaleUnit | null;
  unit_price_brl: number | null;
  price_unit: SaleUnit | null;
  total_amount_brl: number | null;
  expected_payment_date: string | null;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export interface PaymentCreate {
  payment_date: string;
  amount_brl: number;
  method: string | null;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export class SalesApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class SalesApi {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  private tenant(tenantId: string): string {
    return `${this.baseUrl}/v1/tenants/${encodeURIComponent(tenantId)}`;
  }

  private async send<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.token}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
      },
    });
    if (!response.ok) {
      throw new SalesApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  summary(tenantId: string, propertyId: string): Promise<SalesSummary> {
    return this.send(`${this.tenant(tenantId)}/properties/${encodeURIComponent(propertyId)}/sales-summary`);
  }

  createSale(tenantId: string, propertyId: string, payload: SaleCreate): Promise<unknown> {
    return this.send(`${this.tenant(tenantId)}/properties/${encodeURIComponent(propertyId)}/sale-records`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  createPayment(tenantId: string, saleId: string, payload: PaymentCreate): Promise<unknown> {
    return this.send(`${this.tenant(tenantId)}/sale-records/${encodeURIComponent(saleId)}/payments`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
