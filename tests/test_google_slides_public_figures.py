"""#1450: every anyone-with-link permission created for a report figure must be
revoked (or the Drive file deleted) after createImage, including when the
insert fails; figures go to the caller's folder; exposure is documented.

Fully offline: fake Drive/Slides services, fake figure, stubbed MediaFileUpload.
"""
import re
import sys
import types
from types import SimpleNamespace

import pytest

from siege_utilities.analytics import google_slides
from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient


class _Call:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeDrive:
    def __init__(self, events):
        self.events = events
        self.n = 0

    def files(self):
        drive = self

        class Files:
            def create(self, body=None, media_body=None, fields=None, **kw):
                def run():
                    drive.n += 1
                    fid = f"file{drive.n}"
                    drive.events.append(("files.create", fid, dict(body or {})))
                    return {"id": fid}
                return _Call(run)

            def delete(self, fileId=None, **kw):
                return _Call(lambda: drive.events.append(("files.delete", fileId, kw)) or {})

            def get(self, fileId=None, **kw):
                return _Call(lambda: {"parents": ["root"], "permissions": []})

            def update(self, fileId=None, **kw):
                return _Call(lambda: drive.events.append(("files.update", fileId, kw)) or {"id": fileId})

        return Files()

    def permissions(self):
        drive = self

        class Perms:
            def create(self, fileId=None, body=None, **kw):
                def run():
                    drive.events.append(("permissions.create", fileId, dict(body or {})))
                    return {"id": f"perm-{fileId}"}
                return _Call(run)

            def delete(self, fileId=None, permissionId=None, **kw):
                return _Call(lambda: drive.events.append(
                    ("permissions.delete", fileId, {"permissionId": permissionId})) or {})

        return Perms()


class FakeSlides:
    def __init__(self, events, fail_create_image=False):
        self.events = events
        self.fail_create_image = fail_create_image

    def presentations(self):
        slides = self

        class Pres:
            def create(self, body=None):
                return _Call(lambda: {"presentationId": "PRES"})

            def batchUpdate(self, presentationId=None, body=None):
                def run():
                    for r in (body or {}).get("requests", []):
                        if "createImage" in r:
                            slides.events.append(("createImage", r["createImage"]["url"], {}))
                            if slides.fail_create_image:
                                raise RuntimeError("synthetic createImage failure")
                    return {"replies": []}
                return _Call(run)

        return Pres()


class FakeFigure:
    def savefig(self, path, **kw):
        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nrv-dummy")


@pytest.fixture(autouse=True)
def _stub_media_upload(monkeypatch):
    http = types.ModuleType("googleapiclient.http")
    http.MediaFileUpload = lambda *a, **k: SimpleNamespace(args=a, kwargs=k)
    pkg = sys.modules.get("googleapiclient") or types.ModuleType("googleapiclient")
    monkeypatch.setitem(sys.modules, "googleapiclient", pkg)
    monkeypatch.setitem(sys.modules, "googleapiclient.http", http)


def _client(events, fail_create_image=False):
    client = object.__new__(GoogleWorkspaceClient)
    client._credentials = None
    client._services = {
        "drive:v3": FakeDrive(events),
        "slides:v1": FakeSlides(events, fail_create_image),
    }
    return client


def _argument():
    return SimpleNamespace(
        headline="H", narrative="N", table=None, chart=FakeFigure(),
        map_figure=None, layout="side_by_side", base_note=None, source_note=None,
    )


def _assert_every_public_grant_revoked(events):
    grants = [(i, e) for i, e in enumerate(events)
              if e[0] == "permissions.create" and e[2].get("type") == "anyone"]
    assert grants, "fixture sanity: expected the figure path to publish at least once"
    for i, (_, fid, _) in grants:
        revoked = any(
            (kind in ("files.delete", "permissions.delete")) and f == fid
            for kind, f, _ in events[i + 1:]
        )
        assert revoked, f"anyone-permission on {fid} never revoked/deleted: {events}"


def test_public_figure_permission_is_revoked_after_create_image():
    events = []
    google_slides.create_report_from_arguments(_client(events), "T", [_argument()], folder_id="FOLDER")
    _assert_every_public_grant_revoked(events)
    first_image = next(i for i, e in enumerate(events) if e[0] == "createImage")
    last_cleanup = max(i for i, e in enumerate(events)
                       if e[0] in ("files.delete", "permissions.delete"))
    assert last_cleanup > first_image  # revoke only after Slides copied the image


def test_public_figure_permission_is_revoked_when_insert_fails():
    events = []
    with pytest.raises(RuntimeError):
        google_slides.create_report_from_arguments(
            _client(events, fail_create_image=True), "T", [_argument()], folder_id="FOLDER")
    _assert_every_public_grant_revoked(events)


def test_figure_upload_goes_to_caller_folder_not_drive_root():
    events = []
    google_slides.create_report_from_arguments(_client(events), "T", [_argument()], folder_id="FOLDER")
    pngs = [e for e in events if e[0] == "files.create" and str(e[2].get("name", "")).endswith(".png")]
    assert pngs
    for _, fid, body in pngs:
        assert body.get("parents") == ["FOLDER"], f"{fid} uploaded to Drive root: {body}"


def test_public_exposure_is_documented_on_entry_point():
    doc = google_slides.create_report_from_arguments.__doc__ or ""
    assert re.search(r"anyone|public", doc, re.I), "public-link step not documented"


# --- Additional #1450 tests (implementer): opt-out and cleanup-failure paths ---

import logging


class _DeleteFailsDrive(FakeDrive):
    def files(self):
        files = super().files()

        def delete(fileId=None, **kw):
            def run():
                self.events.append(("files.delete.failed", fileId, kw))
                raise RuntimeError("synthetic Drive delete failure")
            return _Call(run)

        files.delete = delete
        return files


class _PublishFailsDrive(FakeDrive):
    def permissions(self):
        perms = super().permissions()

        def create(fileId=None, body=None, **kw):
            def run():
                raise RuntimeError("synthetic permission failure")
            return _Call(run)

        perms.create = create
        return perms


def _client_with_drive(drive, events, fail_create_image=False):
    client = _client(events, fail_create_image)
    client._services["drive:v3"] = drive
    return client


def test_publish_figures_false_creates_no_anyone_permission():
    events = []
    pres_id = google_slides.create_report_from_arguments(
        _client(events), "T", [_argument()], folder_id="FOLDER", publish_figures=False)
    assert pres_id == "PRES"
    assert not [e for e in events if e[0] == "permissions.create"], events
    assert not [e for e in events
                if e[0] == "files.create" and str(e[2].get("name", "")).endswith(".png")], events
    assert not [e for e in events if e[0] == "createImage"], events


def test_cleanup_failure_does_not_mask_insert_error(caplog):
    events = []
    client = _client_with_drive(_DeleteFailsDrive(events), events, fail_create_image=True)
    with caplog.at_level(logging.ERROR, logger=google_slides.__name__):
        with pytest.raises(RuntimeError, match="synthetic createImage failure"):
            google_slides.create_report_from_arguments(client, "T", [_argument()], folder_id="FOLDER")
    assert any(r.levelno == logging.ERROR and "file1" in r.getMessage()
               and "anyone with the link" in r.getMessage() for r in caplog.records)


def test_cleanup_failure_after_successful_insert_is_raised(caplog):
    events = []
    client = _client_with_drive(_DeleteFailsDrive(events), events)
    with caplog.at_level(logging.ERROR, logger=google_slides.__name__):
        with pytest.raises(RuntimeError, match="file1"):
            google_slides.create_report_from_arguments(client, "T", [_argument()], folder_id="FOLDER")
    assert any(r.levelno == logging.ERROR and "file1" in r.getMessage() for r in caplog.records)


def test_file_is_deleted_when_publishing_fails():
    events = []
    client = _client_with_drive(_PublishFailsDrive(events), events)
    with pytest.raises(RuntimeError):
        google_slides.create_report_from_arguments(client, "T", [_argument()], folder_id="FOLDER")
    assert ("files.delete", "file1", {}) in events, events
    assert not [e for e in events if e[0] == "createImage"], events


def test_http_error_from_insert_is_wrapped_and_figure_deleted(monkeypatch):
    errors = types.ModuleType("googleapiclient.errors")

    class HttpError(Exception):
        pass

    errors.HttpError = HttpError
    monkeypatch.setitem(sys.modules, "googleapiclient.errors", errors)

    events = []
    client = _client(events)

    def failing_batch_update(presentation_id, requests):
        if any("createImage" in r for r in requests):
            raise HttpError("403 from Slides")
        return {"replies": []}

    monkeypatch.setattr(client, "batch_update_presentation", failing_batch_update)
    with pytest.raises(RuntimeError, match="slides failed") as info:
        google_slides.create_report_from_arguments(client, "T", [_argument()], folder_id="FOLDER")
    assert "Figure upload/insert failed" in str(info.value)
    _assert_every_public_grant_revoked(events)
