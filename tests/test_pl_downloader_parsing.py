"""Synthetic, offline regression tests for PL 94-171 parsing (#1488)."""

from io import BytesIO
import zipfile

import pandas as pd
import pytest

from siege_utilities.geo.census_files import pl_downloader


def _geo_record():
    # Keep the fixture independent of the parser's column-name list.
    fields = [""] * 37
    fields[:15] = [
        "PLST", "CA", "140", "00", "00", "000", "00", "0000001",
        "1400000US06037101110", "06037101110", "4", "9", "06",
        "01779778", "037",
    ]
    fields[32:35] = ["101110", "1", "1001"]
    return "|".join(fields) + "\n"


def _segment_record(segment, *tables):
    fields = ["PLST", "CA", "000", f"{segment:02d}", "0000001"]
    for start, count in tables:
        fields.extend(str(start + cell) for cell in range(1, count + 1))
    return "|".join(fields) + "\n"


@pytest.fixture
def install_archive(monkeypatch, tmp_path):
    """Exercise ZIP extraction, parsing, joins and caching without HTTP."""
    def no_network(*args, **kwargs):
        pytest.fail("PL parsing tests must not access the network")

    monkeypatch.setattr(pl_downloader.requests, "get", no_network)
    # Keep the cache round trip while isolating these parser tests from the
    # optional Parquet engine (including its native filesystem registration).
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, **kwargs: self.to_pickle(path))
    monkeypatch.setattr(pd, "read_parquet", pd.read_pickle)

    def install(files):
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            for filename, content in files.items():
                zf.writestr(filename, content)
        downloader = pl_downloader.PLFileDownloader(cache_dir=tmp_path)
        monkeypatch.setattr(downloader, "_stream_download", lambda url: archive.getvalue())
        monkeypatch.setattr(pl_downloader, "_default_downloader", downloader)
        return downloader

    return install


@pytest.mark.parametrize("table,start,count", [("P3", 3000, 71), ("P4", 4000, 73)])
def test_get_pl_data_voting_age_tables(install_archive, table, start, count):
    # Published segment 2: five linking fields, P3 (71), P4 (73), H1 (3).
    install_archive({
        "cageo2020.pl": _geo_record(),
        "ca000022020.pl": _segment_record(2, (3000, 71), (4000, 73), (6000, 3)),
    })

    result = pl_downloader.get_pl_data("CA", tables=[table])

    assert len(result) == 1
    columns = [f"{table}_{cell:03d}N" for cell in range(1, count + 1)]
    assert result.loc[0, columns].tolist() == [str(start + cell) for cell in range(1, count + 1)]


def test_housing_is_selected_from_segment_two(install_archive):
    downloader = install_archive({
        "cageo2020.pl": _geo_record(),
        "ca000012020.pl": _segment_record(1, (1000, 71), (2000, 73)),
        "ca000022020.pl": _segment_record(2, (3000, 71), (4000, 73), (6000, 3)),
        "ca000032020.pl": _segment_record(3, (5000, 10)),
    })

    result = pl_downloader.get_pl_data("CA", tables=["H1"])

    housing = ["H1_001N", "H1_002N", "H1_003N"]
    assert result.loc[0, housing].tolist() == ["6001", "6002", "6003"]
    assert pl_downloader.PL_TABLES["H1"]["file"] == "pl2"
    for segment in ("pl1", "pl3"):
        parsed = downloader._download_and_parse_data("fixture.zip", 2020, segment)
        assert not any(column.startswith("H1_") for column in parsed.columns)


@pytest.mark.parametrize("width", [35, 37, 40])
def test_california_geoid_uses_state_not_division(install_archive, width):
    fields = _geo_record().rstrip("\n").split("|")
    fields = (fields + ["extra"] * 3)[:width]
    install_archive({
        "cageo2020.pl": "|".join(fields) + "\n",
        "ca000012020.pl": _segment_record(1, (1000, 71), (2000, 73)),
    })

    result = pl_downloader.get_pl_data("CA", geography="tract", tables=["P1"])

    assert result.loc[0, "STATE"] == "06"
    assert result.loc[0, "GEOID"] == "06037101110"
    assert result.loc[0, ["COUNTY", "TRACT", "BLKGRP", "BLOCK"]].tolist() == [
        "037", "101110", "1", "1001",
    ]


def test_geo_header_missing_required_columns_is_rejected(install_archive):
    fields = _geo_record().rstrip("\n").split("|")[:12]
    downloader = install_archive({"cageo2020.pl": "|".join(fields) + "\n"})

    with pytest.raises(ValueError, match="2020 PL geographic header.*STATE"):
        downloader._download_and_parse_geo("fixture.zip", 2020)


@pytest.mark.parametrize("entry_point", ["public", "geo_parser", "data_parser"])
def test_2010_parsing_is_explicitly_unsupported(install_archive, entry_point):
    # Even a pipe-delimited fixture must be rejected: 2010 uses a different
    # format and must never reach the 2020 parser.
    downloader = install_archive({
        "cageo2010.pl": _geo_record(),
        "ca000012010.pl": _segment_record(1, (1000, 71), (2000, 73)),
    })

    with pytest.raises(NotImplementedError, match="2010.*fixed-width.*2020.*pipe-delimited"):
        if entry_point == "public":
            pl_downloader.get_pl_data("CA", year=2010, tables=["P1"])
        elif entry_point == "geo_parser":
            downloader._download_and_parse_geo("fixture.zip", 2010)
        else:
            downloader._download_and_parse_data("fixture.zip", 2010, "pl1")


def test_old_geo_cache_is_ignored_and_new_cache_is_reused(install_archive, monkeypatch):
    downloader = install_archive({
        "cageo2020.pl": _geo_record(),
        "ca000012020.pl": _segment_record(1, (1000, 71), (2000, 73)),
    })
    stale = pd.DataFrame({
        "LOGRECNO": ["0000001"], "SUMLEV": ["140"], "STATE": ["9"],
        "COUNTY": ["037"], "TRACT": ["101110"],
    })
    stale.to_parquet(downloader.cache_dir / "geo_CA_2020.parquet")

    result = pl_downloader.get_pl_data("CA", tables=["P1"])

    assert result.loc[0, "GEOID"] == "06037101110"

    def no_download(url):
        pytest.fail("The corrected parsed cache should be reused")

    monkeypatch.setattr(downloader, "_stream_download", no_download)
    pd.testing.assert_frame_equal(result, pl_downloader.get_pl_data("CA", tables=["P1"]))


def test_old_data_cache_is_ignored(install_archive):
    downloader = install_archive({
        "cageo2020.pl": _geo_record(),
        "ca000022020.pl": _segment_record(2, (3000, 71), (4000, 73), (6000, 3)),
    })
    pd.DataFrame({"LOGRECNO": ["0000001"], "P3_001N": ["-1"]}).to_parquet(
        downloader.cache_dir / "data_pl2_CA_2020.parquet"
    )

    result = pl_downloader.get_pl_data("CA", tables=["P3"])

    assert result.loc[0, "P3_001N"] == "3001"


def test_2010_cache_cannot_bypass_format_error(install_archive):
    downloader = install_archive({})
    pd.DataFrame({
        "LOGRECNO": ["0000001"], "SUMLEV": ["140"], "STATE": ["06"],
        "COUNTY": ["037"], "TRACT": ["101110"],
    }).to_parquet(downloader.cache_dir / "geo_CA_2010.parquet")
    pd.DataFrame({"LOGRECNO": ["0000001"], "P1_001N": ["1001"]}).to_parquet(
        downloader.cache_dir / "data_pl1_CA_2010.parquet"
    )

    with pytest.raises(NotImplementedError, match="2010.*fixed-width.*2020.*pipe-delimited"):
        pl_downloader.get_pl_data("CA", year=2010, tables=["P1"])


@pytest.mark.parametrize("segment,tables,expected", [
    (1, ((1000, 71), (2000, 73)), 149),
    (2, ((3000, 71), (4000, 73), (6000, 3)), 152),
    (3, ((5000, 10),), 15),
])
@pytest.mark.parametrize("extra", [False, True], ids=["truncated", "oversized"])
def test_segment_width_mismatch_is_explicit(install_archive, segment, tables, expected, extra):
    fields = _segment_record(segment, *tables).rstrip("\n").split("|")
    fields = fields + ["999"] if extra else fields[:-1]
    downloader = install_archive({f"ca0000{segment}2020.pl": "|".join(fields) + "\n"})

    with pytest.raises(ValueError, match=f"2020 PL pl{segment} has {len(fields)} columns; expected {expected}"):
        downloader._download_and_parse_data("fixture.zip", 2020, f"pl{segment}")


def test_all_tables_merge_without_duplicate_linking_fields(install_archive):
    install_archive({
        "cageo2020.pl": _geo_record(),
        "ca000012020.pl": _segment_record(1, (1000, 71), (2000, 73)),
        "ca000022020.pl": _segment_record(2, (3000, 71), (4000, 73), (6000, 3)),
        "ca000032020.pl": _segment_record(3, (5000, 10)),
    })

    result = pl_downloader.get_pl_data("CA")

    assert result.columns.is_unique
    assert result.loc[0, "GEOID"] == "06037101110"
    assert result.loc[0, "STUSAB"] == "CA"
    assert not any(column.endswith(("_x", "_y")) for column in result.columns)
    for table, start, count in [
        ("P1", 1000, 71), ("P2", 2000, 73), ("P3", 3000, 71),
        ("P4", 4000, 73), ("P5", 5000, 10), ("H1", 6000, 3),
    ]:
        columns = [f"{table}_{cell:03d}N" for cell in range(1, count + 1)]
        assert result.loc[0, columns].tolist() == [str(start + cell) for cell in range(1, count + 1)]
