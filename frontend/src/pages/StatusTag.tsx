export type Status = "ready" | "building" | "planned";

const STATUS_LABEL: Record<Status, string> = {
  ready: "Funcionando",
  building: "Em desenvolvimento",
  planned: "Em planejamento",
};

export function StatusTag({ status }: { status: Status }) {
  return <span className={`tag tag-${status}`}>{STATUS_LABEL[status]}</span>;
}
