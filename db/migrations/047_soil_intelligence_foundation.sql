-- Soil Intelligence Foundation: georeferenced soil sample points and laboratory analyses.
-- Enforces spatial containment within property/field, multi-tenant RLS, and evidence validation.

CREATE TABLE soil_sample_point (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  property_id uuid NOT NULL,
  field_id uuid,
  sample_code text NOT NULL CHECK (btrim(sample_code) <> ''),
  depth_top_cm numeric NOT NULL CHECK (depth_top_cm >= 0),
  depth_bottom_cm numeric NOT NULL CHECK (depth_bottom_cm > depth_top_cm),
  collection_date timestamptz NOT NULL,
  collector_name text NOT NULL CHECK (btrim(collector_name) <> ''),
  location geometry(Point, 4326) NOT NULL,
  location_crs text NOT NULL CHECK (location_crs IN ('EPSG:4326', 'CRS:84')),
  classification text NOT NULL,
  source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
  status text NOT NULL CHECK (btrim(status) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, property_id) REFERENCES property(tenant_id, id),
  FOREIGN KEY (tenant_id, field_id) REFERENCES field_context(tenant_id, id)
);

CREATE INDEX soil_sample_point_property_idx
  ON soil_sample_point(tenant_id, property_id, created_at DESC);
CREATE INDEX soil_sample_point_location_gix
  ON soil_sample_point USING gist(location);

CREATE OR REPLACE FUNCTION soil_sample_point_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF ST_SRID(NEW.location) <> 4326
     OR GeometryType(NEW.location) <> 'POINT'
     OR NOT ST_IsValid(NEW.location) THEN
    RAISE EXCEPTION 'soil sample location must be a valid EPSG:4326 Point'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM property
     WHERE tenant_id = NEW.tenant_id
       AND id = NEW.property_id
       AND geometry IS NOT NULL
       AND (ST_Covers(geometry, NEW.location) OR ST_Touches(geometry, NEW.location))
  ) THEN
    RAISE EXCEPTION 'soil sample location must be contained by property boundary'
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.field_id IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM field_context_boundary_version v
       JOIN field_context f ON f.tenant_id = v.tenant_id AND f.id = v.field_context_id
       WHERE v.tenant_id = NEW.tenant_id
         AND v.field_context_id = NEW.field_id
         AND v.property_id = NEW.property_id
         AND (ST_Covers(v.geometry, NEW.location) OR ST_Touches(v.geometry, NEW.location))
    ) THEN
      RAISE EXCEPTION 'soil sample location must be contained by field boundary'
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION soil_sample_point_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION soil_sample_point_guard() TO ribeira_app;
CREATE TRIGGER soil_sample_point_guard
  BEFORE INSERT OR UPDATE ON soil_sample_point
  FOR EACH ROW EXECUTE FUNCTION soil_sample_point_guard();

CREATE TABLE soil_lab_analysis (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  sample_point_id uuid NOT NULL,
  lab_name text NOT NULL CHECK (btrim(lab_name) <> ''),
  report_number text NOT NULL CHECK (btrim(report_number) <> ''),
  report_date date NOT NULL,
  ph_h2o numeric,
  ph_cacl2 numeric,
  organic_matter_g_dm3 numeric,
  phosphorus_mg_dm3 numeric,
  potassium_cmolc_dm3 numeric,
  calcium_cmolc_dm3 numeric,
  magnesium_cmolc_dm3 numeric,
  aluminum_cmolc_dm3 numeric,
  potential_acidity_h_al numeric,
  cation_exchange_capacity_cec numeric,
  base_saturation_percent numeric,
  clay_percent numeric,
  silt_percent numeric,
  sand_percent numeric,
  raw_attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  classification text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, sample_point_id) REFERENCES soil_sample_point(tenant_id, id)
);

CREATE INDEX soil_lab_analysis_sample_idx
  ON soil_lab_analysis(tenant_id, sample_point_id, created_at DESC);

ALTER TABLE soil_sample_point ENABLE ROW LEVEL SECURITY;
ALTER TABLE soil_sample_point FORCE ROW LEVEL SECURITY;
ALTER TABLE soil_lab_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE soil_lab_analysis FORCE ROW LEVEL SECURITY;

CREATE POLICY soil_sample_point_tenant_isolation ON soil_sample_point
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

CREATE POLICY soil_lab_analysis_tenant_isolation ON soil_lab_analysis
  USING (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true')
  WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
    OR current_setting('app.platform_admin', true) = 'true');

GRANT SELECT, INSERT, UPDATE, DELETE ON soil_sample_point, soil_lab_analysis TO ribeira_app;

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
  ELSIF NEW.evidence_type = 'SOIL_SAMPLE' THEN
    SELECT tenant_id INTO referenced_tenant FROM soil_sample_point WHERE id = NEW.reference_id;
  ELSIF NEW.evidence_type = 'SOIL_LAB_ANALYSIS' THEN
    SELECT tenant_id INTO referenced_tenant FROM soil_lab_analysis WHERE id = NEW.reference_id;
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
