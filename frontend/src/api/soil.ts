export interface SoilSamplePoint {
  id: string;
  tenant_id: string;
  property_id: string;
  field_id: string | null;
  sample_code: string;
  depth_top_cm: number;
  depth_bottom_cm: number;
  collection_date: string;
  collector_name: string;
  location_geojson: { type: "Point"; coordinates: [number, number] };
  location_crs: string;
  classification: string;
  source_reference: string;
  status: string;
  created_at: string;
  evidence_id?: string | null;
}

/** Laboratory values: null means the report did not bring that value (never zero). */
export interface SoilLabAnalysis {
  id: string;
  sample_point_id: string;
  lab_name: string;
  report_number: string;
  report_date: string;
  ph_h2o: number | null;
  ph_cacl2: number | null;
  organic_matter_g_dm3: number | null;
  phosphorus_mg_dm3: number | null;
  potassium_cmolc_dm3: number | null;
  calcium_cmolc_dm3: number | null;
  magnesium_cmolc_dm3: number | null;
  aluminum_cmolc_dm3: number | null;
  potential_acidity_h_al: number | null;
  cation_exchange_capacity_cec: number | null;
  base_saturation_percent: number | null;
  clay_percent: number | null;
  silt_percent: number | null;
  sand_percent: number | null;
  created_at: string;
}

export interface SoilSampleCreate {
  sample_code: string;
  depth_top_cm: number;
  depth_bottom_cm: number;
  collection_date: string;
  collector_name: string;
  location_geojson: { type: "Point"; coordinates: [number, number] };
  location_crs: "EPSG:4326";
  source_reference: string;
  field_id: string | null;
}

export type SoilLabValueKey =
  | "ph_h2o"
  | "ph_cacl2"
  | "organic_matter_g_dm3"
  | "phosphorus_mg_dm3"
  | "potassium_cmolc_dm3"
  | "calcium_cmolc_dm3"
  | "magnesium_cmolc_dm3"
  | "aluminum_cmolc_dm3"
  | "potential_acidity_h_al"
  | "cation_exchange_capacity_cec"
  | "base_saturation_percent"
  | "clay_percent"
  | "silt_percent"
  | "sand_percent";

export type SoilLabCreate = { lab_name: string; report_number: string; report_date: string } & Partial<Record<SoilLabValueKey, number | null>>;

export class SoilApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class SoilApi {
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
      throw new SoilApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  async samples(tenantId: string, propertyId: string): Promise<SoilSamplePoint[]> {
    const body = await this.send<{ items: SoilSamplePoint[] }>(
      `${this.tenant(tenantId)}/properties/${encodeURIComponent(propertyId)}/soil-samples`,
    );
    return body.items;
  }

  createSample(tenantId: string, propertyId: string, payload: SoilSampleCreate): Promise<SoilSamplePoint> {
    return this.send(`${this.tenant(tenantId)}/properties/${encodeURIComponent(propertyId)}/soil-samples`, {
      method: "POST",
      body: JSON.stringify({ ...payload, classification: "MANUAL_CONFIRMED" }),
    });
  }

  async analyses(tenantId: string, sampleId: string): Promise<SoilLabAnalysis[]> {
    const body = await this.send<{ items: SoilLabAnalysis[] }>(
      `${this.tenant(tenantId)}/soil-samples/${encodeURIComponent(sampleId)}/lab-analyses`,
    );
    return body.items;
  }

  createAnalysis(tenantId: string, sampleId: string, payload: SoilLabCreate): Promise<SoilLabAnalysis> {
    return this.send(`${this.tenant(tenantId)}/soil-samples/${encodeURIComponent(sampleId)}/lab-analyses`, {
      method: "POST",
      body: JSON.stringify({ ...payload, classification: "MANUAL_CONFIRMED" }),
    });
  }
}
