"""Error-path tests for siege_utilities.economic.bls.qcew (SU-4b)."""

import zipfile

import pytest

try:
    from siege_utilities.economic.bls.qcew import QCEWFiles
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or requests not available")


class TestQCEWDownloadErrors:
    """Error paths for QCEWFiles.download."""

    def test_empty_zip_raises(self, tmp_path):
        """Zip file with no CSV inside must raise ValueError."""
        qcew = QCEWFiles(cache_dir=tmp_path)
        zip_path = tmp_path / "9999_qtrly_singlefile.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "no csv here")

        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.content = zip_path.read_bytes()
        mock_resp.raise_for_status = MagicMock()

        with patch("siege_utilities.economic.bls.qcew.requests.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="No CSV found"):
                qcew.download(9999)
