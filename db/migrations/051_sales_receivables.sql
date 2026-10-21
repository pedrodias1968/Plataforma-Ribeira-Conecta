-- Sales and receivables (vendas e recebimentos): append-only sale records and
-- payment records, tenant-scoped and corrected only by supersession. An amount,
-- quantity, price or due date that was not informed is NULL (UNKNOWN); the total
-- is never computed from quantity times price. A payment points to the sale
-- version it was registered against; the application follows the correction
-- chain to find the current sale.

CREATE TABLE sale_record (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  sale_date date NOT NULL,
  buyer_name text NOT NULL CHECK (btrim(buyer_name) <> ''),
  quantity numeric CHECK (quantity >= 0),
  quantity_unit text CHECK (quantity_unit IN ('BOXES', 'KG', 'BUNCHES')),
  unit_price_brl numeric CHECK (unit_price_brl >= 0),
  price_unit text CHECK (price_unit IN ('BOXES', 'KG', 'BUNCHES')),
  total_amount_brl numeric CHECK (total_amount_brl >= 0),
  expected_payment_date date,
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  CHECK ((quantity IS NULL) = (quantity_unit IS NULL)),
  CHECK ((unit_price_brl IS NULL) = (price_unit IS NULL)),
  CHECK (quantity IS NOT NULL OR total_amount_brl IS NOT NULL),
  CHECK (expected_payment_date IS NULL OR expected_payment_date >= sale_date),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES sale_record(tenant_id, id)
);
CREATE INDEX sale_record_property_idx
  ON sale_record(tenant_id, property_id, sale_date DESC);
CREATE UNIQUE INDEX sale_record_single_correction_idx
  ON sale_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE payment_record (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  sale_id uuid NOT NULL,
  payment_date date NOT NULL,
  amount_brl numeric NOT NULL CHECK (amount_brl > 0),
  method text CHECK (method IS NULL OR btrim(method) <> ''),
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, sale_id) REFERENCES sale_record(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES payment_record(tenant_id, id)
);
CREATE INDEX payment_record_property_idx
  ON payment_record(tenant_id, property_id, payment_date DESC);
CREATE INDEX payment_record_sale_idx
  ON payment_record(tenant_id, sale_id);
CREATE UNIQUE INDEX payment_record_single_correction_idx
  ON payment_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

-- A sale correction must keep the property; a payment must belong to the same
-- property as its sale, and a payment correction must keep property and sale.
CREATE OR REPLACE FUNCTION sale_record_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM sale_record
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
    ) THEN
      RAISE EXCEPTION 'sale correction must keep the property of the corrected sale'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION sale_record_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sale_record_guard() TO ribeira_app;
CREATE TRIGGER sale_record_guard
  BEFORE INSERT ON sale_record
  FOR EACH ROW EXECUTE FUNCTION sale_record_guard();

CREATE OR REPLACE FUNCTION payment_record_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM sale_record
     WHERE tenant_id = NEW.tenant_id
       AND id = NEW.sale_id
       AND property_id = NEW.property_id
  ) THEN
    RAISE EXCEPTION 'payment must belong to the same property as its sale'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM payment_record
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
         AND sale_id = NEW.sale_id
    ) THEN
      RAISE EXCEPTION 'payment correction must keep the property and sale of the corrected payment'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION payment_record_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION payment_record_guard() TO ribeira_app;
CREATE TRIGGER payment_record_guard
  BEFORE INSERT ON payment_record
  FOR EACH ROW EXECUTE FUNCTION payment_record_guard();

ALTER TABLE sale_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_record FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_record FORCE ROW LEVEL SECURITY;

CREATE POLICY sale_record_tenant_isolation ON sale_record
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

CREATE POLICY payment_record_tenant_isolation ON payment_record
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

-- Append-only for the application role: no UPDATE and no DELETE.
GRANT SELECT, INSERT ON sale_record, payment_record TO ribeira_app;

-- Adds SALE_RECORD and PAYMENT_RECORD to the evidence reference check, keeping
-- every branch of migration 050.
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
