"""Tests for siege_utilities.survey.registry (client ↔ survey mapping)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from siege_utilities.survey import (
    ClientSurveyError,
    ClientSurveyRegistry,
    Wave,
    WaveSet,
)


def _ws(name: str, client_id: str | None = None) -> WaveSet:
    df = pd.DataFrame({"party": ["D", "R"]})
    return WaveSet(
        name=name,
        waves=[Wave(id="W1", date=date(2024, 3, 1), df=df)],
        client_id=client_id,
    )


class TestRegisterPreset:
    def test_register_with_client_id_set(self):
        reg = ClientSurveyRegistry()
        ws = _ws("Tracker", client_id="acme")
        reg.register(ws)
        assert reg.surveys_for("acme") == [ws]

    def test_register_without_client_id_raises(self):
        reg = ClientSurveyRegistry()
        with pytest.raises(ClientSurveyError, match="no client_id"):
            reg.register(_ws("Tracker"))


class TestRegisterFor:
    def test_sets_client_id(self):
        reg = ClientSurveyRegistry()
        ws = _ws("Tracker")
        reg.register_for("acme", ws)
        assert ws.client_id == "acme"

    def test_empty_client_id_raises(self):
        reg = ClientSurveyRegistry()
        with pytest.raises(ClientSurveyError, match="non-empty"):
            reg.register_for("", _ws("Tracker"))

    def test_duplicate_name_same_client_raises(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        with pytest.raises(ClientSurveyError, match="already has a survey"):
            reg.register_for("acme", _ws("Tracker"))

    def test_same_name_different_clients_allowed(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        reg.register_for("beacon", _ws("Tracker"))
        assert len(reg) == 2


class TestLookup:
    def test_surveys_for_unknown_returns_empty(self):
        assert ClientSurveyRegistry().surveys_for("nobody") == []

    def test_get_survey_miss_returns_none(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        assert reg.get_survey("acme", "Missing") is None
        assert reg.get_survey("unknown", "Tracker") is None

    def test_require_survey_raises_on_miss(self):
        reg = ClientSurveyRegistry()
        with pytest.raises(ClientSurveyError):
            reg.require_survey("acme", "Tracker")

    def test_client_of_by_field(self):
        reg = ClientSurveyRegistry()
        ws = _ws("Tracker", client_id="acme")
        reg.register(ws)
        assert reg.client_of(ws) == "acme"

    def test_client_of_reverse_lookup_when_field_cleared(self):
        reg = ClientSurveyRegistry()
        ws = _ws("Tracker", client_id="acme")
        reg.register(ws)
        ws.client_id = None  # simulate defensive mutation
        assert reg.client_of(ws) == "acme"

    def test_client_of_unregistered_returns_none(self):
        assert ClientSurveyRegistry().client_of(_ws("Tracker")) is None


class TestUnregister:
    def test_unregister_returns_waveset(self):
        reg = ClientSurveyRegistry()
        ws = reg.register_for("acme", _ws("Tracker"))
        assert reg.unregister("acme", "Tracker") is ws
        assert reg.surveys_for("acme") == []

    def test_unregister_last_removes_client_row(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        reg.unregister("acme", "Tracker")
        assert "acme" not in reg

    def test_unregister_miss_raises(self):
        reg = ClientSurveyRegistry()
        with pytest.raises(ClientSurveyError):
            reg.unregister("acme", "Tracker")


class TestContainsLen:
    def test_contains_client_id(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        assert "acme" in reg
        assert "beacon" not in reg

    def test_contains_tuple(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("Tracker"))
        assert ("acme", "Tracker") in reg
        assert ("acme", "Other") not in reg

    def test_len_counts_all_surveys(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("S1"))
        reg.register_for("acme", _ws("S2"))
        reg.register_for("beacon", _ws("S1"))
        assert len(reg) == 3

    def test_clients_lists_registered_ids(self):
        reg = ClientSurveyRegistry()
        reg.register_for("acme", _ws("S1"))
        reg.register_for("beacon", _ws("S1"))
        assert set(reg.clients()) == {"acme", "beacon"}
