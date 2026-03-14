"""Tests for siege_utilities.reporting.image_utils module."""

import base64
from pathlib import Path
from unittest.mock import MagicMock
from siege_utilities.reporting.image_utils import decode_rl_image, save_rl_image


class TestDecodeRlImage:
    """Tests for decode_rl_image."""

    def test_valid_base64_image(self):
        raw_bytes = b"fake PNG data"
        b64 = base64.b64encode(raw_bytes).decode()
        mock_img = MagicMock()
        mock_img.filename = f"data:image/png;base64,{b64}"
        result = decode_rl_image(mock_img)
        assert result == raw_bytes

    def test_non_data_uri_returns_none(self):
        mock_img = MagicMock()
        mock_img.filename = "/path/to/image.png"
        result = decode_rl_image(mock_img)
        assert result is None

    def test_no_filename_attr_returns_none(self):
        result = decode_rl_image("not an image object")
        assert result is None

    def test_none_filename_returns_none(self):
        mock_img = MagicMock()
        mock_img.filename = None
        result = decode_rl_image(mock_img)
        assert result is None

    def test_non_string_filename_returns_none(self):
        mock_img = MagicMock()
        mock_img.filename = 12345
        result = decode_rl_image(mock_img)
        assert result is None


class TestSaveRlImage:
    """Tests for save_rl_image."""

    def test_save_valid_image(self, tmp_path):
        raw_bytes = b"fake PNG data for saving"
        b64 = base64.b64encode(raw_bytes).decode()
        mock_img = MagicMock()
        mock_img.filename = f"data:image/png;base64,{b64}"

        out_path = tmp_path / "output.png"
        result = save_rl_image(mock_img, out_path)
        assert result == out_path
        assert out_path.exists()
        assert out_path.read_bytes() == raw_bytes

    def test_save_non_image_returns_path(self, tmp_path):
        mock_img = MagicMock()
        mock_img.filename = "/not/a/data/uri.png"

        out_path = tmp_path / "output.png"
        result = save_rl_image(mock_img, out_path)
        assert result == out_path
        assert not out_path.exists()

    def test_creates_parent_dirs(self, tmp_path):
        raw_bytes = b"data"
        b64 = base64.b64encode(raw_bytes).decode()
        mock_img = MagicMock()
        mock_img.filename = f"data:image/png;base64,{b64}"

        out_path = tmp_path / "nested" / "dir" / "output.png"
        save_rl_image(mock_img, out_path)
        assert out_path.exists()

    def test_string_path_accepted(self, tmp_path):
        raw_bytes = b"data"
        b64 = base64.b64encode(raw_bytes).decode()
        mock_img = MagicMock()
        mock_img.filename = f"data:image/png;base64,{b64}"

        out_path = str(tmp_path / "output.png")
        save_rl_image(mock_img, out_path)
        assert Path(out_path).exists()
