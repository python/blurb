import io
import os
import re
import sys
import tempfile
from unittest import mock

import pytest

from blurb import blurb


def test_valid_no_issue_number():
    assert blurb._extract_issue_number(None) is None


@pytest.mark.parametrize('issue', [
    # issue given by their number
    '12345',
    '12345 ',
    ' 12345',
    ' 12345 ',
    # issue given by their number and a 'gh-' prefix
    'gh-12345',
    'gh-12345 ',
    ' gh-12345',
    ' gh-12345 ',
    # issue given by their URL (no protocol)
    'github.com/python/cpython/issues/12345',
    'github.com/python/cpython/issues/12345 ',
    ' github.com/python/cpython/issues/12345',
    ' github.com/python/cpython/issues/12345 ',
    # issue given by their URL (with protocol)
    'https://github.com/python/cpython/issues/12345',
    'https://github.com/python/cpython/issues/12345 ',
    ' https://github.com/python/cpython/issues/12345',
    ' https://github.com/python/cpython/issues/12345 ',
])
def test_valid_issue_number_12345(issue):
    actual = blurb._extract_issue_number(issue)
    assert actual == '12345'


@pytest.mark.parametrize('issue', [
    '',
    'abc',
    'gh-abc',
    'gh-',
    'bpo-',
    'bpo-12345',
    'github.com/python/cpython/issues',
    'github.com/python/cpython/issues/',
    'github.com/python/cpython/issues/abc',
    'github.com/python/cpython/issues/gh-abc',
    'github.com/python/cpython/issues/gh-123',
    'github.com/python/cpython/issues/1234?param=1',
    'https://github.com/python/cpython/issues',
    'https://github.com/python/cpython/issues/',
    'https://github.com/python/cpython/issues/abc',
    'https://github.com/python/cpython/issues/gh-abc',
    'https://github.com/python/cpython/issues/gh-123',
    'https://github.com/python/cpython/issues/1234?param=1',
])
def test_invalid_issue_number(issue):
    error_message = re.escape(f'Invalid GitHub issue: {issue}')
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_issue_number(issue)


class TestValidSectionNames:
    @staticmethod
    def check(section, expected):
        actual = blurb._extract_section_name(section)
        assert actual == expected

    @pytest.mark.parametrize(
        ('section', 'expected'),
        tuple(zip(blurb.SECTIONS, blurb.SECTIONS))
    )
    def test_exact_names(self, section, expected):
        self.check(section, expected)

    @pytest.mark.parametrize(
        ('section', 'expected'), [
            ('Sec', 'Security'),
            ('sec', 'Security'),
            ('security', 'Security'),
            ('Core And', 'Core and Builtins'),
            ('Core And Built', 'Core and Builtins'),
            ('Core And Builtins', 'Core and Builtins'),
            ('Lib', 'Library'),
            ('doc', 'Documentation'),
            ('document', 'Documentation'),
            ('Tes', 'Tests'),
            ('tes', 'Tests'),
            ('Test', 'Tests'),
            ('Tests', 'Tests'),
            # 'Buil' and 'bui' are ambiguous with 'Core and Builtins'
            ('build', 'Build'),
            ('Tool', 'Tools/Demos'),
            ('Tools', 'Tools/Demos'),
            ('Tools/', 'Tools/Demos'),
            ('core', 'Core and Builtins'),
        ]
    )
    def test_partial_words(self, section, expected):
        self.check(section, expected)

    @pytest.mark.parametrize(
        ('section', 'expected'), [
            ('builtin', 'Core and Builtins'),
            ('builtins', 'Core and Builtins'),
            ('api', 'C API'),
            ('c-api', 'C API'),
            ('c/api', 'C API'),
            ('c api', 'C API'),
            ('dem', 'Tools/Demos'),
            ('demo', 'Tools/Demos'),
            ('demos', 'Tools/Demos'),
        ]
    )
    def test_partial_special_names(self, section, expected):
        self.check(section, expected)

    @pytest.mark.parametrize(
        ('section', 'expected'), [
            ('Core-and-Builtins', 'Core and Builtins'),
            ('Core_and_Builtins', 'Core and Builtins'),
            ('Core_and-Builtins', 'Core and Builtins'),
            ('Core and', 'Core and Builtins'),
            ('Core_and', 'Core and Builtins'),
            ('core_and', 'Core and Builtins'),
            ('core-and', 'Core and Builtins'),
            ('Core   and   Builtins', 'Core and Builtins'),
            ('cOre _ and - bUILtins', 'Core and Builtins'),
            ('Tools/demo', 'Tools/Demos'),
            ('Tools-demo', 'Tools/Demos'),
            ('Tools demo', 'Tools/Demos'),
        ]
    )
    def test_partial_separators(self, section, expected):
        # normalize the separtors '_', '-', ' ' and '/'
        self.check(section, expected)

    @pytest.mark.parametrize(
        ('prefix', 'expected'), [
            ('corean', 'Core and Builtins'),
            ('coreand', 'Core and Builtins'),
            ('coreandbuilt', 'Core and Builtins'),
            ('coreand Builtins', 'Core and Builtins'),
            ('coreand Builtins', 'Core and Builtins'),
            ('coreAnd Builtins', 'Core and Builtins'),
            ('CoreAnd Builtins', 'Core and Builtins'),
            ('Coreand', 'Core and Builtins'),
            ('Coreand Builtins', 'Core and Builtins'),
            ('Coreand builtin', 'Core and Builtins'),
            ('Coreand buil', 'Core and Builtins'),
        ]
    )
    def test_partial_prefix_words(self, prefix, expected):
        # try to find a match using prefixes (without separators and lowercase)
        self.check(prefix, expected)

    @pytest.mark.parametrize(
        ('section', 'expected'),
        [(name.lower(), name) for name in blurb.SECTIONS],
    )
    def test_exact_names_lowercase(self, section, expected):
        self.check(section, expected)

    @pytest.mark.parametrize(
        ('section', 'expected'),
        [(name.upper(), name) for name in blurb.SECTIONS],
    )
    def test_exact_names_uppercase(self, section, expected):
        self.check(section, expected)


@pytest.mark.parametrize('section', ['', ' ', '      '])
def test_empty_section_name(section):
    error_message = re.escape('Empty section name!')
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)


@pytest.mark.parametrize('section', [
    # invalid
    '_',
    '-',
    'invalid',
    'Not a section',
    # non-special names
    'c?api',
    'cXapi',
    'C+API',
    # super-strings
    'Library and more',
    'library3',
    'librari',
])
def test_invalid_section_name(section):
    error_message = re.escape(f'Invalid section name: {section!r}')
    error_message = re.compile(rf'{error_message}\n\n.+', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)


@pytest.mark.parametrize(('section', 'matches'), [
    # 'matches' must be a sorted sequence of matching section names
    ('c', ['C API', 'Core and Builtins']),
    ('C', ['C API', 'Core and Builtins']),
    ('buil', ['Build', 'Core and Builtins']),
    ('BUIL', ['Build', 'Core and Builtins']),
])
def test_ambiguous_section_name(section, matches):
    matching_list = ', '.join(map(repr, matches))
    error_message = re.escape(f'More than one match for: {section!r}\n'
                              f'Matches: {matching_list}')
    error_message = re.compile(rf'{error_message}', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)


def test_prepare_template_with_issue():
    """Test that prepare_template correctly fills in issue number."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.rst', delete=False) as tmp:
        blurb.prepare_template(tmp.name, "12345", None, None)
        tmp.seek(0)
        content = tmp.read()

        assert ".. gh-issue: 12345" in content
        assert ".. gh-issue: \n" not in content


def test_prepare_template_with_section():
    """Test that prepare_template correctly uncomments section."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.rst', delete=False) as tmp:
        blurb.prepare_template(tmp.name, None, "Library", None)
        tmp.seek(0)
        content = tmp.read()

        assert ".. section: Library" in content
        assert "#.. section: Library" not in content
        # Other sections should still be commented
        assert "#.. section: Tests" in content


def test_prepare_template_with_content():
    """Test that prepare_template correctly adds content."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.rst', delete=False) as tmp:
        test_content = "Fixed spam module to handle eggs."
        blurb.prepare_template(tmp.name, None, None, test_content)
        tmp.seek(0)
        content = tmp.read()

        assert test_content in content
        # The marker is followed by content, so check that the content appears after it
        assert "#################\n\n" + test_content in content


class TestAddCommandAutomation:
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
        """Test that add command has proper help text."""
        # With cyclopts, help is handled by the framework, not a parameter
        # We'll test the docstring is properly formatted instead
        assert blurb.add.__doc__ is not None
        assert "Add a new Misc/NEWS entry" in blurb.add.__doc__
        assert "issue" in blurb.add.__doc__
        assert "section" in blurb.add.__doc__
        assert "rst_on_stdin" in blurb.add.__doc__

    @pytest.fixture
    def mock_chdir(self):
        """Mock chdir_to_repo_root for tests."""
        with mock.patch.object(blurb, 'chdir_to_repo_root') as m:
            yield m

    def test_rst_on_stdin_requires_other_params(self, mock_chdir, capsys):
        """Test that --rst-on-stdin requires --issue and --section."""
        with pytest.raises(SystemExit) as exc_info:
            blurb.add(rst_on_stdin=True)

        # error() function exits with string message, not code
        assert "--issue and --section required with --rst-on-stdin" in str(exc_info.value)

    def test_add_with_all_automation_params(self, tmp_path):
        """Test successful add with all automation parameters."""
        # Set up filesystem
        (tmp_path / "Misc" / "NEWS.d" / "next" / "Library").mkdir(parents=True)
        os.chdir(tmp_path)
        blurb.root = str(tmp_path)

        with mock.patch.object(blurb, 'chdir_to_repo_root'):
            with mock.patch.object(blurb, 'flush_git_add_files') as mock_flush_git:
                with mock.patch.object(sys, 'stdin', new_callable=io.StringIO) as mock_stdin:
                    # Mock stdin content with a Monty Python reference
                    mock_stdin.write("Fixed spam module to properly handle eggs, bacon, and spam repetition counts.")
                    mock_stdin.seek(0)

                    # Call add with automation parameters
                    with mock.patch.object(blurb, 'sortable_datetime', return_value='2024-01-01-12-00-00'):
                        with mock.patch.object(blurb, 'nonceify', return_value='abc123'):
                            blurb.add(
                                issue="123456",
                                section="Library",
                                rst_on_stdin=True
                            )

        # Verify the file was created
        expected_filename = "2024-01-01-12-00-00.gh-issue-123456.abc123.rst"
        expected_path = tmp_path / "Misc" / "NEWS.d" / "next" / "Library" / expected_filename
        assert expected_path.exists()

        # Verify file contents - the metadata is in the filename, not the file content
        content = expected_path.read_text()

        # The file should only contain the body text (which may be wrapped)
        assert "Fixed spam module to properly handle eggs, bacon, and spam repetition" in content
        assert "counts." in content

        # Verify git add was called
        assert str(expected_path) in blurb.git_add_files
        mock_flush_git.assert_called_once()
