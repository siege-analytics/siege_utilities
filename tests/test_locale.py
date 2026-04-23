"""Tests for NCES locale classifier module."""

import pytest
import geopandas as gpd
from shapely.geometry import Point, box

from siege_utilities.geo.locale import (
    ALL_LOCALE_CODES,
    CITY_LARGE,
    CITY_MIDSIZE,
    CITY_SMALL,
    RURAL_DISTANT,
    RURAL_FRINGE,
    RURAL_REMOTE,
    SUBURB_LARGE,
    SUBURB_MIDSIZE,
    SUBURB_SMALL,
    TOWN_DISTANT,
    TOWN_FRINGE,
    TOWN_REMOTE,
    LocaleCode,
    LocaleType,
    NCESLocaleClassifier,
    locale_from_code,
)


# ─── LocaleCode dataclass ─────────────────────────────────────────────────

class TestLocaleCode:
    """Tests for the LocaleCode dataclass."""

    def test_from_code_all_twelve(self):
        """All 12 valid codes should round-trip correctly."""
        expected_codes = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]
        for code in expected_codes:
            lc = LocaleCode.from_code(code)
            assert lc.code == code

    def test_from_code_invalid_raises(self):
        """Invalid codes should raise ValueError."""
        for code in [0, 10, 14, 20, 24, 30, 34, 40, 44, 50, -1, 99]:
            with pytest.raises(ValueError):
                LocaleCode.from_code(code)

    def test_categories(self):
        """Each code should map to the correct category."""
        assert CITY_LARGE.category == "city"
        assert CITY_MIDSIZE.category == "city"
        assert CITY_SMALL.category == "city"
        assert SUBURB_LARGE.category == "suburban"
        assert SUBURB_MIDSIZE.category == "suburban"
        assert SUBURB_SMALL.category == "suburban"
        assert TOWN_FRINGE.category == "town"
        assert TOWN_DISTANT.category == "town"
        assert TOWN_REMOTE.category == "town"
        assert RURAL_FRINGE.category == "rural"
        assert RURAL_DISTANT.category == "rural"
        assert RURAL_REMOTE.category == "rural"

    def test_subcategories(self):
        """Subcategory should match the NCES constant string."""
        assert CITY_LARGE.subcategory == "city_large"
        assert SUBURB_MIDSIZE.subcategory == "suburb_midsize"
        assert TOWN_FRINGE.subcategory == "town_fringe"
        assert RURAL_REMOTE.subcategory == "rural_remote"

    def test_labels(self):
        """Labels should be human-readable Title-Case."""
        assert CITY_LARGE.label == "City-Large"
        assert SUBURB_SMALL.label == "Suburb-Small"
        assert TOWN_DISTANT.label == "Town-Distant"
        assert RURAL_REMOTE.label == "Rural-Remote"

    def test_frozen(self):
        """LocaleCode should be immutable."""
        with pytest.raises(AttributeError):
            CITY_LARGE.code = 99

    def test_all_locale_codes_length(self):
        """ALL_LOCALE_CODES should contain exactly 12 entries."""
        assert len(ALL_LOCALE_CODES) == 12


class TestLocaleType:
    """Tests for the LocaleType enum."""

    def test_values(self):
        assert LocaleType.CITY == 1
        assert LocaleType.SUBURB == 2
        assert LocaleType.TOWN == 3
        assert LocaleType.RURAL == 4

    def test_names(self):
        assert LocaleType(1).name == "CITY"
        assert LocaleType(4).name == "RURAL"


class TestLocaleFromCode:
    """Tests for the locale_from_code fast lookup."""

    def test_returns_prebuilt_constant(self):
        result = locale_from_code(11)
        assert result is CITY_LARGE

    def test_returns_all_twelve(self):
        for code in [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43]:
            result = locale_from_code(code)
            assert result.code == code

    def test_invalid_falls_through(self):
        with pytest.raises(ValueError):
            locale_from_code(99)


# ─── Helper: build test classifier ────────────────────────────────────────

def _make_ua(bounds, pop=500_000, ua_id="00001"):
    """Create a UA GeoDataFrame from a bounding box."""
    return gpd.GeoDataFrame(
        {"UACE20": [ua_id], "POP20": [pop]},
        geometry=[box(*bounds)],
        crs="EPSG:4269",
    )


def _make_uc(bounds, uc_id="99001"):
    """Create a UC GeoDataFrame from a bounding box."""
    return gpd.GeoDataFrame(
        {"UACE20": [uc_id]},
        geometry=[box(*bounds)],
        crs="EPSG:4269",
    )


def _make_principal_cities(bounds, place_id="00100", pop=300_000):
    """Create a principal city GeoDataFrame."""
    return gpd.GeoDataFrame(
        {"PLACEFP": [place_id], "POP20": [pop]},
        geometry=[box(*bounds)],
        crs="EPSG:4269",
    )


def _empty_gdf():
    """Return an empty GeoDataFrame."""
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4269")


# ─── NCESLocaleClassifier ─────────────────────────────────────────────────

class TestClassifyPointCity:
    """Test city classification for points inside UA + principal city."""

    def test_city_large(self):
        """Point inside UA and principal city with pop >= 250k → City-Large."""
        ua = _make_ua((-78, 38, -76, 40), pop=500_000)
        pc = _make_principal_cities((-78, 38, -76, 40), pop=300_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={"00100": 300_000},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 11
        assert result.category == "city"

    def test_city_midsize(self):
        """Principal city pop 100k-249k → City-Midsize."""
        ua = _make_ua((-78, 38, -76, 40), pop=200_000)
        pc = _make_principal_cities((-78, 38, -76, 40), pop=150_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={"00100": 150_000},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 12

    def test_city_small(self):
        """Principal city pop < 100k → City-Small."""
        ua = _make_ua((-78, 38, -76, 40), pop=80_000)
        pc = _make_principal_cities((-78, 38, -76, 40), pop=50_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={"00100": 50_000},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 13


class TestClassifyPointSuburb:
    """Test suburb classification for points inside UA but outside principal city."""

    def test_suburb_large(self):
        """Inside UA, outside principal city, UA pop >= 250k → Suburb-Large."""
        ua = _make_ua((-78, 38, -76, 40), pop=500_000)
        # Principal city is a small box that does NOT contain the test point
        pc = _make_principal_cities((-78, 38, -77.5, 38.5), pop=300_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={"00100": 300_000},
            ua_populations={"00001": 500_000},
        )
        # Point at (-77, 39) is inside UA but outside the small PC box
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 21
        assert result.category == "suburban"

    def test_suburb_midsize(self):
        """UA pop 100k-249k → Suburb-Midsize."""
        ua = _make_ua((-78, 38, -76, 40), pop=150_000)
        pc = _make_principal_cities((-78, 38, -77.5, 38.5), pop=60_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={},
            ua_populations={"00001": 150_000},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 22

    def test_suburb_small(self):
        """UA pop < 100k → Suburb-Small."""
        ua = _make_ua((-78, 38, -76, 40), pop=60_000)
        pc = _make_principal_cities((-78, 38, -77.5, 38.5), pop=30_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={},
            ua_populations={"00001": 60_000},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 23


class TestClassifyPointTown:
    """Test town classification for points inside UC."""

    def test_town_fringe(self):
        """Inside UC, very close to UA → Town-Fringe."""
        # UC contains the test point at (-77, 39)
        uc = _make_uc((-78, 38, -76, 40))
        # UA is just outside the test point but very close — ~0.02 degrees
        # from point edge ≈ ~1.7 km ≈ ~1 mile → well within 10-mile fringe
        # Place the UA adjacent but not overlapping the UC
        ua = _make_ua((-76, 38.9, -75.98, 39.1), pop=500_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=uc,
            principal_cities=_empty_gdf(),
            place_populations={},
        )
        # Point is at (-77, 39) — inside UC, with UA edge at ~(-76, 39) which
        # is about 85 km ≈ 53 miles in projection... that's too far for fringe.
        # Instead test a point near the UC edge, close to the UA.
        result = classifier.classify_point(-76.01, 39.0)
        assert result.code == 31

    def test_town_remote(self):
        """Inside UC, very far from UA → Town-Remote."""
        # UC contains the test point
        uc = _make_uc((-78, 38, -76, 40))
        # UA is very far away (10 degrees ≈ ~600 miles)
        ua = _make_ua((-68, 48, -66, 50), pop=500_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=uc,
            principal_cities=_empty_gdf(),
            place_populations={},
        )
        result = classifier.classify_point(-77.0, 39.0)
        assert result.code == 33


class TestClassifyPointRural:
    """Test rural classification for points outside both UA and UC."""

    def test_rural_remote_no_ua_no_uc(self):
        """No UA or UC anywhere → Rural-Remote."""
        classifier = NCESLocaleClassifier(
            urbanized_areas=_empty_gdf(),
            urban_clusters=_empty_gdf(),
            principal_cities=_empty_gdf(),
            place_populations={},
        )
        result = classifier.classify_point(-105.0, 42.0)
        assert result.code == 43
        assert result.category == "rural"

    def test_rural_remote_far_from_everything(self):
        """Far from both UA and UC → Rural-Remote."""
        ua = _make_ua((-74, 40, -73, 41), pop=500_000)
        uc = _make_uc((-74, 40, -73, 41))
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=uc,
            principal_cities=_empty_gdf(),
            place_populations={},
        )
        # Point in Wyoming, far from NYC-area UA/UC
        result = classifier.classify_point(-108.0, 43.0)
        assert result.code == 43


class TestClassifyPoints:
    """Test bulk point classification."""

    def test_bulk_adds_columns(self):
        """classify_points should add locale_code/category/subcategory/label."""
        ua = _make_ua((-78, 38, -76, 40), pop=500_000)
        pc = _make_principal_cities((-78, 38, -76, 40), pop=300_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=pc,
            place_populations={"00100": 300_000},
        )
        points = gpd.GeoDataFrame(
            {"name": ["A", "B"]},
            geometry=[Point(-77.0, 39.0), Point(-77.0, 39.0)],
            crs="EPSG:4269",
        )
        result = classifier.classify_points(points)
        assert "locale_code" in result.columns
        assert "locale_category" in result.columns
        assert "locale_subcategory" in result.columns
        assert "locale_label" in result.columns
        assert list(result["locale_code"]) == [11, 11]


class TestClassifyPolygon:
    """Test polygon classification."""

    def test_majority_method(self):
        """classify_polygon with majority should return single code."""
        ua = _make_ua((-78, 38, -76, 40), pop=500_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=_empty_gdf(),
            place_populations={},
            ua_populations={"00001": 500_000},
        )
        # Polygon fully inside UA
        poly = box(-77.5, 38.5, -76.5, 39.5)
        result = classifier.classify_polygon(poly, method="majority")
        assert "locale_code" in result
        assert "locale_label" in result

    def test_distribution_method(self):
        """classify_polygon with distribution should return dict of fractions."""
        ua = _make_ua((-78, 38, -77, 39), pop=500_000)
        classifier = NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=None,
            principal_cities=_empty_gdf(),
            place_populations={},
        )
        # Polygon partially overlaps UA
        poly = box(-77.5, 38.5, -76.5, 39.5)
        result = classifier.classify_polygon(poly, method="distribution")
        assert isinstance(result, dict)
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01  # fractions sum to ~1


class TestLocaleLabel:
    """Test the static locale_label helper."""

    def test_known_labels(self):
        assert NCESLocaleClassifier.locale_label(11) == "City-Large"
        assert NCESLocaleClassifier.locale_label(43) == "Rural-Remote"
        assert NCESLocaleClassifier.locale_label(31) == "Town-Fringe"

    def test_invalid_code(self):
        with pytest.raises(ValueError):
            NCESLocaleClassifier.locale_label(99)


class TestSettingsOverride:
    """Test that projection CRS can be overridden."""

    def test_custom_projection_crs(self):
        """Classifier should accept a custom projection CRS."""
        classifier = NCESLocaleClassifier(
            urbanized_areas=_empty_gdf(),
            urban_clusters=_empty_gdf(),
            principal_cities=_empty_gdf(),
            place_populations={},
            projection_crs=3338,  # Alaska Albers
        )
        assert classifier._projection_crs == 3338


# ─── Regression: from_census_year-style inputs cover all 4 categories ────

class TestFromCensusYearCategoryCoverage:
    """Regression tests: a classifier built with from_census_year-style data
    (UC-equivalent derivation, population-filtered principal cities) can
    produce all 4 NCES category families: City, Suburb, Town, Rural.

    These tests simulate the data that from_census_year() constructs:
    - UAs derived from urban areas with pop >= 50,000
    - UC-equivalents derived from urban areas with pop < 50,000
    - Principal cities filtered by population >= 25,000 (small_city threshold)
    - Place populations extracted from shapefile attributes
    """

    @pytest.fixture
    def census_style_classifier(self):
        """Build a classifier mimicking from_census_year(year=2020) output.

        Layout (Washington DC area, all in EPSG:4269):
        - Large UA (pop 500k): covers (-78, 38) to (-76, 40) — contains DC
        - UC-equivalent (pop 10k): covers (-80, 38) to (-79, 39) — small town
        - Principal city: covers (-77.5, 38.5) to (-76.5, 39.5) — subset of UA
        """
        # Urbanized Area — large, pop >= 50k threshold
        ua = gpd.GeoDataFrame(
            {"UACE20": ["00001"], "POP20": [500_000]},
            geometry=[box(-78, 38, -76, 40)],
            crs="EPSG:4269",
        )
        # UC-equivalent — small urban area, pop < 50k threshold
        uc = gpd.GeoDataFrame(
            {"UACE20": ["99001"], "POP20": [10_000]},
            geometry=[box(-80, 38, -79, 39)],
            crs="EPSG:4269",
        )
        # Principal city — filtered by population >= 25k
        pc = gpd.GeoDataFrame(
            {"PLACEFP": ["00100"], "POP20": [300_000]},
            geometry=[box(-77.5, 38.5, -76.5, 39.5)],
            crs="EPSG:4269",
        )
        return NCESLocaleClassifier(
            urbanized_areas=ua,
            urban_clusters=uc,
            principal_cities=pc,
            place_populations={"00100": 300_000},
            ua_populations={"00001": 500_000},
        )

    def test_city_reachable(self, census_style_classifier):
        """Point inside UA and principal city → City category."""
        result = census_style_classifier.classify_point(-77.0, 39.0)
        assert result.category == "city"
        assert result.code == 11  # City-Large (pop 300k >= 250k)

    def test_suburb_reachable(self, census_style_classifier):
        """Point inside UA but outside principal city → Suburb category."""
        # (-77.9, 38.1) is inside the UA but outside the PC box
        result = census_style_classifier.classify_point(-77.9, 38.1)
        assert result.category == "suburban"

    def test_town_reachable(self, census_style_classifier):
        """Point inside UC-equivalent → Town category."""
        # (-79.5, 38.5) is inside the UC-equivalent
        result = census_style_classifier.classify_point(-79.5, 38.5)
        assert result.category == "town"

    def test_rural_reachable(self, census_style_classifier):
        """Point outside both UA and UC → Rural category."""
        # (-105, 42) is in Wyoming, far from any urban area
        result = census_style_classifier.classify_point(-105.0, 42.0)
        assert result.category == "rural"

    def test_all_four_categories_covered(self, census_style_classifier):
        """A single classifier can produce all 4 categories."""
        categories = set()
        test_points = [
            (-77.0, 39.0),    # inside UA + PC → city
            (-77.9, 38.1),    # inside UA, outside PC → suburb
            (-79.5, 38.5),    # inside UC → town
            (-105.0, 42.0),   # far from everything → rural
        ]
        for lon, lat in test_points:
            result = census_style_classifier.classify_point(lon, lat)
            categories.add(result.category)
        assert categories == {"city", "suburban", "town", "rural"}


class TestFromCensusYearHelpers:
    """Tests for the helper constants and _find_column function."""

    def test_find_column_returns_first_match(self):
        """_find_column returns the first matching column name."""
        from siege_utilities.geo.locale import _find_column
        gdf = gpd.GeoDataFrame({"POP20": [100], "GEOID": ["01"]})
        assert _find_column(gdf, ("POPULATION", "POP20", "POP10")) == "POP20"

    def test_find_column_returns_none_for_no_match(self):
        """_find_column returns None when no candidate matches."""
        from siege_utilities.geo.locale import _find_column
        gdf = gpd.GeoDataFrame({"NAME": ["test"]})
        assert _find_column(gdf, ("POP20", "POP10")) is None

    def test_find_column_handles_none_input(self):
        """_find_column returns None for None input."""
        from siege_utilities.geo.locale import _find_column
        assert _find_column(None, ("POP20",)) is None

    def test_ua_pop_threshold_value(self):
        """_UA_POP_THRESHOLD should be 50,000."""
        from siege_utilities.geo.locale import _UA_POP_THRESHOLD
        assert _UA_POP_THRESHOLD == 50_000
