export type CostCategory = "LABOR" | "PESTICIDE" | "FUEL" | "MAINTENANCE" | "PACKAGING" | "TRANSPORT" | "OTHER";

export interface ManualCostBlock {
  entry_count: number;
  total: number | null;
  by_category: Partial<Record<CostCategory, number>>;
}

export interface CostFieldSummary {
  field_id: string;
  field_name: string;
  manual_cost: ManualCostBlock;
  fertilization_cost: {
    record_count: number;
    total: number | null;
    records_with_value: number;
    records_without_value: number;
  };
  allocated_cost_total: number | null;
  cost_is_partial: boolean;
  harvest: {
    record_count: number;
    weight_kg_total: number | null;
    records_with_weight: number;
    records_without_weight: number;
  };
  cost_per_kg: number | null;
  cost_per_kg_unavailable_reason: "NO_COST_DATA" | "NO_WEIGHT_DATA" | "SOME_HARVEST_WITHOUT_WEIGHT" | null;
}

export interface CostSummary {
  property_id: string;
  date_from: string | null;
  date_to: string | null;
  classification: string;
  fields: CostFieldSummary[];
  unallocated_cost: ManualCostBlock;
  limitations: string[];
}

export interface CostEntryCreate {
  field_id: string | null;
  entry_date: string;
  category: CostCategory;
  description: string;
  amount_brl: number;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export class CostApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class CostApi {
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
      throw new CostApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  summary(tenantId: string, propertyId: string): Promise<CostSummary> {
    return this.send(this.url(tenantId, propertyId, "cost-summary"));
  }

  createEntry(tenantId: string, propertyId: string, payload: CostEntryCreate): Promise<unknown> {
    return this.send(this.url(tenantId, propertyId, "cost-entries"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
