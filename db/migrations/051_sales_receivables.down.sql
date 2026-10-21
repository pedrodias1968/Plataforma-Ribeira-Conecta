DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM evidence WHERE evidence_type IN ('SALE_RECORD', 'PAYMENT_RECORD')
  ) THEN
    RAISE EXCEPTION 'cannot roll back sales tables while sales evidence exists';
  END IF;
END
$$;

DROP TRIGGER IF EXISTS payment_record_guard ON payment_record;
DROP TRIGGER IF EXISTS sale_record_guard ON sale_record;
DROP FUNCTION IF EXISTS payment_record_guard();
DROP FUNCTION IF EXISTS sale_record_guard();
DROP TABLE IF EXISTS payment_record;
DROP TABLE IF EXISTS sale_record;

-- Restore the function exactly as migration 050 left it.
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
