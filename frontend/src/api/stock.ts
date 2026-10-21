export type StockUnit = "KG" | "L" | "UNIT";
export type MovementType = "IN" | "OUT";

export interface StockItem {
  item_name: string;
  unit: StockUnit;
  entries: number;
  exits: number;
  balance: number;
  negative_balance: boolean;
  movement_count: number;
  last_movement_date: string;
}

export interface StockSummary {
  property_id: string;
  as_of: string;
  items: StockItem[];
  items_with_negative_balance: number;
  limitations: string[];
}

export interface StockMovementCreate {
  movement_date: string;
  movement_type: MovementType;
  item_name: string;
  unit: StockUnit;
  quantity: number;
  counterparty: string | null;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export class StockApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class StockApi {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  private url(tenantId: string, propertyId: string, resource: string): string {
    return `${this.baseUrl}/v1/tenants/${encodeURIComponent(tenantId)}/properties/${encodeURIComponent(propertyId)}/${resource}`;
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
      throw new StockApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  summary(tenantId: string, propertyId: string): Promise<StockSummary> {
    return this.send(this.url(tenantId, propertyId, "stock-summary"));
  }

  createMovement(tenantId: string, propertyId: string, payload: StockMovementCreate): Promise<unknown> {
    return this.send(this.url(tenantId, propertyId, "stock-movements"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
