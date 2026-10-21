export type ProductType = "MINERAL_FERTILIZER" | "ORGANIC_FERTILIZER" | "LIMING" | "FOLIAR" | "OTHER";
export type QuantityUnit = "KG" | "G" | "L" | "ML";

export interface FertilizationBlock {
  record_count: number;
  last_application_date: string | null;
  products: string[];
  quantity_by_unit: Partial<Record<QuantityUnit, number>>;
  records_without_quantity: number;
  cost_brl: {
    total: number | null;
    records_with_value: number;
    records_without_value: number;
  };
}

export interface FertilizationFieldSummary extends FertilizationBlock {
  field_id: string;
  field_name: string;
  no_fertilization_records: boolean;
}

export interface FertilizationSummary {
  property_id: string;
  date_from: string | null;
  date_to: string | null;
  classification: string;
  fields: FertilizationFieldSummary[];
  property_totals: FertilizationBlock;
  limitations: string[];
}

export interface FertilizationRecordCreate {
  field_id: string;
  application_date: string;
  product_name: string;
  product_type: ProductType;
  quantity: number | null;
  quantity_unit: QuantityUnit | null;
  area_applied_ha: number | null;
  application_method: string | null;
  cost_brl: number | null;
  applied_by: string;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export class FertilizationApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class FertilizationApi {
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
      throw new FertilizationApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  summary(tenantId: string, propertyId: string): Promise<FertilizationSummary> {
    return this.send(this.url(tenantId, propertyId, "fertilization-summary"));
  }

  createRecord(tenantId: string, propertyId: string, payload: FertilizationRecordCreate): Promise<unknown> {
    return this.send(this.url(tenantId, propertyId, "fertilization-records"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
