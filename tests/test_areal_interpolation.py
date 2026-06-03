"""Tests for areal interpolation module.

Uses synthetic polygons with known geometry to verify area-weighted
interpolation produces correct results.
"""

import pytest
import numpy as np
import geopandas as gpd
from shapely.geometry import box


@pytest.fixture
def source_gdf():
    """Create a source GeoDataFrame: one large polygon covering a 2x2 unit area."""
    return gpd.GeoDataFrame(
        {"total_pop": [1000], "median_income": [50000.0]},
        geometry=[box(0, 0, 2, 2)],
        crs="EPSG:4326",
    )


@pytest.fixture
def target_gdf():
    """Create target GeoDataFrame: four 1x1 quadrants of the source polygon."""
    return gpd.GeoDataFrame(
        {"name": ["SW", "SE", "NW", "NE"]},
        geometry=[
            box(0, 0, 1, 1),
            box(1, 0, 2, 1),
            box(0, 1, 1, 2),
            box(1, 1, 2, 2),
        ],
        crs="EPSG:4326",
    )


@pytest.fixture
def two_source_gdf():
    """Two source polygons with different values, overlapping the same target."""
    return gpd.GeoDataFrame(
        {"total_pop": [400, 600], "density": [100.0, 200.0]},
        geometry=[box(0, 0, 1, 2), box(1, 0, 2, 2)],
        crs="EPSG:4326",
    )


class TestArealInterpolationResult:
    """Tests for the result dataclass."""

    def test_result_fields(self):
        from siege_utilities.geo.interpolation.areal import ArealInterpolationResult

        result = ArealInterpolationResult(
            data=gpd.GeoDataFrame(),
            extensive_variables=["pop"],
            intensive_variables=["income"],
            n_source=10,
            n_target=20,
        )
        assert result.extensive_variables == ["pop"]
        assert result.intensive_variables == ["income"]
        assert result.n_source == 10
        assert result.n_target == 20
        assert result.warnings == []


class TestInterpolateExtensive:
    """Tests for extensive (total/count) variable interpolation."""

    def test_splits_population_by_area(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_extensive

        result = interpolate_extensive(
            source_gdf=source_gdf,
            target_gdf=target_gdf,
            variables=["total_pop"],
        )
        assert result.n_source == 1
        assert result.n_target == 4
        # Each quadrant should get ~250 (1/4 of 1000)
        values = result.data["total_pop"].values
        assert len(values) == 4
        np.testing.assert_allclose(values, 250.0, atol=1.0)

    def test_conserves_total(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_extensive

        result = interpolate_extensive(
            source_gdf=source_gdf,
            target_gdf=target_gdf,
            variables=["total_pop"],
        )
        assert result is not None
        assert "total_pop" in result.data.columns
        total = result.data["total_pop"].sum()
        np.testing.assert_allclose(total, 1000.0, atol=1.0)


class TestInterpolateIntensive:
    """Tests for intensive (rate/density) variable interpolation."""

    def test_uniform_intensive_stays_constant(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_intensive

        result = interpolate_intensive(
            source_gdf=source_gdf,
            target_gdf=target_gdf,
            variables=["median_income"],
        )
        assert result is not None
        assert "median_income" in result.data.columns
        values = result.data["median_income"].values
        # Uniform source - all targets get same value
        np.testing.assert_allclose(values, 50000.0, atol=1.0)


class TestInterpolateAreal:
    """Tests for the combined interpolation function."""

    def test_mixed_variables(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_areal

        result = interpolate_areal(
            source_gdf=source_gdf,
            target_gdf=target_gdf,
            extensive_variables=["total_pop"],
            intensive_variables=["median_income"],
        )
        assert "total_pop" in result.data.columns
        assert "median_income" in result.data.columns
        assert result.extensive_variables == ["total_pop"]
        assert result.intensive_variables == ["median_income"]

    def test_no_variables_raises(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_areal

        with pytest.raises(ValueError, match="At least one"):
            interpolate_areal(source_gdf=source_gdf, target_gdf=target_gdf)

    def test_missing_variable_raises(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_areal

        with pytest.raises(ValueError, match="not found in source"):
            interpolate_areal(
                source_gdf=source_gdf,
                target_gdf=target_gdf,
                extensive_variables=["nonexistent_col"],
            )

    def test_crs_mismatch_warning(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_areal

        target_3857 = target_gdf.to_crs("EPSG:3857")
        result = interpolate_areal(
            source_gdf=source_gdf,
            target_gdf=target_3857,
            extensive_variables=["total_pop"],
        )
        assert any("CRS mismatch" in w for w in result.warnings)

    def test_two_sources_extensive(self, two_source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_extensive

        result = interpolate_extensive(
            source_gdf=two_source_gdf,
            target_gdf=target_gdf,
            variables=["total_pop"],
        )
        assert result is not None
        assert "total_pop" in result.data.columns
        total = result.data["total_pop"].sum()
        np.testing.assert_allclose(total, 1000.0, atol=1.0)

    def test_result_has_target_geometry(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import interpolate_extensive

        result = interpolate_extensive(
            source_gdf=source_gdf,
            target_gdf=target_gdf,
            variables=["total_pop"],
        )
        # Result should have target's geometry
        assert len(result.data) == 4
        assert result.data.crs is not None


class TestComputeAreaWeights:
    """Tests for the area weight computation."""

    def test_full_overlap_returns_data(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import compute_area_weights

        weights = compute_area_weights(source_gdf, target_gdf)
        assert len(weights) > 0

    def test_documented_columns_present(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import compute_area_weights

        weights = compute_area_weights(source_gdf, target_gdf)
        assert len(weights) > 0
        for col in ("source_idx", "target_idx", "overlap_area",
                     "source_fraction", "target_fraction"):
            assert col in weights.columns, f"Missing documented column: {col}"
        assert (weights["source_fraction"] >= 0).all()
        assert (weights["source_fraction"] <= 1.0 + 1e-6).all()
        assert (weights["target_fraction"] >= 0).all()

    def test_no_overlap_returns_empty(self):
        from siege_utilities.geo.interpolation import compute_area_weights

        source = gpd.GeoDataFrame(
            geometry=[box(0, 0, 1, 1)], crs="EPSG:4326"
        )
        target = gpd.GeoDataFrame(
            geometry=[box(10, 10, 11, 11)], crs="EPSG:4326"
        )
        weights = compute_area_weights(source, target)
        assert len(weights) == 0


# ---------------------------------------------------------------------------
# #986: Backend-specific tests
# ---------------------------------------------------------------------------

class TestShapelyBackend:
    """Test pure-Shapely areal interpolation (no tobler, no DuckDB)."""

    def test_extensive_even_split(self, source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False), \
             patch.object(areal, "_DUCKDB_AVAILABLE", False):
            result = areal.interpolate_areal(
                source_gdf, target_gdf,
                extensive_variables=["total_pop"],
            )
        assert result.backend == "shapely"
        pops = result.data["total_pop"].values
        assert np.allclose(pops.sum(), 1000, atol=1.0)
        assert np.allclose(pops, 250, atol=1.0)

    def test_intensive_uniform(self, source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False), \
             patch.object(areal, "_DUCKDB_AVAILABLE", False):
            result = areal.interpolate_areal(
                source_gdf, target_gdf,
                intensive_variables=["median_income"],
            )
        assert result.backend == "shapely"
        incomes = result.data["median_income"].values
        assert np.allclose(incomes, 50000, atol=1.0)

    def test_two_sources_extensive(self, two_source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False), \
             patch.object(areal, "_DUCKDB_AVAILABLE", False):
            result = areal.interpolate_areal(
                two_source_gdf, target_gdf,
                extensive_variables=["total_pop"],
            )
        assert result.backend == "shapely"
        assert np.allclose(result.data["total_pop"].sum(), 1000, atol=1.0)


class TestDuckDBBackend:
    """Test DuckDB-spatial areal interpolation."""

    @pytest.fixture(autouse=True)
    def _skip_without_duckdb(self):
        pytest.importorskip("duckdb")

    def test_extensive_even_split(self, source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False):
            result = areal.interpolate_areal(
                source_gdf, target_gdf,
                extensive_variables=["total_pop"],
            )
        assert result.backend == "duckdb"
        pops = result.data["total_pop"].values
        assert np.allclose(pops.sum(), 1000, atol=1.0)
        assert np.allclose(pops, 250, atol=1.0)

    def test_intensive_uniform(self, source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False):
            result = areal.interpolate_areal(
                source_gdf, target_gdf,
                intensive_variables=["median_income"],
            )
        assert result.backend == "duckdb"
        incomes = result.data["median_income"].values
        assert np.allclose(incomes, 50000, atol=1.0)

    def test_two_sources_extensive(self, two_source_gdf, target_gdf):
        from unittest.mock import patch
        from siege_utilities.geo.interpolation import areal

        with patch.object(areal, "_TOBLER_AVAILABLE", False):
            result = areal.interpolate_areal(
                two_source_gdf, target_gdf,
                extensive_variables=["total_pop"],
            )
        assert result.backend == "duckdb"
        assert np.allclose(result.data["total_pop"].sum(), 1000, atol=1.0)


class TestBackendSelection:
    """Test backend dispatch logic."""

    def test_reports_backend_in_result(self, source_gdf, target_gdf):
        from siege_utilities.geo.interpolation import areal

        result = areal.interpolate_areal(
            source_gdf, target_gdf,
            extensive_variables=["total_pop"],
        )
        assert result.backend in ("tobler", "duckdb", "shapely")
