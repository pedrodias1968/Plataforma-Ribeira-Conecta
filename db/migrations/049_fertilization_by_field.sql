-- Fertilization and inputs by field (adubação e insumos por talhão): append-only
-- application records, tenant-scoped, field-bound and corrected only by
-- supersession. Quantity, area and cost that were not recorded are NULL
-- (UNKNOWN), never zero.

CREATE TABLE fertilization_record (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  field_id uuid NOT NULL,
  application_date date NOT NULL,
  product_name text NOT NULL CHECK (btrim(product_name) <> ''),
  product_type text NOT NULL CHECK (product_type IN (
    'MINERAL_FERTILIZER', 'ORGANIC_FERTILIZER', 'LIMING', 'FOLIAR', 'OTHER')),
  quantity numeric CHECK (quantity >= 0),
  quantity_unit text CHECK (quantity_unit IN ('KG', 'G', 'L', 'ML')),
  area_applied_ha numeric CHECK (area_applied_ha > 0),
  application_method text CHECK (application_method IS NULL OR btrim(application_method) <> ''),
  cost_brl numeric CHECK (cost_brl >= 0),
  applied_by text NOT NULL CHECK (btrim(applied_by) <> ''),
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  CHECK ((quantity IS NULL) = (quantity_unit IS NULL)),
  CHECK (product_type <> 'OTHER' OR (notes IS NOT NULL AND btrim(notes) <> '')),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, field_id) REFERENCES field_context(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES fertilization_record(tenant_id, id)
);
CREATE INDEX fertilization_record_property_idx
  ON fertilization_record(tenant_id, property_id, application_date DESC);
CREATE INDEX fertilization_record_field_idx
  ON fertilization_record(tenant_id, field_id, application_date DESC);
CREATE UNIQUE INDEX fertilization_record_single_correction_idx
  ON fertilization_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

-- The field must belong to the stated property, and a correction must keep the
-- same property and field as the record it supersedes.
CREATE OR REPLACE FUNCTION fertilization_record_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM field_context
     WHERE tenant_id = NEW.tenant_id
       AND id = NEW.field_id
       AND property_id = NEW.property_id
  ) THEN
    RAISE EXCEPTION 'fertilization field must belong to the stated property'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM fertilization_record
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
         AND field_id = NEW.field_id
    ) THEN
      RAISE EXCEPTION 'fertilization correction must keep the property and field of the corrected record'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION fertilization_record_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION fertilization_record_guard() TO ribeira_app;
CREATE TRIGGER fertilization_record_guard
  BEFORE INSERT ON fertilization_record
  FOR EACH ROW EXECUTE FUNCTION fertilization_record_guard();

ALTER TABLE fertilization_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE fertilization_record FORCE ROW LEVEL SECURITY;

CREATE POLICY fertilization_record_tenant_isolation ON fertilization_record
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

-- Append-only for the application role: no UPDATE and no DELETE.
GRANT SELECT, INSERT ON fertilization_record TO ribeira_app;

-- Adds FERTILIZATION_RECORD to the evidence reference check, keeping every
-- branch of migration 048.
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
