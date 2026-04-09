"""Tests for `_version()` when package metadata is missing (file fallback and unknown sentinel)."""

from unittest.mock import MagicMock, patch

import py_bash as under_test


class TestVersionFallback:
    """Tests for `_version` exception-handling branches."""

    @patch("pathlib.Path.read_text", autospec=True, return_value="1.2.3\n")
    @patch.object(under_test, "version", autospec=True, side_effect=under_test.PackageNotFoundError)
    def test_given_package_not_found_without_oserror_then_reads_version_file(
        self, mock_version: MagicMock, mock_read_text: MagicMock
    ) -> None:
        # Given / When
        result = under_test._version()
        # Then
        assert result == "1.2.3"
        mock_version.assert_called_once_with("py_bash")
        mock_read_text.assert_called_once()

    @patch("pathlib.Path.read_text", autospec=True, side_effect=OSError("cannot read file"))
    @patch.object(under_test, "version", autospec=True, side_effect=under_test.PackageNotFoundError)
    def test_given_package_not_found_and_oserror_then_returns_unknown_version(
        self, mock_version: MagicMock, mock_read_text: MagicMock
    ) -> None:
        # Given / When
        result = under_test._version()
        # Then
        # An unreadable VERSION yields this exact sentinel for diagnostics.
        assert result == "0+unknown"
        mock_version.assert_called_once_with("py_bash")
        mock_read_text.assert_called_once()
