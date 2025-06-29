"""Integration tests for the blurb CLI tool."""

import os
import subprocess
import sys
from pathlib import Path
import pytest
import shutil


@pytest.fixture
def mock_cpython_repo(tmp_path):
    """Create a minimal mock CPython repository structure."""
    # Core directories
    (tmp_path / "Include").mkdir()
    (tmp_path / "Python").mkdir()
    (tmp_path / "Misc" / "NEWS.d" / "next").mkdir(parents=True)

    # Section directories
    sections = ["Library", "Tests", "Documentation", "Core_and_Builtins",
               "Build", "Windows", "macOS", "IDLE", "Tools-Demos", "C_API", "Security"]
    for section in sections:
        (tmp_path / "Misc" / "NEWS.d" / "next" / section).mkdir()

    # Required files for CPython repo identification
    (tmp_path / "README").write_text("This is Python version 3.12.0\n")
    (tmp_path / "LICENSE").write_text("A. HISTORY OF THE SOFTWARE\n==========================\n")
    (tmp_path / "Include" / "Python.h").touch()
    (tmp_path / "Python" / "ceval.c").touch()

    # Git setup
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "brian@pythons.invalid"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Brian of Nazareth"], cwd=tmp_path, capture_output=True)

    yield tmp_path


@pytest.fixture
def mock_cpython_with_blurbs(mock_cpython_repo):
    """Mock CPython repo with existing blurb files."""
    library_blurb = mock_cpython_repo / "Misc/NEWS.d/next/Library/2024-01-01-12-00-00.gh-issue-100000.abc123.rst"
    library_blurb.write_text("Fixed spam module to handle eggs properly.")

    tests_blurb = mock_cpython_repo / "Misc/NEWS.d/next/Tests/2024-01-02-13-00-00.gh-issue-100001.def456.rst"
    tests_blurb.write_text("Added tests for the spam module.")

    version_file = mock_cpython_repo / "Misc/NEWS.d/3.12.0.rst"
    version_file.write_text(""".. date: 2024-01-01
.. gh-issue: 100002
.. nonce: xyz789
.. release date: 2024-01-01
.. section: Library

Previous release notes.
""")
    return mock_cpython_repo


@pytest.fixture
def blurb_executable():
    """Get the command line to run the blurb executable."""
    return [sys.executable, "-m", "blurb"]


def run_blurb(blurb_executable, args, cwd=None, input_text=None):
    """Run blurb with the given arguments."""
    cmd = [blurb_executable] + args if isinstance(blurb_executable, str) else blurb_executable + args
    return subprocess.run(cmd, cwd=cwd, input=input_text, capture_output=True, text=True)


class TestBasicCommands:
    """Test basic CLI functionality and help."""

    @pytest.mark.parametrize("cmd,expected", [
        (["version"], "blurb version"),
        (["help"], "Commands"),
        (["-h"], "Commands"),
    ])
    def test_info_commands(self, blurb_executable, cmd, expected):
        result = run_blurb(blurb_executable, cmd)
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert expected in output

    @pytest.mark.parametrize("subcommand", ["add", "merge", "release", "populate", "export"])
    def test_help_subcommands(self, blurb_executable, subcommand):
        result = run_blurb(blurb_executable, ["help", subcommand])
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert subcommand in output.lower()

    def test_invalid_subcommand(self, blurb_executable):
        result = run_blurb(blurb_executable, ["invalid_command"])
        assert result.returncode != 0
        # With cyclopts, invalid commands show "Unused Tokens" error
        output = result.stdout + result.stderr
        assert "Unused Tokens" in output

    def test_outside_cpython_repo(self, blurb_executable, tmp_path):
        non_cpython_dir = tmp_path / "not_cpython"
        non_cpython_dir.mkdir()
        result = run_blurb(blurb_executable, ["add"], cwd=non_cpython_dir)
        assert result.returncode != 0
        assert "not inside a CPython repo" in result.stderr


class TestAddCommand:
    """Test the add command functionality."""

    def test_help_content(self, mock_cpython_repo, blurb_executable):
        result = run_blurb(blurb_executable, ["add", "--help"], cwd=mock_cpython_repo)
        assert result.returncode == 0
        output = result.stdout + result.stderr
        required_content = ["Add a new Misc/NEWS entry", "--gh-issue", "--section", "--rst-on-stdin", "Library"]
        assert all(content in output for content in required_content)

    @pytest.mark.parametrize("args,error_text", [
        (["--section", "InvalidSection"], "must be one of"),
        (["--gh-issue", "-123"], "must be a positive integer"),
        (["--rst-on-stdin"], "--gh-issue and --section required"),
    ])
    def test_validation_errors(self, mock_cpython_repo, blurb_executable, args, error_text):
        result = run_blurb(blurb_executable, ["add"] + args, cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert error_text in result.stderr

    @pytest.mark.parametrize("section", ["Library", "Tests", "Documentation"])
    def test_stdin_automation(self, mock_cpython_repo, blurb_executable, section):
        blurb_text = f"Fixed a bug in the {section.lower()} that improves spam handling."
        result = run_blurb(
            blurb_executable,
            ["add", "--gh-issue", "123456", "--section", section, "--rst-on-stdin"],
            cwd=mock_cpython_repo,
            input_text=blurb_text
        )
        assert result.returncode == 0
        assert "Ready for commit" in result.stdout

        news_dir = mock_cpython_repo / "Misc" / "NEWS.d" / "next" / section
        rst_files = list(news_dir.glob("*.gh-issue-123456.*.rst"))
        assert len(rst_files) == 1
        assert blurb_text in rst_files[0].read_text()

    def test_default_behavior(self, mock_cpython_repo, blurb_executable, monkeypatch):
        monkeypatch.setenv("EDITOR", "true")
        result = run_blurb(blurb_executable, [], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert "Blurb 'body' text must not be empty!" in result.stdout or "EOFError" in result.stderr


class TestMergeCommand:
    """Test merge functionality and options."""

    def test_basic_merge(self, mock_cpython_with_blurbs, blurb_executable):
        result = run_blurb(blurb_executable, ["merge"], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0

        news_file = mock_cpython_with_blurbs / "Misc/NEWS"
        assert news_file.exists()
        content = news_file.read_text()
        assert "Fixed spam module" in content
        assert "Added tests for the spam module" in content

    def test_custom_output(self, mock_cpython_with_blurbs, blurb_executable):
        result = run_blurb(blurb_executable, ["merge", "custom_news.txt"], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0

        custom_file = mock_cpython_with_blurbs / "custom_news.txt"
        assert custom_file.exists()
        assert "Fixed spam module" in custom_file.read_text()

    @pytest.mark.parametrize("force_flag", ["--forced", "-f"])
    def test_forced_overwrite(self, mock_cpython_with_blurbs, blurb_executable, force_flag):
        news_file = mock_cpython_with_blurbs / "Misc/NEWS"
        news_file.write_text("Old content")

        result = run_blurb(blurb_executable, ["merge", force_flag], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0

        content = news_file.read_text()
        assert "Old content" not in content
        assert "Fixed spam module" in content

    def test_no_blurbs_error(self, tmp_path, blurb_executable):
        # Create a minimal CPython repo with empty NEWS.d (no next directories)
        (tmp_path / "Include").mkdir()
        (tmp_path / "Python").mkdir()
        (tmp_path / "Misc" / "NEWS.d").mkdir(parents=True)

        # Required files for CPython repo identification
        (tmp_path / "README").write_text("This is Python version 3.12.0\n")
        (tmp_path / "LICENSE").write_text("A. HISTORY OF THE SOFTWARE\n==========================\n")
        (tmp_path / "Include" / "Python.h").touch()
        (tmp_path / "Python" / "ceval.c").touch()

        result = run_blurb(blurb_executable, ["merge"], cwd=tmp_path)
        assert result.returncode != 0
        assert "don't have ANY blurbs" in result.stderr


class TestReleaseCommand:
    """Test release management functionality."""

    def test_version_release(self, mock_cpython_with_blurbs, blurb_executable):
        result = run_blurb(blurb_executable, ["release", "3.12.1"], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0

        version_file = mock_cpython_with_blurbs / "Misc/NEWS.d/3.12.1.rst"
        assert version_file.exists()

        # Verify blurbs were moved
        library_dir = mock_cpython_with_blurbs / "Misc/NEWS.d/next/Library"
        tests_dir = mock_cpython_with_blurbs / "Misc/NEWS.d/next/Tests"
        assert not list(library_dir.glob("*.rst"))
        assert not list(tests_dir.glob("*.rst"))

    def test_dot_version(self, mock_cpython_with_blurbs, blurb_executable):
        versioned_dir = mock_cpython_with_blurbs.parent / "3.12.2"
        shutil.move(str(mock_cpython_with_blurbs), str(versioned_dir))

        result = run_blurb(blurb_executable, ["release", "."], cwd=versioned_dir)
        assert result.returncode == 0

        version_file = versioned_dir / "Misc/NEWS.d/3.12.2.rst"
        assert version_file.exists()

    def test_missing_version_error(self, mock_cpython_repo, blurb_executable):
        result = run_blurb(blurb_executable, ["release"], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert any(word in result.stdout.lower() for word in ["requires", "missing", "expected"])

    def test_too_many_args_error(self, mock_cpython_repo, blurb_executable):
        result = run_blurb(blurb_executable, ["release", "arg1", "arg2"], cwd=mock_cpython_repo)
        assert result.returncode != 0
        assert any(word in result.stdout.lower() for word in ["unused", "too many"])


class TestMaintenanceCommands:
    """Test populate and export commands."""

    def test_populate_structure(self, mock_cpython_repo, blurb_executable):
        shutil.rmtree(mock_cpython_repo / "Misc/NEWS.d")

        result = run_blurb(blurb_executable, ["populate"], cwd=mock_cpython_repo)
        assert result.returncode == 0

        news_d = mock_cpython_repo / "Misc/NEWS.d"
        assert news_d.exists()
        assert (news_d / "next").exists()

        for section in ["Library", "Tests", "Documentation"]:
            section_dir = news_d / "next" / section
            assert section_dir.exists()
            readme = section_dir / "README.rst"
            assert readme.exists()
            assert section in readme.read_text()

    def test_populate_idempotent(self, mock_cpython_with_blurbs, blurb_executable):
        library_blurb = mock_cpython_with_blurbs / "Misc/NEWS.d/next/Library/2024-01-01-12-00-00.gh-issue-100000.abc123.rst"
        initial_content = library_blurb.read_text()

        result = run_blurb(blurb_executable, ["populate"], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0
        assert library_blurb.read_text() == initial_content

    def test_export_removes_directory(self, mock_cpython_with_blurbs, blurb_executable):
        news_d = mock_cpython_with_blurbs / "Misc/NEWS.d"
        assert news_d.exists()

        result = run_blurb(blurb_executable, ["export"], cwd=mock_cpython_with_blurbs)
        assert result.returncode == 0
        assert not news_d.exists()

    def test_export_missing_directory_ok(self, mock_cpython_repo, blurb_executable):
        news_d = mock_cpython_repo / "Misc/NEWS.d"
        shutil.rmtree(news_d)

        result = run_blurb(blurb_executable, ["export"], cwd=mock_cpython_repo)
        assert result.returncode == 0
