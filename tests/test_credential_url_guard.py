"""Blocking package-wide credential URL guard, including injected leak proofs."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_credential_urls import (
    ALLOWLIST,
    credential_url_sites,
    scan_tree,
    unreviewed_sites,
)


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = [
    "key", "password", "access_token", "token", "apiKey", "api_key",
    "APIKEY", "client_secret", "secret", "sig", "X-Amz-Signature", "auth",
    "Signature", "X-Goog-Signature", "X-Amz-Security-Token",
]


def test_no_unreviewed_credential_urls():
    findings = unreviewed_sites(ROOT / "siege_utilities")
    assert not findings, "Unreviewed credential URL sites:\n" + "\n".join(map(str, findings))


def test_credential_url_allowlist_is_specific_and_current():
    identities = {site.identity for site in scan_tree(ROOT / "siege_utilities")}
    assert set(ALLOWLIST) <= identities, "Remove stale URL exemptions"
    assert all(reason.strip() for reason in ALLOWLIST.values())


@pytest.mark.parametrize("parameter", PARAMETERS)
@pytest.mark.parametrize("construction", ["fstring", "urlencode", "params"])
def test_guard_rejects_injected_leak(tmp_path, parameter, construction):
    if construction == "fstring":
        build = f'url = f"https://h/p?{parameter}={{credential}}"'
    elif construction == "urlencode":
        build = f'params = {{"{parameter}": credential}}\n    url = "https://h/p?" + urlencode(params)'
    else:
        build = f'requests.get("https://h/p", params={{"{parameter}": credential}})'
    source = (
        "def fetch(credential):\n"
        f"    {build}\n"
        "    try:\n"
        "        requests.get(url).raise_for_status()\n"
        "    except Exception as e:\n"
        "        log.warning(f'failed: {e}')\n"
        "        raise RuntimeError(f'failed: {e}') from e\n"
    )
    injected = tmp_path / "geo/providers/_injected_leak.py"
    injected.parent.mkdir(parents=True)
    injected.write_text(source)
    findings = unreviewed_sites(tmp_path)
    assert len(findings) == 1
    assert findings[0].path == "geo/providers/_injected_leak.py"
    assert findings[0].parameters == (parameter.lower(),)
    injected.unlink()
    assert unreviewed_sites(tmp_path) == []


@pytest.mark.parametrize("build", [
    'params = dict(apiKey=credential)\nurl = urlencode(params)',
    'params = {}\nparams["apiKey"] = credential\nurl = urlencode(params)',
    'params = {}\nparams.update({"apiKey": credential})\nurl = urlencode(params)',
    'params = {}\nparams.update(apiKey=credential)\nurl = urlencode(params)',
    'params = {"apiKey": credential}\nother = params\nurl = urlencode(other)',
    'params = {"apiKey": credential}\nurl = urlencode({**params, "x": 1})',
    'url = urlencode({"apiKey": credential})',
    'url = urlencode(query={"apiKey": credential})',
    'url = urlencode([("apiKey", credential)])',
    'url = f"https://h/p?%61piKey={credential}"',
    'url = "https://h/p?apiKey=" + credential',
    'url = "https://h/p?apiKey={}".format(credential)',
    'from urllib.parse import urlencode as encode\nurl = encode({"apiKey": credential})',
    'def fetch():\n    log.warning(f"https://h/p?apiKey={credential}")',
    'params = dict(apiKey=credential)\nrequests.get(url, params=params)',
    'params = {}\nparams["apiKey"] = credential\nsession.post(url, params=params)',
    'params = {}\nparams.update({"apiKey": credential})\nsession.head(url, params=params)',
    'params = {}\nparams.update(apiKey=credential)\nsession.put(url, params=params)',
    'params = {"apiKey": credential}\nother = params\nsession.delete(url, params=other)',
    'params = {"apiKey": credential}\nsession.patch(url, params={**params, "x": 1})',
    'session.options(url, params=[("apiKey", credential)])',
    'session.request("GET", url, params={"apiKey": credential})',
    'from requests import get as fetch\nfetch(url, params={"apiKey": credential})',
    'url = f"https://h/cb#apiKey={credential}"',
    'url = f"https://h/p?next=https%3A%2F%2Fx%3FapiKey%3D{credential}"',
])
def test_guard_tracks_query_construction_variants(build):
    sites = credential_url_sites(build, "client.py")
    assert len(sites) == 1
    assert sites[0].parameters == ("apikey",)


@pytest.mark.parametrize("build", [
    'session.get(url, params=_auth(pw))',
    'self._session.get(url, params=self._auth_params(url))',
    'params = dict(self._auth_params(url))\nparams["state"] = "VA"\nsession.get(url, params=params)',
    'params = _auth(pw)\nalias = params\nsession.get(url, params=alias)',
    'session.get(url, params=params)',
    'session.get(url, params={key: value})',
    'session.get(url, params={**_auth(pw), "state": "VA"})',
    'session.get(url, params={k: v for k, v in data.items()})',
    'session.get(url, params=params if params else None)',
    'def forward(params):\n    session.get(url, params=params)\ndef unrelated():\n    params = {"state": "VA"}',
])
def test_guard_requires_review_for_unresolved_params(build):
    sites = credential_url_sites(build, "client.py")
    assert len(sites) == 1
    assert sites[0].parameters == ("<unresolved params>",)


def test_guard_ignores_comments_docstrings_and_nonsecret_parameters():
    source = '''"""Example: https://h/p?key={credential}"""
# url = f"https://h/p?password={credential}"
params = {"state": "17"}
url = f"https://h/p?{urlencode(params)}"
requests.get(url, params=params)
session.get(url, params=None)
session.get(url, params={})
session.post(url, params=dict(state="VA"))
'''
    assert credential_url_sites(source, "client.py") == []


@pytest.mark.parametrize("source, parameter", [
    ('url = f"https://h/p?access_token={credential}"\nlog.warning(url)\n', "access_token"),
    ('requests.get("https://x/y", params={"api_key": k})', "api_key"),
    ('url = f"https://h/p?Signature={s}"', "signature"),
    ('session.get(url, params=_auth(pw))', "<unresolved params>"),
])
def test_guard_cli_fails_on_injected_file_and_passes_after_removal(tmp_path, source, parameter):
    injected = tmp_path / "_injected_leak.py"
    injected.write_text(source)
    command = [sys.executable, str(ROOT / "scripts/check_credential_urls.py"), str(tmp_path)]
    leaked = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert leaked.returncode == 1
    assert "_injected_leak.py:1" in leaked.stdout
    assert parameter in leaked.stdout
    injected.unlink()
    clean = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert clean.returncode == 0
    assert "0 unreviewed sites" in clean.stdout


def test_guard_allowlist_does_not_cover_a_new_file(tmp_path):
    injected = tmp_path / "_injected_leak.py"
    injected.write_text('class CensusAPI:\n    def _build_url(self):\n        return f"&key={self.api_key}"\n')
    assert len(unreviewed_sites(tmp_path)) == 1
