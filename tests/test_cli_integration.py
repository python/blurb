"""Integration tests for the blurb CLI tool."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def mock_cpython_repo(tmp_path):
    """Create a minimal mock CPython repository structure."""
    # Create necessary directories
    (tmp_path / "Include").mkdir()
    (tmp_path / "Python").mkdir()
    (tmp_path / "Misc" / "NEWS.d" / "next").mkdir(parents=True)

    # Create section directories
    sections = ["Library", "Tests", "Documentation", "Core_and_Builtins",
               "Build", "Windows", "macOS", "IDLE", "Tools-Demos", "C_API", "Security"]
    for section in sections:
        (tmp_path / "Misc" / "NEWS.d" / "next" / section).mkdir()

    # Create required files that identify a CPython repo
    (tmp_path / "README").write_text("This is Python version 3.12.0\n")
    (tmp_path / "LICENSE").write_text("A. HISTORY OF THE SOFTWARE\n==========================\n")
    (tmp_path / "Include" / "Python.h").touch()
    (tmp_path / "Python" / "ceval.c").touch()

    # Initialize as a git repository
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "brian@pythons.invalid"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Brian of Nazareth"], cwd=tmp_path, capture_output=True)

    yield tmp_path
    # Cleanup happens automatically when tmp_path fixture is torn down


@pytest.fixture
def blurb_executable():
    """Get the path to the blurb executable."""
    # Try to find blurb in the virtual environment
    venv_blurb = Path(__file__).parent.parent / "venv" / "bin" / "blurb"
    if venv_blurb.exists():
        return str(venv_blurb)

    # Fall back to using Python module
    return [sys.executable, "-m", "blurb"]


def run_blurb(blurb_executable, args, cwd=None, input_text=None):
    """Run blurb with the given arguments."""
    if isinstance(blurb_executable, str):
        cmd = [blurb_executable] + args
    else:
        cmd = blurb_executable + args

    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True
    )
    return result


class TestCLIIntegration:
    """Test the blurb command line interface with a mock CPython repo."""

    def test_blurb_add_help_in_mock_repo(self, mock_cpython_repo, blurb_executable):
        """Test that 'blurb add --help' works in a mock CPython repo."""
        # Run blurb add --help
        result = run_blurb(blurb_executable, ["add", "--help"], cwd=mock_cpython_repo)

        # Check it succeeded
        assert result.returncode == 0

        # Check the help output contains expected content
        output = result.stdout + result.stderr  # Help might go to either
        assert "Add a blurb" in output
        assert "--gh_issue" in output
        assert "--section" in output
        assert "--rst_on_stdin" in output
        assert "Library" in output  # Should show available sections

    def test_blurb_version(self, blurb_executable):
        """Test that 'blurb version' works without a CPython repo."""
        result = run_blurb(blurb_executable, ["version"])

        assert result.returncode == 0
        assert "blurb version" in result.stdout

    def test_blurb_help(self, blurb_executable):
        """Test that 'blurb help' works without a CPython repo."""
        result = run_blurb(blurb_executable, ["help"])

        assert result.returncode == 0
        assert "Available subcommands:" in result.stdout
        assert "add" in result.stdout
        assert "merge" in result.stdout
        assert "release" in result.stdout

    def test_blurb_add_automation_params_validation(self, mock_cpython_repo, blurb_executable):
        """Test validation of automation parameters via CLI."""
        # Test invalid section
        result = run_blurb(blurb_executable, ["add", "--section", "InvalidSection"], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert "must be one of" in result.stderr

        # Test negative gh_issue
        result = run_blurb(blurb_executable, ["add", "--gh_issue", "-123"], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert "must be a positive integer" in result.stderr

        # Test rst_on_stdin without required params
        result = run_blurb(blurb_executable, ["add", "--rst_on_stdin"], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert "--gh_issue and --section required" in result.stderr

    @pytest.mark.parametrize("section", ["Library", "Tests", "Documentation"])
    def test_blurb_add_with_stdin_integration(self, mock_cpython_repo, blurb_executable, section):
        """Test the full automation flow with stdin input."""
        # Create the blurb content
        blurb_text = f"Fixed a bug in the {section.lower()} that improves spam handling."

        # Run blurb with all automation parameters
        result = run_blurb(
            blurb_executable,
            ["add", "--gh_issue", "123456", "--section", section, "--rst_on_stdin"],
            cwd=mock_cpython_repo,
            input_text=blurb_text
        )

        # Check it succeeded
        assert result.returncode == 0
        assert "Ready for commit" in result.stdout
        assert "created and git added" in result.stdout

        # Verify the file was created
        news_dir = mock_cpython_repo / "Misc" / "NEWS.d" / "next" / section
        rst_files = list(news_dir.glob("*.gh-issue-123456.*.rst"))
        assert len(rst_files) == 1

        # Verify the content
        created_file = rst_files[0]
        content = created_file.read_text()
        assert blurb_text in content

    def test_blurb_outside_cpython_repo(self, blurb_executable, tmp_path):
        """Test that blurb gives appropriate error outside a CPython repo."""
        # Create a non-CPython directory
        non_cpython_dir = tmp_path / "not_cpython"
        non_cpython_dir.mkdir()

        # Try to run blurb add
        result = run_blurb(blurb_executable, ["add"], cwd=non_cpython_dir)

        assert result.returncode != 0
        assert "not inside a CPython repo" in result.stderr
