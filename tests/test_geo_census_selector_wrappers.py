from siege_utilities import get_analysis_approach
from siege_utilities import get_census_intelligence
from siege_utilities import quick_census_selection
from siege_utilities import select_census_datasets
from siege_utilities import select_datasets_for_analysis
from siege_utilities import suggest_analysis_approach


class FakeSelector:
    def __init__(self):
        self.calls = []

    def select_datasets_for_analysis(
        self, analysis_type, geography_level, time_period=None, variables=None
    ):
        self.calls.append(
            (
                "select_datasets_for_analysis",
                analysis_type,
                geography_level,
                time_period,
                variables,
            )
        )
        return {"selected": analysis_type, "geography": geography_level}

    def suggest_analysis_approach(
        self, analysis_type, geography_level, time_constraints=None
    ):
        self.calls.append(
            ("suggest_analysis_approach", analysis_type, geography_level, time_constraints)
        )
        return {"approach": analysis_type, "geography": geography_level}


class FakeMapper:
    pass


def test_select_census_datasets_delegates_to_selector(monkeypatch):
    selector = FakeSelector()
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.get_census_data_selector",
        lambda: selector,
    )

    result = select_census_datasets(
        "demographics", "tract", time_period="latest", variables=["population"]
    )

    assert result == {"selected": "demographics", "geography": "tract"}
    assert selector.calls == [
        (
            "select_datasets_for_analysis",
            "demographics",
            "tract",
            "latest",
            ["population"],
        )
    ]


def test_select_datasets_for_analysis_delegates_to_selector(monkeypatch):
    selector = FakeSelector()
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.get_census_data_selector",
        lambda: selector,
    )

    result = select_datasets_for_analysis("housing", "county", variables=["rent"])

    assert result == {"selected": "housing", "geography": "county"}
    assert selector.calls == [
        ("select_datasets_for_analysis", "housing", "county", None, ["rent"])
    ]


def test_analysis_approach_wrappers_delegate_to_selector(monkeypatch):
    selector = FakeSelector()
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.get_census_data_selector",
        lambda: selector,
    )

    assert get_analysis_approach("business", "county", "quick") == {
        "approach": "business",
        "geography": "county",
    }
    assert suggest_analysis_approach("health", "tract", "comprehensive") == {
        "approach": "health",
        "geography": "tract",
    }
    assert selector.calls == [
        ("suggest_analysis_approach", "business", "county", "quick"),
        ("suggest_analysis_approach", "health", "tract", "comprehensive"),
    ]


def test_geo_quick_census_selection_combines_selector_helpers(monkeypatch):
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.select_census_datasets",
        lambda analysis_type, geography_level: {
            "selected": analysis_type,
            "geography": geography_level,
        },
    )
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.get_analysis_approach",
        lambda analysis_type, geography_level: {
            "approach": analysis_type,
            "geography": geography_level,
        },
    )

    assert quick_census_selection("education", "tract") == {
        "recommendations": {"selected": "education", "geography": "tract"},
        "analysis_approach": {"approach": "education", "geography": "tract"},
    }


def test_get_census_intelligence_returns_mapper_and_selector(monkeypatch):
    mapper = FakeMapper()
    selector = FakeSelector()
    monkeypatch.setattr(
        "siege_utilities.geo.census_dataset_mapper.get_census_dataset_mapper",
        lambda: mapper,
    )
    monkeypatch.setattr(
        "siege_utilities.geo.census_data_selector.get_census_data_selector",
        lambda: selector,
    )

    assert get_census_intelligence() == (mapper, selector)
