-- Costs by field (custos por talhão): append-only manual cost entries,
-- tenant-scoped, corrected only by supersession. A cost may be allocated to one
-- field or left property-wide (field_id NULL); property-wide costs are never
-- spread over fields. Fertilizer costs live in fertilization_record and are not
-- accepted here, so a cost is never counted twice.

CREATE TABLE cost_entry (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  field_id uuid,
  entry_date date NOT NULL,
  category text NOT NULL CHECK (category IN (
    'LABOR', 'PESTICIDE', 'FUEL', 'MAINTENANCE', 'PACKAGING', 'TRANSPORT', 'OTHER')),
  description text NOT NULL CHECK (btrim(description) <> ''),
  amount_brl numeric NOT NULL CHECK (amount_brl >= 0),
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  CHECK (category <> 'OTHER' OR (notes IS NOT NULL AND btrim(notes) <> '')),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, field_id) REFERENCES field_context(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES cost_entry(tenant_id, id)
);
CREATE INDEX cost_entry_property_idx
  ON cost_entry(tenant_id, property_id, entry_date DESC);
CREATE INDEX cost_entry_field_idx
  ON cost_entry(tenant_id, field_id, entry_date DESC);
CREATE UNIQUE INDEX cost_entry_single_correction_idx
  ON cost_entry(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

-- When a field is stated it must belong to the stated property, and a
-- correction must keep the same property and field (or lack of field).
CREATE OR REPLACE FUNCTION cost_entry_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.field_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM field_context
     WHERE tenant_id = NEW.tenant_id
       AND id = NEW.field_id
       AND property_id = NEW.property_id
  ) THEN
    RAISE EXCEPTION 'cost field must belong to the stated property'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM cost_entry
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
         AND field_id IS NOT DISTINCT FROM NEW.field_id
    ) THEN
      RAISE EXCEPTION 'cost correction must keep the property and field of the corrected entry'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION cost_entry_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION cost_entry_guard() TO ribeira_app;
CREATE TRIGGER cost_entry_guard
  BEFORE INSERT ON cost_entry
  FOR EACH ROW EXECUTE FUNCTION cost_entry_guard();

ALTER TABLE cost_entry ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_entry FORCE ROW LEVEL SECURITY;

CREATE POLICY cost_entry_tenant_isolation ON cost_entry
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

-- Append-only for the application role: no UPDATE and no DELETE.
GRANT SELECT, INSERT ON cost_entry TO ribeira_app;

-- Adds COST_ENTRY to the evidence reference check, keeping every branch of 049.
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
