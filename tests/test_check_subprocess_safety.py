"""Behavior tests for the subprocess AST class guard."""

import pytest

from scripts.check_subprocess_safety import main, scan_file


@pytest.mark.parametrize("source, label", [
    ('import subprocess\nsubprocess.run("cmd", shell=True)', 'subprocess.run'),
    ('import subprocess as sp\nsp.call("cmd", shell=True)', 'subprocess.call'),
    ('from subprocess import Popen\nPopen("cmd", shell=True)', 'subprocess.Popen'),
    ('from subprocess import check_output as run\nrun("cmd", shell=True)', 'subprocess.check_output'),
    ('import subprocess\nsubprocess.Popen("cmd", shell=enabled)', 'subprocess.Popen'),
    ('import subprocess\nsubprocess.run("cmd", shell=1)', 'subprocess.run'),
    ('import os\nos.system("cmd")', 'os.system'),
    ('import os as platform\nplatform.popen("cmd")', 'os.popen'),
    ('from os import system as execute\nexecute("cmd")', 'os.system'),
    ('from os import popen\npopen("cmd")', 'os.popen'),
    ('import subprocess\nsubprocess.getoutput("cmd")', 'subprocess.getoutput'),
    ('import subprocess\nsubprocess.getstatusoutput("cmd")', 'subprocess.getstatusoutput'),
    ('import subprocess as sp\nsp.getoutput("cmd")', 'subprocess.getoutput'),
    ('import subprocess as sp\nsp.getstatusoutput("cmd")', 'subprocess.getstatusoutput'),
    ('from subprocess import getoutput as run\nrun("cmd")', 'subprocess.getoutput'),
    ('from subprocess import getstatusoutput as run\nrun("cmd")', 'subprocess.getstatusoutput'),
    ('import asyncio\nasyncio.create_subprocess_shell("cmd")', 'asyncio.create_subprocess_shell'),
    ('import asyncio as aio\naio.create_subprocess_shell("cmd")', 'asyncio.create_subprocess_shell'),
    ('from asyncio import create_subprocess_shell as run\nrun("cmd")', 'asyncio.create_subprocess_shell'),
    ('from os import spawnlp as run\nrun(0, "sh", "sh", "-c", "cmd")', 'os.spawnlp'),
    ('import os as platform\nplatform.execvp("sh", ["sh", "-c", "cmd"])', 'os.execvp'),
])
def test_forbidden_call_fails_guard(tmp_path, capsys, source, label):
    path = tmp_path / 'module.py'
    path.write_text(source)
    assert main([str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert f'module.py:2: {label}' in output
    assert 'FAIL: 1 subprocess safety violation(s) in 1 files' in output


@pytest.mark.parametrize('family', ['spawn', 'exec'])
@pytest.mark.parametrize('suffix', ['l', 'le', 'lp', 'lpe', 'v', 've', 'vp', 'vpe'])
def test_low_level_process_family_fails_guard(tmp_path, family, suffix):
    path = tmp_path / 'module.py'
    name = f'os.{family}{suffix}'
    path.write_text(f'import os\n{name}(*args)')
    assert scan_file(path) == [(2, f'{name} is forbidden; use argv execution')]


def test_argv_calls_and_quoted_examples_pass_guard(tmp_path, capsys):
    path = tmp_path / 'module.py'
    path.write_text('''
import subprocess as sp
import asyncio as aio
from subprocess import Popen
sp.run(["echo", "ok"], shell=False)
Popen(["echo", "ok"])
aio.create_subprocess_exec("echo", "ok")
# os.system("cmd")
example = 'subprocess.run("cmd", shell=True)'
''')
    assert main([str(tmp_path)]) == 0
    assert 'PASS: 0 subprocess safety violation(s) in 1 files' in capsys.readouterr().out


def test_nested_library_sources_are_scanned(tmp_path):
    nested = tmp_path / 'package'
    nested.mkdir()
    (nested / 'module.py').write_text('import os\nos.popen("cmd")')
    assert main([str(tmp_path)]) == 1


def test_invalid_source_raises_instead_of_passing(tmp_path):
    path = tmp_path / 'broken.py'
    path.write_text('def broken(')
    with pytest.raises(SyntaxError, match='never closed'):
        main([str(tmp_path)])


def test_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_file(tmp_path / 'missing.py')


def test_empty_tree_raises_instead_of_passing(tmp_path):
    with pytest.raises(ValueError, match='No Python sources found'):
        main([str(tmp_path)])
