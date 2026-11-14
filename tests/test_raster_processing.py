"""Unit tests for ribeira_platform.raster_processing.

Covers the pure helpers (``algorithm_parameters``), the error value object
(``RasterProcessingError``), the COG structural validator (``validate_cog``)
and the main processing logic of ``NdviProcessor`` / ``TemporalDeltaProcessor``
against explicitly synthetic rasters written to a temporary directory.

No database, network or external provider is required.  Every input raster is
labelled ``synthetic_test_data``.  The raster I/O helpers (``_crop``,
``_read_aligned``, ``_write_cog``) are exercised through the public ``process``
methods rather than called directly; the pure geometry/reprojection paths are
left to their own integration coverage.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from ribeira_platform.geospatial import (
    GeospatialQuality,
    SatelliteAsset,
)
from ribeira_platform.object_storage import LocalObjectStorage
from ribeira_platform.raster_processing import (
    DeltaRasterProcessingOutput,
    NdviProcessor,
    RasterProcessingError,
    RasterProcessingOutput,
    TemporalDeltaProcessor,
    algorithm_parameters,
    validate_cog,
)
from ribeira_platform.sentinel2_quality import Sentinel2QualityPolicy

AOI = {
    "type": "Polygon",
    "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]],
}


def _write_cog(
    path: Path,
    values: np.ndarray,
    *,
    crs: str | None = "EPSG:4326",
    transform=None,
    nodata: float = float("nan"),
    compress: str = "deflate",
) -> None:
    """Persist ``values`` as a synthetic COG used to exercise validate_cog."""
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.asarray(values, dtype="float32")
    if array.ndim == 2:
        array = array[np.newaxis, :, :]
    transform = transform or from_origin(0, 1, 0.125, 0.125)
    with rasterio.open(
        path,
        "w",
        driver="COG",
        height=array.shape[1],
        width=array.shape[2],
        count=array.shape[0],
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
        compress=compress,
    ) as dataset:
        dataset.write(array)


def _asset(
    key: str,
    title: str,
    roles: list[str],
    href: str,
) -> SatelliteAsset:
    return SatelliteAsset(
        key,
        "synthetic_test_data",
        "scene",
        key,
        href,
        "image/tiff",
        roles,
        title,
        {},
    )


class AlgorithmParametersTests(unittest.TestCase):
    def test_returns_canonical_processing_policy(self) -> None:
        parameters = algorithm_parameters(AOI)
        self.assertEqual(parameters["nodata_policy"], "NO_DATA")
        self.assertEqual(parameters["resampling"], "nearest")

    def test_aoi_checksum_is_sha256_of_canonical_json(self) -> None:
        parameters = algorithm_parameters(AOI)
        expected = hashlib.sha256(
            json.dumps(AOI, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(parameters["aoi_checksum"], expected)
        self.assertEqual(len(parameters["aoi_checksum"]), 64)

    def test_key_order_does_not_change_checksum(self) -> None:
        reordered = {"coordinates": AOI["coordinates"], "type": AOI["type"]}
        self.assertEqual(
            algorithm_parameters(AOI)["aoi_checksum"],
            algorithm_parameters(reordered)["aoi_checksum"],
        )

    def test_distinct_aois_produce_distinct_checksums(self) -> None:
        other = {"type": "Point", "coordinates": [1, 2]}
        self.assertNotEqual(
            algorithm_parameters(AOI)["aoi_checksum"],
            algorithm_parameters(other)["aoi_checksum"],
        )

    def test_parameters_are_json_serializable(self) -> None:
        json.dumps(algorithm_parameters(AOI))


class RasterProcessingErrorTests(unittest.TestCase):
    def test_preserves_quality_and_message(self) -> None:
        error = RasterProcessingError(GeospatialQuality.PROCESSING_FAILED, "boom")
        self.assertEqual(error.quality, GeospatialQuality.PROCESSING_FAILED)
        self.assertEqual(str(error), "boom")

    def test_is_a_runtime_error(self) -> None:
        error = RasterProcessingError(GeospatialQuality.ASSET_UNAVAILABLE, "x")
        self.assertIsInstance(error, RuntimeError)


class ValidateCogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.transform = from_origin(0, 1, 0.125, 0.125)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _valid_path(self) -> Path:
        path = self.root / "valid.tif"
        _write_cog(path, np.full((8, 8), 0.5), transform=self.transform)
        return path

    def test_accepts_a_valid_single_band_deflate_cog(self) -> None:
        validate_cog(
            self._valid_path(),
            expected_crs=rasterio.crs.CRS.from_epsg(4326),
            expected_transform=self.transform,
            expected_shape=(8, 8),
            expected_value_range=(-1.0, 1.0),
        )

    def test_rejects_non_cog_geotiff(self) -> None:
        path = self.root / "plain.tif"
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=4,
            width=4,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            nodata=float("nan"),
        ) as dataset:
            dataset.write(np.zeros((1, 4, 4), dtype="float32"))
        with self.assertRaises(ValueError):
            validate_cog(path)

    def test_rejects_multiband_cog(self) -> None:
        path = self.root / "multiband.tif"
        _write_cog(path, np.zeros((2, 8, 8)), transform=self.transform)
        with self.assertRaises(ValueError):
            validate_cog(path)

    def test_rejects_missing_crs(self) -> None:
        path = self.root / "nocrs.tif"
        _write_cog(path, np.zeros((8, 8)), crs=None, transform=self.transform)
        with self.assertRaises(ValueError):
            validate_cog(path)

    def test_rejects_non_nan_nodata(self) -> None:
        path = self.root / "nodata.tif"
        _write_cog(path, np.zeros((8, 8)), transform=self.transform, nodata=-9999.0)
        with self.assertRaises(ValueError):
            validate_cog(path)

    def test_rejects_crs_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            validate_cog(
                self._valid_path(),
                expected_crs=rasterio.crs.CRS.from_epsg(3857),
            )

    def test_rejects_shape_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            validate_cog(self._valid_path(), expected_shape=(4, 4))

    def test_rejects_transform_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            validate_cog(
                self._valid_path(),
                expected_transform=from_origin(10, 20, 1, 1),
            )

    def test_rejects_values_outside_expected_range(self) -> None:
        path = self.root / "outofrange.tif"
        _write_cog(path, np.full((8, 8), 5.0), transform=self.transform)
        with self.assertRaises(ValueError):
            validate_cog(path, expected_value_range=(-1.0, 1.0))

    def test_range_check_is_skipped_when_none(self) -> None:
        path = self.root / "anyvalue.tif"
        _write_cog(path, np.full((8, 8), 99.0), transform=self.transform)
        validate_cog(path, expected_value_range=None)


class NdviProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.storage = LocalObjectStorage(self.root)
        self.processor = NdviProcessor(self.storage)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _assets(
        self,
        prefix: str,
        red_value: float,
        nir_value: float,
        scl: np.ndarray | None = None,
    ) -> list[SatelliteAsset]:
        transform = from_origin(0, 1, 0.25, 0.25)
        rasters = {
            "B04_10m": np.full((4, 4), red_value, dtype="float32"),
            "B08_10m": np.full((4, 4), nir_value, dtype="float32"),
        }
        if scl is not None:
            rasters["SCL_20m"] = scl.astype("uint8")
        titles = {
            "B04_10m": "Red (band 4) - 10m",
            "B08_10m": "NIR 1 (band 8) - 10m",
            "SCL_20m": "Scene classification map (SCL) - 20m",
        }
        assets: list[SatelliteAsset] = []
        for key, values in rasters.items():
            path = self.root / prefix / f"{key}.tif"
            path.parent.mkdir(parents=True, exist_ok=True)
            nodata = 255 if values.dtype == np.uint8 else -9999.0
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                height=4,
                width=4,
                count=1,
                dtype=str(values.dtype),
                crs="EPSG:4326",
                transform=transform,
                nodata=nodata,
            ) as dataset:
                dataset.write(values, 1)
            assets.append(
                _asset(
                    key,
                    titles[key],
                    ["reflectance"] if key != "SCL_20m" else ["data"],
                    f"local://{prefix}/{key}.tif",
                )
            )
        return assets

    def test_computes_ndvi_and_reports_full_coverage(self) -> None:
        output = self.processor.process(
            self._assets("scene", red_value=1.0, nir_value=3.0),
            AOI,
            "derived/ndvi.tif",
        )
        self.assertIsInstance(output, RasterProcessingOutput)
        self.assertEqual(output.statistics.valid_count, 16)
        self.assertEqual(output.statistics.nodata_count, 0)
        self.assertEqual(output.statistics.coverage_percentage, Decimal("100"))
        self.assertEqual(output.statistics.mean, Decimal("0.5"))
        self.assertEqual(output.statistics.minimum, Decimal("0.5"))
        self.assertEqual(output.statistics.maximum, Decimal("0.5"))
        self.assertEqual(output.quality, [])
        self.assertEqual(output.limitations, [])
        self.assertEqual(sorted(output.input_asset_keys), ["B04_10m", "B08_10m"])
        self.assertIsNone(output.quality_mask)

    def test_algorithm_identity_is_exposed(self) -> None:
        self.assertEqual(NdviProcessor.algorithm_id, "NDVI")
        self.assertEqual(NdviProcessor.algorithm_version, "1.0.0")
        self.assertEqual(NdviProcessor.formula, "(NIR - RED) / (NIR + RED)")

    def test_output_cog_is_valid_and_masks_nodata(self) -> None:
        output = self.processor.process(
            self._assets("scene", red_value=1.0, nir_value=3.0),
            AOI,
            "derived/ndvi.tif",
        )
        path = self.storage.read_local_path(output.output_reference)
        validate_cog(path, expected_value_range=(-1.0, 1.0))
        with rasterio.open(path) as dataset:
            values = dataset.read(1, masked=True)
            self.assertAlmostEqual(float(values.mean()), 0.5, places=6)

    def test_unresolvable_band_roles_raise_asset_unavailable(self) -> None:
        assets = [_asset("x", "Blue (band 2) - 10m", ["reflectance"], "local://x.tif")]
        with self.assertRaises(RasterProcessingError) as context:
            self.processor.process(assets, AOI, "derived/ndvi.tif")
        self.assertEqual(context.exception.quality, GeospatialQuality.ASSET_UNAVAILABLE)

    def test_missing_local_asset_raises_asset_unavailable(self) -> None:
        assets = [
            _asset(
                "B04_10m",
                "Red (band 4) - 10m",
                ["reflectance"],
                "local://missing/red.tif",
            ),
            _asset(
                "B08_10m",
                "NIR 1 (band 8) - 10m",
                ["reflectance"],
                "local://missing/nir.tif",
            ),
        ]
        with self.assertRaises(RasterProcessingError) as context:
            self.processor.process(assets, AOI, "derived/ndvi.tif")
        self.assertEqual(context.exception.quality, GeospatialQuality.ASSET_UNAVAILABLE)

    def test_out_of_range_ndvi_raises_quality_error(self) -> None:
        assets = self._assets("scene", red_value=1.0, nir_value=-3.0)
        with self.assertRaises(RasterProcessingError) as context:
            self.processor.process(assets, AOI, "derived/ndvi.tif")
        self.assertEqual(context.exception.quality, GeospatialQuality.NDVI_OUT_OF_RANGE)

    def test_quality_policy_records_scl_masking(self) -> None:
        scl = np.full((4, 4), 4, dtype="uint8")
        scl[0, 0] = 8
        assets = self._assets("scene", red_value=1.0, nir_value=3.0, scl=scl)
        output = self.processor.process(
            assets,
            AOI,
            "derived/ndvi.tif",
            quality_policy=Sentinel2QualityPolicy(),
        )
        self.assertIsNotNone(output.quality_mask)
        mask = output.quality_mask or {}
        self.assertEqual(mask["valid_before_scl"], 16)
        self.assertEqual(mask["discarded_by_scl"], 1)
        self.assertEqual(mask["valid_after_scl"], 15)
        self.assertIn("SCL_20m", output.input_asset_keys)
        self.assertIn(GeospatialQuality.PARTIAL_COVERAGE, output.quality)

    def test_output_is_a_frozen_dataclass(self) -> None:
        output = self.processor.process(
            self._assets("scene", red_value=1.0, nir_value=3.0),
            AOI,
            "derived/ndvi.tif",
        )
        with self.assertRaises(Exception):
            output.output_reference = "other"  # type: ignore[misc]


class TemporalDeltaProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.storage = LocalObjectStorage(self.root)
        self.ndvi = NdviProcessor(self.storage)
        self.delta = TemporalDeltaProcessor(self.storage)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _assets(
        self, prefix: str, red_value: float, nir_value: float
    ) -> list[SatelliteAsset]:
        transform = from_origin(0, 1, 0.25, 0.25)
        rasters = {
            "B04_10m": np.full((4, 4), red_value, dtype="float32"),
            "B08_10m": np.full((4, 4), nir_value, dtype="float32"),
        }
        titles = {
            "B04_10m": "Red (band 4) - 10m",
            "B08_10m": "NIR 1 (band 8) - 10m",
        }
        assets: list[SatelliteAsset] = []
        for key, values in rasters.items():
            path = self.root / prefix / f"{key}.tif"
            path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                height=4,
                width=4,
                count=1,
                dtype="float32",
                crs="EPSG:4326",
                transform=transform,
                nodata=-9999.0,
            ) as dataset:
                dataset.write(values, 1)
            assets.append(
                _asset(
                    key,
                    titles[key],
                    ["reflectance"],
                    f"local://{prefix}/{key}.tif",
                )
            )
        return assets

    def test_identical_grid_delta_records_alignment(self) -> None:
        baseline = self.ndvi.process(
            self._assets("base", 1.0, 3.0), AOI, "derived/base.tif"
        )
        target = self.ndvi.process(
            self._assets("target", 1.0, 1.8), AOI, "derived/target.tif"
        )
        output = self.delta.process(
            baseline.output_reference,
            target.output_reference,
            "derived/delta.tif",
        )
        self.assertIsInstance(output, DeltaRasterProcessingOutput)
        self.assertEqual(output.alignment["status"], "IDENTICAL_GRID")
        self.assertEqual(output.alignment["reference_pixels"], 16)
        self.assertEqual(
            output.alignment["comparable_valid_pixels"],
            output.statistics.valid_count,
        )
        validate_cog(
            self.storage.read_local_path(output.output_reference),
            expected_value_range=(-2.0, 2.0),
        )

    def test_delta_statistics_match_ndvi_difference(self) -> None:
        baseline = self.ndvi.process(
            self._assets("base", 1.0, 3.0), AOI, "derived/base.tif"
        )
        target = self.ndvi.process(
            self._assets("target", 1.0, 1.8), AOI, "derived/target.tif"
        )
        output = self.delta.process(
            baseline.output_reference,
            target.output_reference,
            "derived/delta.tif",
        )
        baseline_mean = float(baseline.statistics.mean or 0)
        target_mean = float(target.statistics.mean or 0)
        self.assertAlmostEqual(
            float(output.statistics.mean or 0),
            target_mean - baseline_mean,
            places=5,
        )

    def test_no_comparable_pixels_raises_processing_failed(self) -> None:
        baseline = self.ndvi.process(
            self._assets("base", 1.0, 3.0), AOI, "derived/base.tif"
        )
        empty = np.full((4, 4), np.nan, dtype="float32")
        empty_path = self.root / "empty.tif"
        with rasterio.open(
            empty_path,
            "w",
            driver="GTiff",
            height=4,
            width=4,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=from_origin(0, 1, 0.25, 0.25),
            nodata=float("nan"),
        ) as dataset:
            dataset.write(empty, 1)
        empty_ref, _ = self.storage.put_bytes(
            "derived/empty.tif", empty_path.read_bytes(), "image/tiff"
        )
        with self.assertRaises(RasterProcessingError) as context:
            self.delta.process(
                baseline.output_reference,
                empty_ref,
                "derived/delta.tif",
            )
        self.assertEqual(context.exception.quality, GeospatialQuality.PROCESSING_FAILED)


if __name__ == "__main__":
    unittest.main()
