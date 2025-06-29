"""Tests for the blurb add command with automation features."""

import io
import os
import tempfile
from unittest import mock
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from blurb import blurb


class TestAddCommand:
    """Test cases for the add command's automation features."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Save original values
        self.original_dir = os.getcwd()
        self.original_root = blurb.root

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original values
        os.chdir(self.original_dir)
        blurb.root = self.original_root

    def test_add_help_parameter(self, capsys):
        """Test that --help displays the help text."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(help=True)

        # help exits with code 0
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Add a blurb" in captured.out
        assert "--gh_issue" in captured.out
        assert "--section" in captured.out
        assert "--rst_on_stdin" in captured.out

    def test_invalid_section_parameter(self, capsys):
        """Test that invalid section names are rejected."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(section="InvalidSection")

        # error() function exits with string message, not code
        assert "--section must be one of" in str(exc_info.value)
        assert "InvalidSection" in str(exc_info.value)

    def test_negative_gh_issue(self, capsys):
        """Test that negative GitHub issue numbers are rejected."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(gh_issue=-123)

        # error() function exits with string message, not code
        assert "--gh_issue must be a positive integer" in str(exc_info.value)

    def test_rst_on_stdin_requires_other_params(self, capsys):
        """Test that --rst_on_stdin requires --gh_issue and --section."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(rst_on_stdin=True)

        # error() function exits with string message, not code
        assert "--gh_issue and --section required with --rst_on_stdin" in str(exc_info.value)

    def test_rst_on_stdin_missing_section(self, capsys):
        """Test that --rst_on_stdin fails without --section."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(rst_on_stdin=True, gh_issue=12345)

        # error() function exits with string message, not code
        assert "--gh_issue and --section required with --rst_on_stdin" in str(exc_info.value)

    def test_rst_on_stdin_missing_gh_issue(self, capsys):
        """Test that --rst_on_stdin fails without --gh_issue."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(rst_on_stdin=True, section="Library")

        # error() function exits with string message, not code
        assert "--gh_issue and --section required with --rst_on_stdin" in str(exc_info.value)

    @mock.patch('blurb.blurb.chdir_to_repo_root')
    @mock.patch('blurb.blurb.flush_git_add_files')
    @mock.patch('sys.stdin', new_callable=io.StringIO)
    def test_add_with_all_automation_params(self, mock_stdin, mock_flush_git, mock_chdir, fs: FakeFilesystem):
        """Test successful add with all automation parameters."""
        # Set up fake filesystem
        fs.create_dir("/fake_repo")
        fs.create_dir("/fake_repo/Misc/NEWS.d/next/Library")
        os.chdir("/fake_repo")
        blurb.root = "/fake_repo"

        # Mock stdin content with a Monty Python reference
        mock_stdin.write("Fixed spam module to properly handle eggs, bacon, and spam repetition counts.")
        mock_stdin.seek(0)

        # Mock chdir_to_repo_root to do nothing since we're in fake fs
        mock_chdir.return_value = None

        # Call add with automation parameters
        with mock.patch('blurb.blurb.sortable_datetime', return_value='2024-01-01-12-00-00'):
            with mock.patch('blurb.blurb.nonceify', return_value='abc123'):
                result = blurb.add(
                    gh_issue=123456,
                    section="Library",
                    rst_on_stdin=True
                )

        # Verify the file was created
        expected_path = "/fake_repo/Misc/NEWS.d/next/Library/2024-01-01-12-00-00.gh-issue-123456.abc123.rst"
        assert os.path.exists(expected_path)

        # Verify file contents - the metadata is in the filename, not the file content
        with open(expected_path) as f:
            content = f.read()

        # The file should only contain the body text (which may be wrapped)
        assert "Fixed spam module to properly handle eggs, bacon, and spam repetition" in content
        assert "counts." in content

        # Verify git add was called
        assert expected_path in blurb.git_add_files
        mock_flush_git.assert_called_once()
