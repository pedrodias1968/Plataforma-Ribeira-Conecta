-- Harvest by field (colheita por talhão): append-only harvest records and
-- discard records, tenant-scoped, field-bound and corrected only by supersession.
-- A missing measure is NULL (UNKNOWN), never zero.

CREATE TABLE harvest_record (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  field_id uuid NOT NULL,
  harvest_date date NOT NULL,
  bunches_harvested integer CHECK (bunches_harvested >= 0),
  boxes_packed integer CHECK (boxes_packed >= 0),
  weight_kg numeric CHECK (weight_kg >= 0),
  cut_criterion text CHECK (cut_criterion IS NULL OR btrim(cut_criterion) <> ''),
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  notes text,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  CHECK (bunches_harvested IS NOT NULL OR boxes_packed IS NOT NULL OR weight_kg IS NOT NULL),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, field_id) REFERENCES field_context(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES harvest_record(tenant_id, id)
);
CREATE INDEX harvest_record_property_idx
  ON harvest_record(tenant_id, property_id, harvest_date DESC);
CREATE INDEX harvest_record_field_idx
  ON harvest_record(tenant_id, field_id, harvest_date DESC);
CREATE UNIQUE INDEX harvest_record_single_correction_idx
  ON harvest_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE harvest_discard (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  field_id uuid NOT NULL,
  discard_date date NOT NULL,
  reason text NOT NULL CHECK (reason IN ('STAIN', 'MECHANICAL_DAMAGE', 'CALIBER', 'OTHER')),
  quantity numeric NOT NULL CHECK (quantity >= 0),
  unit text NOT NULL CHECK (unit IN ('BOXES', 'KG', 'BUNCHES')),
  notes text,
  recorded_by text NOT NULL CHECK (btrim(recorded_by) <> ''),
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  classification text NOT NULL,
  supersedes_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  CHECK (reason <> 'OTHER' OR (notes IS NOT NULL AND btrim(notes) <> '')),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, field_id) REFERENCES field_context(tenant_id, id),
  FOREIGN KEY (tenant_id, supersedes_id) REFERENCES harvest_discard(tenant_id, id)
);
CREATE INDEX harvest_discard_property_idx
  ON harvest_discard(tenant_id, property_id, discard_date DESC);
CREATE INDEX harvest_discard_field_idx
  ON harvest_discard(tenant_id, field_id, discard_date DESC);
CREATE UNIQUE INDEX harvest_discard_single_correction_idx
  ON harvest_discard(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

-- The field must belong to the stated property, and a correction must keep the
-- same property and field as the record it supersedes.
CREATE OR REPLACE FUNCTION harvest_record_guard()
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
    RAISE EXCEPTION 'harvest field must belong to the stated property'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM harvest_record
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
         AND field_id = NEW.field_id
    ) THEN
      RAISE EXCEPTION 'harvest correction must keep the property and field of the corrected record'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION harvest_record_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION harvest_record_guard() TO ribeira_app;
CREATE TRIGGER harvest_record_guard
  BEFORE INSERT ON harvest_record
  FOR EACH ROW EXECUTE FUNCTION harvest_record_guard();

CREATE OR REPLACE FUNCTION harvest_discard_guard()
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
    RAISE EXCEPTION 'discard field must belong to the stated property'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.supersedes_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM harvest_discard
       WHERE tenant_id = NEW.tenant_id
         AND id = NEW.supersedes_id
         AND property_id = NEW.property_id
         AND field_id = NEW.field_id
    ) THEN
      RAISE EXCEPTION 'discard correction must keep the property and field of the corrected record'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION harvest_discard_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION harvest_discard_guard() TO ribeira_app;
CREATE TRIGGER harvest_discard_guard
  BEFORE INSERT ON harvest_discard
  FOR EACH ROW EXECUTE FUNCTION harvest_discard_guard();

ALTER TABLE harvest_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvest_record FORCE ROW LEVEL SECURITY;
ALTER TABLE harvest_discard ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvest_discard FORCE ROW LEVEL SECURITY;

CREATE POLICY harvest_record_tenant_isolation ON harvest_record
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

CREATE POLICY harvest_discard_tenant_isolation ON harvest_discard
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

-- Append-only for the application role: no UPDATE and no DELETE. Corrections
-- are new rows that supersede the previous one.
GRANT SELECT, INSERT ON harvest_record, harvest_discard TO ribeira_app;

-- Adds HARVEST_RECORD and HARVEST_DISCARD. It also keeps the
-- FIELD_BOUNDARY_CORRECTION branch added by migration 045, which migration 047
-- omitted when it redefined this function.
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
