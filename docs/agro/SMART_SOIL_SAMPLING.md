# Smart Soil Sampling and Management Zones

`SMART_SOIL_SAMPLING` uses available terrain, soil baseline, Sentinel/Landsat
variability, moisture/waterlogging context, vegetation history, hydrology and
prior confirmed samples to propose cost-effective sampling zones. It does not
create a soil measurement.

`AGRICULTURAL_MANAGEMENT_ZONES` are versioned derived geometry with derivation
method, inputs, generated time and limitations. They are neither property nor
cadastral boundaries. A suggested sample location is
`RECOMMENDED_ACTION`/`DERIVED_LOCATION` until a technician confirms collection.

Workflow:

`suggest zone -> technician confirms/adjusts -> collection -> sample ID ->`
`geolocation/depth/time -> laboratory -> import -> validation -> Soil`
`Intelligence update -> suitability recalculation`

Traceability links the derived suggestion, confirmation, sample, lab/provider
raw evidence, normalized result, validation, recomputation and resulting
decision/action/outcome. Sampling density and sensor deployment are selected
by information value and risk; whole-farm point-sensor coverage is not assumed.

Future `MOBILE_SOIL_EC_SURVEY` may support zone delineation and sampling
optimization. EC is an indirect spatial variability indicator, never a direct
fertilizer requirement.

## Implementation status

This section describes only what is currently implemented in
`src/ribeira_platform/sampling.py` and covered by `tests/test_sampling.py`
(94 `def test_` methods). It documents existing code; it is not a plan and
promises nothing.

### What exists

Pure, Evidence-First domain logic with no database, network, API, raster or
migration code.

- `SamplingValidationError` — exception raised for all sampling validation failures.
- `ManagementZone` — frozen dataclass: versioned derived management-zone geometry with derivation method, method version, inputs, generated time, limitations and `DERIVED` classification.
- `SuggestedSamplePoint` — frozen dataclass: proposed sample location (`DERIVED_LOCATION`) derived from a management zone, not a measurement.
- `ConfirmedSampleLocation` — frozen dataclass: technician-confirmed (`MANUAL_CONFIRMED`) planning location linked back to the original suggestion; not a collected sample.
- `validate_management_zone(geometry, derivation_method, inputs)` — validates zone geometry and derivation metadata; rejects invalid/empty/wrong-type geometry and empty method/inputs.
- `suggest_grid_sample_points(field_id, field_geometry, crs, spacing_m, generated_at=None, *, max_points=10000)` — suggests points on a deterministic regular grid in a projected metre-based CRS; fallback representative point when no grid centre falls inside.
- `suggest_zone_sample_points(zones, generated_at=None)` — suggests exactly one point per already-delineated zone via `representative_point()`; sampling density is explicitly not decided here.
- `reproject_sample_points(points, source_crs, target_crs="EPSG:4326")` — pure coordinate transformation preserving all other fields and input order.
- `confirm_sample_location(suggestion, field_geometry, confirmed_by, adjusted_geometry=None, adjustment_note=None, confirmed_at=None)` — confirms or adjusts a suggested location inside the field polygon; produces no measurement.
- `zones_to_feature_collection(zones)` — serializes management zones as a GeoJSON FeatureCollection.
- `sample_points_to_feature_collection(points)` — serializes suggested sample points as a GeoJSON FeatureCollection.
- `confirmed_locations_to_feature_collection(locations)` — serializes confirmed sample locations as a GeoJSON FeatureCollection.

### What does not exist yet

- Delineation of management zones from terrain, satellite or historical data (zones must currently be supplied already delineated).
- A density rule or number-of-points-per-zone rule (the module deliberately decides no sampling density).
- Persistence, database migration or RLS for zones, points or confirmed locations.
- API routes exposing the sampling domain.
- A Farm360 screen or workflow for sampling.
- A link between the confirmation step and `SoilSamplePoint` / laboratory report (`laudo`) records.
