-- Input stock (estoque de insumos): append-only stock movements (entrada/saida),
-- tenant-scoped and corrected only by supersession. Quantity is always
-- positive; the direction is the movement type. Balances are computed per item
-- and unit by the application and are never clamped at zero: a negative balance
-- means more outputs than registered inputs (unknown opening stock).

CREATE TABLE stock_movement (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  movement_date date NOT NULL,
  movement_type text NOT NULL CHECK (movement_type IN ('IN', 'OUT')),
  item_name text NOT NULL CHECK (btrim(item_name) <> ''),
  unit text NOT NULL CHECK (unit IN ('KG', 'L', 'UNIT')),
  quantity numeric NOT NULL CHECK (quantity > 0),
  counterparty text CHECK (counterparty IS NULL OR btrim(counterparty) <> ''),
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES stock_movement(tenant_id, id)
);
CREATE INDEX stock_movement_property_idx
  ON stock_movement(tenant_id, property_id, movement_date DESC);
CREATE UNIQUE INDEX stock_movement_single_correction_idx
  ON stock_movement(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

-- A correction must keep the property of the corrected movement.
CREATE OR REPLACE FUNCTION stock_movement_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM stock_movement
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
    ) THEN
      RAISE EXCEPTION 'stock correction must keep the property of the corrected movement'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION stock_movement_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION stock_movement_guard() TO ribeira_app;
CREATE TRIGGER stock_movement_guard
  BEFORE INSERT ON stock_movement
  FOR EACH ROW EXECUTE FUNCTION stock_movement_guard();

ALTER TABLE stock_movement ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_movement FORCE ROW LEVEL SECURITY;

CREATE POLICY stock_movement_tenant_isolation ON stock_movement
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

-- Append-only for the application role: no UPDATE and no DELETE.
GRANT SELECT, INSERT ON stock_movement TO ribeira_app;

-- Adds STOCK_MOVEMENT to the evidence reference check, keeping every branch of
-- migration 051.
CREATE OR REPLACE FUNCTION enforce_evidence_reference_tenant()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  referenced_tenant uuid;
BEGIN
  IF NEW.evidence_type = 'OBSERVATION' THEN
    SELECT tenant_id INTO referenced_tenant FROM observation WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'PROPERTY' THEN
    SELECT tenant_id INTO referenced_tenant FROM property WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'DECISION' THEN
    SELECT tenant_id INTO referenced_tenant FROM decision WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'SATELLITE_SCENE' THEN
    SELECT tenant_id INTO referenced_tenant FROM satellite_scene WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'DERIVED_PRODUCT' THEN
    SELECT tenant_id INTO referenced_tenant FROM derived_product WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'ASSET_REGISTRATION' THEN
    SELECT tenant_id INTO referenced_tenant FROM asset WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'FIELD_REGISTRATION' THEN
    SELECT tenant_id INTO referenced_tenant FROM field_context WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'FIELD_BOUNDARY_CORRECTION' THEN
    SELECT tenant_id INTO referenced_tenant FROM field_context_boundary_version WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'SOIL_SAMPLE' THEN
    SELECT tenant_id INTO referenced_tenant FROM soil_sample_point WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'SOIL_LAB_ANALYSIS' THEN
    SELECT tenant_id INTO referenced_tenant FROM soil_lab_analysis WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'HARVEST_RECORD' THEN
    SELECT tenant_id INTO referenced_tenant FROM harvest_record WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'HARVEST_DISCARD' THEN
    SELECT tenant_id INTO referenced_tenant FROM harvest_discard WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'FERTILIZATION_RECORD' THEN
    SELECT tenant_id INTO referenced_tenant FROM fertilization_record WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'COST_ENTRY' THEN
    SELECT tenant_id INTO referenced_tenant FROM cost_entry WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'SALE_RECORD' THEN
    SELECT tenant_id INTO referenced_tenant FROM sale_record WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'PAYMENT_RECORD' THEN
    SELECT tenant_id INTO referenced_tenant FROM payment_record WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'STOCK_MOVEMENT' THEN
    SELECT tenant_id INTO referenced_tenant FROM stock_movement WHERE id = NEW.reference_id;
  ELSE
    RAISE EXCEPTION 'unsupported evidence reference type: %', NEW.evidence_type
      USING ERRCODE = 'check_violation';
  END IF;
  IF referenced_tenant IS NULL OR referenced_tenant <> NEW.tenant_id THEN
    RAISE EXCEPTION 'evidence reference crosses tenant boundary'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  RETURN NEW;
END;
$$;
