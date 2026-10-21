export type HarvestUnit = "BOXES" | "KG" | "BUNCHES";
export type DiscardReason = "STAIN" | "MECHANICAL_DAMAGE" | "CALIBER" | "OTHER";

export interface HarvestMeasure {
  total: number | null;
  records_with_value: number;
  records_without_value: number;
}

export interface HarvestBlock {
  record_count: number;
  discard_record_count: number;
  bunches_harvested: HarvestMeasure;
  boxes_packed: HarvestMeasure;
  weight_kg: HarvestMeasure;
  discards_by_unit: Partial<Record<HarvestUnit, { total: number; by_reason: Partial<Record<DiscardReason, number>> }>>;
}

export interface HarvestFieldSummary extends HarvestBlock {
  field_id: string;
  field_name: string;
  no_harvest_records: boolean;
}

export interface HarvestSummary {
  property_id: string;
  date_from: string | null;
  date_to: string | null;
  classification: string;
  fields: HarvestFieldSummary[];
  property_totals: HarvestBlock;
  limitations: string[];
}

export interface HarvestRecordCreate {
  field_id: string;
  harvest_date: string;
  bunches_harvested: number | null;
  boxes_packed: number | null;
  weight_kg: number | null;
  cut_criterion: string | null;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export interface HarvestDiscardCreate {
  field_id: string;
  discard_date: string;
  reason: DiscardReason;
  quantity: number;
  unit: HarvestUnit;
  recorded_by: string;
  source_reference: string;
  notes: string | null;
}

export class HarvestApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class HarvestApi {
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
      throw new HarvestApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  summary(tenantId: string, propertyId: string): Promise<HarvestSummary> {
    return this.send(this.url(tenantId, propertyId, "harvest-summary"));
  }

  createRecord(tenantId: string, propertyId: string, payload: HarvestRecordCreate): Promise<unknown> {
    return this.send(this.url(tenantId, propertyId, "harvest-records"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  createDiscard(tenantId: string, propertyId: string, payload: HarvestDiscardCreate): Promise<unknown> {
    return this.send(this.url(tenantId, propertyId, "harvest-discards"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}
