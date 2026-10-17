"""CA bundle selection and verified downloads through a real TLS connection."""

import shutil
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import certifi
import pytest

from siege_utilities.files import remote


@pytest.mark.parametrize("system", ["Linux", "Darwin"])
@pytest.mark.parametrize(
    "requests_bundle,curl_bundle,expected",
    [
        ("requests.pem", "curl.pem", "requests.pem"),
        (None, "curl.pem", "curl.pem"),
        ("", "curl.pem", "curl.pem"),
    ],
)
def test_ca_bundle_environment_precedes_platform_defaults(
    monkeypatch, system, requests_bundle, curl_bundle, expected,
):
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    if requests_bundle is not None:
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", requests_bundle)
    monkeypatch.setenv("CURL_CA_BUNDLE", curl_bundle)
    monkeypatch.setattr(remote.platform, "system", lambda: system)
    monkeypatch.setattr(remote.os.path, "exists", lambda path: True)

    assert remote._get_ssl_verify_path() == expected


def test_ca_bundle_defaults_to_certifi(monkeypatch):
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.setattr(remote.platform, "system", lambda: "Linux")

    assert remote._get_ssl_verify_path() == certifi.where()


@pytest.fixture
def private_ca_server(tmp_path):
    """Generate disposable keys; listen only on an ephemeral loopback port."""
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("Install openssl and put it on PATH to run the local TLS test")
    ca = tmp_path / "ca.pem"
    ca_key = tmp_path / "ca.key"
    cert = tmp_path / "server.pem"
    key = tmp_path / "server.key"
    csr = tmp_path / "server.csr"
    extensions = tmp_path / "server.ext"
    extensions.write_text(
        "subjectAltName=IP:127.0.0.1\n"
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
    )
    commands = [
        ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=Temporary Test CA", "-keyout", str(ca_key), "-out", str(ca),
         "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign"],
        ["req", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1",
         "-keyout", str(key), "-out", str(csr)],
        ["x509", "-req", "-in", str(csr), "-CA", str(ca), "-CAkey", str(ca_key),
         "-CAcreateserial", "-days", "1", "-extfile", str(extensions), "-out", str(cert)],
    ]
    for arguments in commands:
        subprocess.run([openssl, *arguments], check=True, capture_output=True, timeout=30)

    body = b"verified private CA download\n"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"https://127.0.0.1:{server.server_port}/payload", ca, body
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.integration
@pytest.mark.files
@pytest.mark.parametrize("bundle_variable", ["REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"])
@pytest.mark.parametrize("downloader", [remote.download_file, remote.download_file_with_retry])
def test_private_ca_download_verifies_without_insecure_retry(
    private_ca_server, tmp_path, monkeypatch, bundle_variable, downloader,
):
    url, ca, body = private_ca_server
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    monkeypatch.setenv(bundle_variable, str(ca))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    real_get = remote.requests.get
    verification = []

    def record_get(*args, **kwargs):
        verification.append(kwargs["verify"])
        return real_get(*args, **kwargs)

    monkeypatch.setattr(remote.requests, "get", record_get)
    destination = tmp_path / "download.bin"

    assert downloader(url, destination, verify_ssl=True) == str(destination)
    assert destination.read_bytes() == body
    assert verification == [str(ca)]
    assert False not in verification
