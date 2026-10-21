export type RecordKind = "harvest" | "discard" | "fertilization" | "cost" | "sale" | "payment" | "stock";

/** Collection names used by the list and correction endpoints of each module. */
export const KIND_RESOURCES: Record<RecordKind, { list: string; correct: string }> = {
  harvest: { list: "harvest-records", correct: "harvest-records" },
  discard: { list: "harvest-discards", correct: "harvest-discards" },
  fertilization: { list: "fertilization-records", correct: "fertilization-records" },
  cost: { list: "cost-entries", correct: "cost-entries" },
  sale: { list: "sale-records", correct: "sale-records" },
  payment: { list: "payment-records", correct: "payment-records" },
  stock: { list: "stock-movements", correct: "stock-movements" },
};

export type RecordItem = Record<string, unknown> & { id: string };

export class CorrectionsApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export class CorrectionsApi {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  private async send<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.token}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
      },
    });
    if (!response.ok) {
      throw new CorrectionsApiError(response.status, `Request failed (${response.status})`);
    }
    return response.json() as Promise<T>;
  }

  async list(tenantId: string, propertyId: string, kind: RecordKind): Promise<RecordItem[]> {
    const url = `${this.baseUrl}/v1/tenants/${encodeURIComponent(tenantId)}/properties/${encodeURIComponent(propertyId)}/${KIND_RESOURCES[kind].list}`;
    const body = await this.send<{ items: RecordItem[] }>(url);
    return body.items;
  }

  correct(tenantId: string, kind: RecordKind, recordId: string, payload: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/v1/tenants/${encodeURIComponent(tenantId)}/${KIND_RESOURCES[kind].correct}/${encodeURIComponent(recordId)}/corrections`;
    return this.send(url, { method: "POST", body: JSON.stringify(payload) });
  }
}
