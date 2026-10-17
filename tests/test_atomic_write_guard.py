"""The atomic-write guard must distinguish staging from final destinations."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/check_atomic_writes.py"
spec = importlib.util.spec_from_file_location("atomic_write_guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def scan(tmp_path, source):
    path = tmp_path / "writer.py"
    path.write_text(source)
    return guard.scan_file(path)


@pytest.mark.parametrize("sink", [
    'open(path, "w")', 'open(file=path, mode="wb")',
    'path.open("w")', 'path.write_text("data")', 'path.write_bytes(b"data")',
    'df.to_csv(path)', 'df.to_parquet(path=path)', 'gdf.to_file(filename=path)',
])
def test_rejects_each_direct_final_path_sink(tmp_path, sink):
    assert len(scan(tmp_path, f"def save(path):\n    {sink}\n")) == 1


@pytest.mark.parametrize("source", [
    'from siege_utilities.files.operations import atomic_write_path as atomic\n'
    'with atomic(final) as tmp:\n    tmp.write_text("ok")\n',
    'import tempfile\nfrom pathlib import Path\n'
    'with tempfile.NamedTemporaryFile() as f:\n    Path(f.name).write_bytes(b"ok")\n',
    'from tempfile import mkstemp\nfd, tmp = mkstemp()\n'
    'alias = tmp\nwith open(alias, "wb") as f:\n    df.to_csv(f)\n',
    'import io\nimport sys\nbuffer = io.BytesIO()\n'
    'df.to_csv(sys.stdout)\ndf.to_parquet(buffer)\ndf.to_csv()\ndf.to_csv(None)\n',
    'from sys import stdout as output\ndf.to_csv(output)\n',
    'import tempfile\nfrom pathlib import Path\n'
    'with tempfile.TemporaryDirectory() as directory:\n'
    '    tmp = Path(directory) / "data.csv"\n    df.to_csv(str(tmp))\n',
])
def test_accepts_proven_temporary_or_memory_destinations(tmp_path, source):
    assert scan(tmp_path, source) == []


@pytest.mark.parametrize("body", [
    '    final.write_text("bad")\n',
    '    tmp = final\n    tmp.write_text("bad")\n',
    '    if condition:\n        tmp = final\n    tmp.write_text("bad")\n',
    '    for tmp in destinations:\n        tmp.write_text("bad")\n',
    '    def unrelated(tmp):\n        tmp.write_text("bad")\n',
    '    pass\ntmp.write_text("bad")\n',
])
def test_temp_binding_does_not_exempt_other_writes(tmp_path, body):
    source = ('from siege_utilities.files.operations import atomic_write_path\n'
              'with atomic_write_path(final) as tmp:\n' + body)
    assert len(scan(tmp_path, source)) == 1


def test_filename_spelling_is_not_temporary_provenance(tmp_path):
    assert len(scan(tmp_path, 'tmp = "output.csv"\ntmp.write_text("bad")\n')) == 1


def test_temporary_directory_cannot_exempt_absolute_join(tmp_path):
    source = ('import tempfile\nfrom pathlib import Path\n'
              'with tempfile.TemporaryDirectory() as directory:\n'
              '    Path(directory, "/final.csv").write_text("bad")\n')
    assert len(scan(tmp_path, source)) == 1


def test_allowlist_is_exact_counted_and_rejects_stale_entries(tmp_path):
    source = 'def save(path):\n    path.write_text("data")\n'
    finding = scan(tmp_path, source)[0]
    entry = {k: v for k, v in finding.items() if k != "line"}
    entry.update(file="writer.py", count=1, reason="Reviewed fixture")
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(json.dumps([entry]))
    args = [str(tmp_path), "--allowlist", str(allowlist)]
    assert guard.main(args) == 0
    (tmp_path / "writer.py").write_text(source + '    path.write_text("data")\n')
    assert guard.main(args) == 1  # a second identical sink is still new
    (tmp_path / "writer.py").write_text('def save(path):\n    pass\n')
    assert guard.main(args) == 1  # obsolete exemptions cannot silently survive


def test_invalid_source_fails_closed(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:")
    assert guard.main([str(tmp_path)]) == 1


def test_repository_has_zero_unlisted_atomic_writes():
    result = subprocess.run(
        [sys.executable, str(GUARD)], cwd=ROOT, capture_output=True,
        text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 unlisted atomic writes; 0 stale exceptions" in result.stdout
