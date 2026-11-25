"""A crosswalk cache that cannot be written or read must not lose a crosswalk (refs #1994).

``pip install 'siege-utilities[geo]'`` does not install pyarrow or
fastparquet, so pandas raises ``ImportError`` from ``to_parquet`` and
``read_parquet``. The parquet cache is optional: a failed cache write is
logged and the computed crosswalk is still returned, and a cache file that
cannot be read (no engine, or a corrupt file) is logged and treated as a
cache miss, so the crosswalk is downloaded.
"""

import logging

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk import crosswalk_client
from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient

LOGGER = "siege_utilities.geo.crosswalk.crosswalk_client"
READ_WARNING = "Cannot read crosswalk cache"
NO_ENGINE = ImportError(
    "Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'."
)


def _downloaded():
    return pd.DataFrame({
        "source_geoid": ["01001020100", "01001020200"],
        "target_geoid": ["01001020100", "01001020201"],
        "source_area": ["100", "200"],
        "overlap_area": ["100", "50"],
    })


def _raise_no_engine(*args, **kwargs):
    raise NO_ENGINE


@pytest.fixture
def downloads():
    return []


@pytest.fixture
def client(tmp_path, monkeypatch, downloads):
    client = CrosswalkClient(cache_dir=tmp_path)

    def download(*args, **kwargs):
        downloads.append(args)
        return _downloaded()

    monkeypatch.setattr(client, "_download_crosswalk", download)
    return client


def _read_warnings(caplog):
    return [record.getMessage() for record in caplog.records
            if record.name == LOGGER and record.getMessage().startswith(READ_WARNING)]


def test_crosswalk_is_returned_when_the_cache_cannot_be_written(client, tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(pd.DataFrame, "to_parquet", _raise_no_engine)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert list(result["area_weight"]) == [1.0, 0.25]
    assert list(tmp_path.glob("*.parquet")) == []
    assert any(
        record.name == LOGGER and "parquet" in record.getMessage().lower()
        for record in caplog.records
    )


def test_cache_is_a_miss_when_no_engine_can_read_it(client, tmp_path, monkeypatch, downloads, caplog):
    cache_key = client._generate_cache_key(2010, 2020, "tract", None)
    (tmp_path / f"{cache_key}.parquet").write_bytes(b"cached by an environment with pyarrow")
    monkeypatch.setattr(crosswalk_client.pd, "read_parquet", _raise_no_engine)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", _raise_no_engine)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    (warning,) = _read_warnings(caplog)
    assert "ImportError" in warning and "install pyarrow" in warning


@pytest.mark.parametrize("payload", [
    b"cached by an environment with pyarrow",
    b"",
    b"PAR1",
], ids=["garbage", "empty", "truncated-magic"])
def test_corrupt_cache_file_is_a_miss_with_an_engine_installed(client, tmp_path, downloads, caplog, payload):
    pa = pytest.importorskip("pyarrow")
    assert issubclass(pa.lib.ArrowInvalid, ValueError)
    cache_key = client._generate_cache_key(2010, 2020, "tract", None)
    (tmp_path / f"{cache_key}.parquet").write_bytes(payload)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    assert len(_read_warnings(caplog)) == 1


@pytest.fixture
def cache_file(client, tmp_path):
    path = tmp_path / f"{client._generate_cache_key(2010, 2020, 'tract', None)}.parquet"
    path.write_bytes(b"not a parquet file")
    return path


def _raiser(error):
    def read_parquet(*args, **kwargs):
        raise error
    return read_parquet


@pytest.mark.parametrize("error", [
    PermissionError(13, "Permission denied"),
    OSError(5, "Input/output error"),
], ids=["PermissionError", "OSError"])
def test_cache_is_a_miss_when_the_file_cannot_be_opened(client, cache_file, monkeypatch, downloads, caplog, error):
    """The OSError arm: pyarrow reports page-level corruption and I/O failures as OSError."""
    monkeypatch.setattr(crosswalk_client.pd, "read_parquet", _raiser(error))

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    (warning,) = _read_warnings(caplog)
    assert cache_file.name in warning
    assert type(error).__name__ in warning
    assert error.strerror in warning


@pytest.mark.parametrize("error", [TypeError("boom"), RuntimeError("boom"), KeyError("boom")],
                         ids=["TypeError", "RuntimeError", "KeyError"])
def test_other_read_errors_are_not_swallowed(client, cache_file, monkeypatch, downloads, error):
    """The handler is not a catch-all."""
    monkeypatch.setattr(crosswalk_client.pd, "read_parquet", _raiser(error))

    with pytest.raises(type(error)):
        client.get_crosswalk(2010, 2020, "tract")

    assert downloads == []


def test_unreadable_cache_is_replaced_so_the_next_call_is_a_hit(client, cache_file, downloads):
    pytest.importorskip("pyarrow")

    first = client.get_crosswalk(2010, 2020, "tract")
    second = client.get_crosswalk(2010, 2020, "tract")

    assert len(downloads) == 1
    pd.testing.assert_frame_equal(first.reset_index(drop=True), second)


@pytest.fixture
def one_bad_byte(client, downloads):
    """The client's own cache file with the first byte of one GEOID set to 0xFF (invalid UTF-8)."""
    pytest.importorskip("pyarrow")
    client.get_crosswalk(2010, 2020, "tract")
    (cache_file,) = list(client.cache_dir.glob("*.parquet"))
    data = bytearray(cache_file.read_bytes())
    at = data.find(b"01001020100")
    assert at > 0
    data[at] = 0xFF
    cache_file.write_bytes(bytes(data))
    downloads.clear()
    return cache_file


def test_pyarrow_raises_its_base_arrow_exception_for_one_bad_byte(one_bad_byte):
    pa = pytest.importorskip("pyarrow")
    with pytest.raises(Exception) as raised:
        pd.read_parquet(one_bad_byte)
    assert type(raised.value) is pa.lib.ArrowException
    assert not isinstance(raised.value, (ImportError, OSError, ValueError))


def test_one_bad_byte_in_the_cache_is_a_miss(one_bad_byte, client, downloads, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    (warning,) = _read_warnings(caplog)
    assert "ArrowException" in warning


def test_cache_is_a_miss_for_a_value_error_that_is_not_pyarrows(client, cache_file, monkeypatch, downloads, caplog):
    """The ValueError arm on its own: a plain ValueError, not an ArrowInvalid."""
    error = ValueError("Expecting property name enclosed in double quotes")
    monkeypatch.setattr(crosswalk_client.pd, "read_parquet", _raiser(error))

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    (warning,) = _read_warnings(caplog)
    assert "ValueError" in warning and str(error) in warning


def test_damaged_pandas_metadata_is_a_miss(client, downloads, caplog):
    """The same arm with a real file: pandas raises json.JSONDecodeError, a ValueError."""
    pq = pytest.importorskip("pyarrow.parquet")
    client.get_crosswalk(2010, 2020, "tract")
    (path,) = list(client.cache_dir.glob("*.parquet"))
    table = pq.read_table(path)
    metadata = dict(table.schema.metadata)
    metadata[b"pandas"] = b"{not json"
    pq.write_table(table.replace_schema_metadata(metadata), path)
    downloads.clear()

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        result = client.get_crosswalk(2010, 2020, "tract")

    assert list(result["target_geoid"]) == ["01001020100", "01001020201"]
    assert len(downloads) == 1
    (warning,) = _read_warnings(caplog)
    assert "JSONDecodeError" in warning
