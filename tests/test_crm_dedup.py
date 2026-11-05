"""Identity and input-validation regressions for CRM deduplication (#1416)."""

import logging

import pandas as pd
import pytest

from siege_utilities.connectors._dedup import CRM_NAMESPACE, crm_dedup_pipeline
from siege_utilities.identifiers.uuid_generation import uuid5_from_seed


OUTPUT_COLUMNS = [
    "canonical_id", "normalized_name", "source_system", "source_id",
    "match_confidence", "name_candidate_id",
]
LEGACY_NAME_ID = str(uuid5_from_seed(CRM_NAMESPACE, "maria garcia"))


def _contact(source_id, **overrides):
    return {
        "first_name": "Maria",
        "last_name": "Garcia",
        "source_system": "crm_a",
        "source_id": source_id,
        **overrides,
    }


@pytest.mark.parametrize(
    "missing", [["source_id"], ["source_system"], ["source_id", "source_system"]],
)
def test_missing_required_columns_skip_entire_frame(missing, caplog):
    invalid = pd.DataFrame([_contact("bad-1"), _contact("bad-2")]).drop(columns=missing)
    valid = pd.DataFrame([_contact("valid")])

    with caplog.at_level(logging.WARNING):
        result = crm_dedup_pipeline([invalid, valid])

    assert result["source_id"].tolist() == ["valid"]
    assert list(result.columns) == OUTPUT_COLUMNS
    assert "DataFrame 0 missing columns" in caplog.text
    assert "skipping" in caplog.text
    assert all(column in caplog.text for column in missing)


@pytest.mark.parametrize("separate_frames", [False, True])
def test_same_normalized_name_with_different_emails_stays_distinct(separate_frames):
    rows = [
        _contact("a", email="maria.a@example.com"),
        _contact("b", first_name=" MARIA ", last_name="GARCIA",
                 source_system="crm_b", email="maria.b@example.com"),
    ]
    frames = [pd.DataFrame([row]) for row in rows] if separate_frames else [pd.DataFrame(rows)]

    result = crm_dedup_pipeline(frames)

    assert len(result) == 2
    assert result["normalized_name"].nunique() == 1
    assert result["canonical_id"].nunique() == 2


def test_same_name_and_normalized_email_match_with_full_confidence():
    frames = [
        pd.DataFrame([_contact("a", email=" Maria@Example.COM ")]),
        pd.DataFrame([_contact("b", source_system="crm_b", email="maria@example.com")]),
        pd.DataFrame([_contact("name-only", source_system="crm_c")]),
    ]

    result = crm_dedup_pipeline(frames).set_index("source_id")

    assert result.loc["a", "canonical_id"] == result.loc["b", "canonical_id"]
    assert result.loc[["a", "b"], "match_confidence"].eq(1.0).all()
    # An uncorroborated namesake must not join the identifier-backed match.
    assert result.loc["a", "canonical_id"] != result.loc["name-only", "canonical_id"]
    assert result.loc["name-only", "match_confidence"] == 0.5


def test_name_only_match_is_review_candidate_with_legacy_key():
    frames = [
        pd.DataFrame([_contact("a")]),
        pd.DataFrame([_contact("b", source_system="crm_b")]),
    ]

    result = crm_dedup_pipeline(frames)

    assert result["canonical_id"].nunique() == 2
    assert not result["canonical_id"].eq(LEGACY_NAME_ID).any()
    # Merge tables persisted by earlier versions join on the legacy key.
    assert result["name_candidate_id"].eq(LEGACY_NAME_ID).all()
    assert result["match_confidence"].eq(0.5).all()


def test_empty_and_no_name_rows_are_skipped():
    nameless = pd.DataFrame([
        _contact("empty", first_name="", last_name=""),
        _contact("whitespace", first_name=" \t", last_name=" "),
        _contact("punctuation", first_name="---", last_name="!!!"),
        _contact("none", first_name=None, last_name=None),
        _contact("nan", first_name=float("nan"), last_name=float("nan")),
        _contact("pd-na", first_name=pd.NA, last_name=pd.NA),
    ])
    missing_names = pd.DataFrame([{"source_system": "crm_a", "source_id": "missing"}])

    result = crm_dedup_pipeline([
        pd.DataFrame(), nameless, missing_names, pd.DataFrame([_contact("valid")]),
    ])

    assert result["source_id"].tolist() == ["valid"]
    assert result["normalized_name"].tolist() == ["maria garcia"]


@pytest.mark.parametrize("missing_name", [None, float("nan"), pd.NA])
def test_missing_name_part_is_not_converted_to_text(missing_name):
    frame = pd.DataFrame([_contact("a", first_name=missing_name)])

    result = crm_dedup_pipeline([frame])

    assert result["normalized_name"].tolist() == ["garcia"]
    assert result["match_confidence"].tolist() == [0.25]


@pytest.mark.parametrize("missing_identifier", [None, "", " \t", float("nan"), pd.NA])
def test_missing_identifier_value_falls_back_to_source_record_identity(missing_identifier):
    frame = pd.DataFrame([_contact("a", email=missing_identifier)])

    result = crm_dedup_pipeline([frame])

    record_seed = '["source_record", "crm_a", "a"]'
    assert result["canonical_id"].tolist() == [str(uuid5_from_seed(CRM_NAMESPACE, record_seed))]
    assert result["name_candidate_id"].tolist() == [LEGACY_NAME_ID]
    assert result["match_confidence"].tolist() == [0.5]


def test_custom_identifier_columns_replace_default_email():
    frame = pd.DataFrame([
        _contact("a", email="a@example.com", member_id=" MEMBER-1 "),
        _contact("b", email="b@example.com", member_id="member-1"),
        _contact("c", email="a@example.com", member_id="member-2"),
    ])

    result = crm_dedup_pipeline([frame], identifier_columns=["member_id"]).set_index("source_id")

    assert result.loc["a", "canonical_id"] == result.loc["b", "canonical_id"]
    assert result.loc["a", "canonical_id"] != result.loc["c", "canonical_id"]
    assert result["match_confidence"].eq(1.0).all()


def test_empty_identifier_columns_disables_identifier_merging():
    frame = pd.DataFrame([
        _contact("a", email="same@example.com"),
        _contact("b", email="same@example.com"),
    ])

    result = crm_dedup_pipeline([frame], identifier_columns=[])

    assert result["canonical_id"].nunique() == 2
    assert result["name_candidate_id"].eq(LEGACY_NAME_ID).all()
    assert result["match_confidence"].eq(0.5).all()


def test_multiple_identifiers_use_available_columns_and_unambiguous_values():
    frame = pd.DataFrame([
        _contact("a", email="a|b", member_id="c"),
        _contact("b", email="a", member_id="b|c"),
        _contact("c", email="a|b", member_id="different"),
    ])

    result = crm_dedup_pipeline([frame], identifier_columns=["absent", "email", "member_id"])
    reordered = crm_dedup_pipeline([frame], identifier_columns=["member_id", "email"])

    assert result["canonical_id"].nunique() == 3
    assert result["match_confidence"].eq(1.0).all()
    pd.testing.assert_frame_equal(result, reordered)


def test_identifier_column_names_distinguish_equal_values():
    frames = [
        pd.DataFrame([_contact("a", member_id="123")]),
        pd.DataFrame([_contact("b", account_id="123")]),
    ]

    result = crm_dedup_pipeline(frames, identifier_columns=["member_id", "account_id"])

    assert result["canonical_id"].nunique() == 2


def test_custom_source_columns_are_required_and_preserved():
    frame = pd.DataFrame([_contact("a")]).rename(
        columns={"source_system": "crm", "source_id": "record_id"},
    )
    invalid = frame.drop(columns="record_id")

    result = crm_dedup_pipeline([invalid, frame], source_system_column="crm", source_id_column="record_id")

    assert result["record_id"].tolist() == ["a"]
    assert list(result.columns) == [
        "canonical_id", "normalized_name", "crm", "record_id", "match_confidence", "name_candidate_id",
    ]


@pytest.mark.parametrize("frames", [[], [pd.DataFrame()], [pd.DataFrame([_contact("a", first_name="", last_name="")])]])
def test_empty_input_keeps_return_columns(frames):
    result = crm_dedup_pipeline(frames)

    assert result.empty
    assert list(result.columns) == OUTPUT_COLUMNS


def test_all_invalid_frames_return_empty_schema():
    result = crm_dedup_pipeline([pd.DataFrame([{"first_name": "Maria", "last_name": "Garcia"}])])

    assert result.empty
    assert list(result.columns) == OUTPUT_COLUMNS


@pytest.mark.parametrize("identifier, confidence", [
    (" NaN ", 0.5),
    ("\tNoNe\t", 0.5),
    (" NULL ", 0.5),
    (" <nA> ", 0.5),
    (" nAt ", 0.5),
    ("member-nan-1", 1.0),
    ("member-none-1", 1.0),
    ("member-null-1", 1.0),
    ("member-<na>-1", 1.0),
    ("member-nat-1", 1.0),
])
def test_textual_null_filter_matches_only_whole_normalized_tokens(identifier, confidence):
    frame = pd.DataFrame([
        _contact("a", member_id=identifier),
        _contact("b", source_system="crm_b", member_id=identifier),
    ])

    result = crm_dedup_pipeline([frame], identifier_columns=["member_id"])

    assert result["match_confidence"].eq(confidence).all()
    # Textual nulls are not corroboration, so those namesakes stay unmerged.
    assert result["canonical_id"].nunique() == (2 if confidence == 0.5 else 1)
    assert result["name_candidate_id"].eq(LEGACY_NAME_ID).all()


def test_textual_null_does_not_change_a_valid_identifier_match():
    frame = pd.DataFrame([
        _contact("a", email=" None ", member_id="123"),
        _contact("b", source_system="crm_b", member_id="123"),
    ])

    result = crm_dedup_pipeline([frame], identifier_columns=["email", "member_id"])

    assert result["canonical_id"].nunique() == 1
    assert result["match_confidence"].eq(1.0).all()


@pytest.mark.parametrize("name_columns, confidence", [
    (["first_name", "last_name"], 0.25),
    (["first_name", "absent"], 0.25),
    (["first_name"], 0.5),
])
def test_name_only_confidence_uses_configured_name_parts(name_columns, confidence):
    frame = pd.DataFrame([_contact("a", last_name=" \t")])

    result = crm_dedup_pipeline([frame], name_columns=name_columns)

    assert result["normalized_name"].tolist() == ["maria"]
    assert result["match_confidence"].tolist() == [confidence]


@pytest.mark.parametrize("sentinel", ["nan", "NaN", "None", "null", "<NA>", "NaT"])
def test_textual_null_identifier_is_not_corroborating_evidence(sentinel):
    frame = pd.DataFrame([
        _contact("a", email=sentinel),
        _contact("b", source_system="crm_b", email=sentinel),
    ])
    result = crm_dedup_pipeline([frame])
    assert result["match_confidence"].lt(1.0).all()


def test_surname_only_rows_are_weaker_than_full_name_candidates():
    frame = pd.DataFrame([
        _contact("a", first_name=None),
        _contact("b", source_system="crm_b", first_name=float("nan")),
        _contact("c"),
        _contact("d", source_system="crm_b"),
    ])
    r = crm_dedup_pipeline([frame]).set_index("source_id")

    assert r["canonical_id"].nunique() == 4
    assert r.loc["a", "name_candidate_id"] == r.loc["b", "name_candidate_id"]
    assert r.loc["a", "match_confidence"] < r.loc["c", "match_confidence"]


@pytest.mark.parametrize("identifier_columns", [None, []])
def test_uncorroborated_namesakes_stay_distinct_final_entities(identifier_columns):
    frames = [
        pd.DataFrame([_contact("a")]),
        pd.DataFrame([_contact("b", source_system="crm_b")]),
    ]

    result = crm_dedup_pipeline(frames, identifier_columns=identifier_columns)
    groups = result.groupby("canonical_id")["source_id"].apply(sorted).tolist()

    # A consumer grouping by canonical_id must not coalesce the namesakes.
    assert sorted(groups) == [["a"], ["b"]]
    # The name match survives only as a review-only candidate key.
    assert result["name_candidate_id"].eq(LEGACY_NAME_ID).all()
    assert result["match_confidence"].eq(0.5).all()


@pytest.mark.parametrize("missing_key", [None, float("nan"), pd.NA, "", " \t"])
def test_uncorroborated_rows_with_missing_source_key_stay_distinct(missing_key):
    frame = pd.DataFrame([
        _contact(missing_key),
        _contact(missing_key),
        _contact("a", source_system=missing_key),
    ])

    result = crm_dedup_pipeline([frame])
    rerun = crm_dedup_pipeline([frame])

    assert result["canonical_id"].nunique() == 3
    assert result["name_candidate_id"].eq(LEGACY_NAME_ID).all()
    # Deterministic for identical input.
    assert sorted(result["canonical_id"]) == sorted(rerun["canonical_id"])


def test_missing_source_key_rows_with_duplicate_index_labels_stay_distinct():
    first = pd.DataFrame([_contact(None)])
    second = pd.DataFrame([_contact(None, first_name="John", last_name="Smith")])
    # concat without ignore_index repeats label 0.
    frame = pd.concat([first, second])

    result = crm_dedup_pipeline([frame])

    assert frame.index.tolist() == [0, 0]
    assert result["canonical_id"].nunique() == 2


def test_corroborated_match_and_uncorroborated_namesake_share_only_candidate_key():
    frame = pd.DataFrame([
        _contact("a", email="maria@example.com"),
        _contact("b", source_system="crm_b", email="maria@example.com"),
        _contact("c", source_system="crm_c"),
    ])

    r = crm_dedup_pipeline([frame]).set_index("source_id")

    assert r.loc["a", "canonical_id"] == r.loc["b", "canonical_id"]
    assert r.loc["c", "canonical_id"] != r.loc["a", "canonical_id"]
    assert r["name_candidate_id"].eq(LEGACY_NAME_ID).all()


def test_repeated_uncorroborated_source_record_keeps_one_identity():
    frames = [pd.DataFrame([_contact("a")]), pd.DataFrame([_contact("a")])]

    result = crm_dedup_pipeline(frames)

    assert result["canonical_id"].nunique() == 1


def test_log_reports_unmerged_review_candidate_groups(caplog):
    frame = pd.DataFrame([
        _contact("a"),
        _contact("b", source_system="crm_b"),
        _contact("c", first_name="Ana", email="ana@example.com"),
        _contact("d", first_name="Ana", source_system="crm_b", email="ana@example.com"),
        _contact("a"),
    ])

    with caplog.at_level(logging.INFO, logger="siege_utilities.connectors._dedup"):
        crm_dedup_pipeline([frame])

    # The repeated source row "a" is not an identifier-corroborated match.
    assert "5 records → 3 canonical IDs" in caplog.text
    assert "2 records in identifier-corroborated matches" in caplog.text
    assert "1 name candidate groups left unmerged for review" in caplog.text
