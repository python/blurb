import re

import pytest

import blurb._add
from blurb._add import (
    _blurb_template_text,
    _check_commented_cve,
    _extract_cve,
    _extract_issue_number,
    _extract_section_name,
)
from blurb._template import sections as SECTIONS
from blurb._template import template as blurb_template


def test_valid_no_issue_number():
    assert _extract_issue_number(None) is None
    res = _blurb_template_text(issue=None, section=None)
    lines = frozenset(res.splitlines())
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' in lines


@pytest.mark.parametrize(
    'issue',
    (
        # issue given by their number
        '12345',
        ' 12345  ',
        # issue given by their number and a 'GH-' prefix
        'GH-12345',
        ' GH-12345  ',
        # issue given by their number and a 'gh-' prefix
        'gh-12345',
        ' gh-12345  ',
        # issue given by their number and a '#' prefix
        '#12345',
        ' #12345  ',
        # issue given by their URL (no scheme)
        'github.com/python/cpython/issues/12345',
        ' github.com/python/cpython/issues/12345  ',
        # issue given by their URL (with scheme)
        'https://github.com/python/cpython/issues/12345',
        ' https://github.com/python/cpython/issues/12345  ',
    ),
)
def test_valid_issue_number_12345(issue):
    actual = _extract_issue_number(issue)
    assert actual == 12345

    res = _blurb_template_text(issue=issue, section=None)
    lines = frozenset(res.splitlines())
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' not in lines
    assert '.. gh-issue: 12345' in lines


@pytest.mark.parametrize(
    'issue',
    (
        '',
        'abc',
        'Gh-123',
        'gh-abc',
        'gh- 123',
        'gh -123',
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
    ),
)
def test_invalid_issue_number(issue):
    error_message = re.escape(f'Invalid GitHub issue number: {issue}')
    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=issue, section=None)


@pytest.mark.parametrize(
    'invalid',
    (
        'gh-issue: ',
        'gh-issue: 1',
        'gh-issue',
    ),
)
def test_malformed_gh_issue_line(invalid, monkeypatch):
    template = blurb_template.replace('.. gh-issue:', invalid)
    error_message = re.escape("Can't find gh-issue line in the template!")
    with monkeypatch.context() as cm:
        cm.setattr(blurb._add, 'template', template)
        with pytest.raises(SystemExit, match=error_message):
            _blurb_template_text(issue='1234', section=None)


def _check_section_name(section_name, expected):
    actual = _extract_section_name(section_name)
    assert actual == expected

    res = _blurb_template_text(issue=None, section=section_name)
    res = res.splitlines()
    for section_name in SECTIONS:
        if section_name == expected:
            assert f'.. section: {section_name}' in res
        else:
            assert f'#.. section: {section_name}' in res
            assert f'.. section: {section_name}' not in res


@pytest.mark.parametrize(
    ('section_name', 'expected'),
    [(name, name) for name in SECTIONS],
)
def test_exact_names(section_name, expected):
    _check_section_name(section_name, expected)


@pytest.mark.parametrize(
    ('section_name', 'expected'),
    [(name.lower(), name) for name in SECTIONS],
)
def test_exact_names_lowercase(section_name, expected):
    _check_section_name(section_name, expected)


@pytest.mark.parametrize(
    'section',
    (
        '',
        ' ',
        '\t',
        '\n',
        '\r\n',
        '      ',
    ),
)
def test_empty_section_name(section):
    error_message = re.escape('Empty section name!')
    with pytest.raises(SystemExit, match=error_message):
        _extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=None, section=section)


@pytest.mark.parametrize(
    'section',
    [
        # Wrong capitalisation
        'C api',
        'c API',
        'LibrarY',
        # Invalid
        '_',
        '-',
        '/',
        'invalid',
        'Not a section',
        # Non-special names
        'c?api',
        'cXapi',
        'C+API',
        # Super-strings
        'Library and more',
        'library3',
        'librari',
    ],
)
def test_invalid_section_name(section):
    error_message = rf"(?m)Invalid section name: '{re.escape(section)}'\n\n.+"
    with pytest.raises(SystemExit, match=error_message):
        _extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=None, section=section)


def test_no_cve():
    assert _extract_cve(None) is None
    res = _blurb_template_text(issue=None, section=None)
    lines = frozenset(res.splitlines())
    assert '#.. cve:' in lines
    assert '.. section: Security' not in lines


@pytest.mark.parametrize(
    ('cve', 'section'),
    [
        ('CVE-2025-12345', None),
        ('cve-2025-12345', 'Security'),
        (' 2025-12345 ', 'security'),
    ],
)
def test_valid_cve(cve, section):
    assert _extract_cve(cve) == 'CVE-2025-12345'

    res = _blurb_template_text(issue=None, section=section, cve=cve)
    lines = frozenset(res.splitlines())
    assert '#.. cve:' not in lines
    assert '.. cve: CVE-2025-12345' in lines
    # Giving a CVE selects the Security section.
    assert '.. section: Security' in lines
    assert '#.. section: Security' not in lines
    assert '#.. section: Library' in lines


@pytest.mark.parametrize('cve', ['', 'abc', 'CVE-25-1', 'CVE-2025', 'CVE-2025-1'])
def test_invalid_cve(cve):
    error_message = re.escape(f'Invalid CVE identifier: {cve}')
    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=None, section=None, cve=cve)


@pytest.mark.parametrize('section', [s for s in SECTIONS if s != 'Security'])
def test_cve_wrong_section(section):
    error_message = re.escape("A CVE may only be given for the 'Security' section")
    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=None, section=section, cve='CVE-2025-12345')


def test_malformed_cve_line(monkeypatch):
    template = blurb_template.replace('#.. cve:', '#.. cve: ')
    error_message = re.escape("Can't find cve line in the template!")
    with monkeypatch.context() as cm:
        cm.setattr(blurb._add, 'template', template)
        with pytest.raises(SystemExit, match=error_message):
            _blurb_template_text(issue=None, section=None, cve='CVE-2025-12345')


@pytest.mark.parametrize(
    ('line', 'expected'),
    [
        ('#.. cve:', ''),
        ('#.. cve: ', ''),
        ('.. cve: CVE-2025-12345', ''),
        ('#.. cve: CVE-2025-12345', 'still commented out'),
        ('#.. cve:CVE-2025-12345', 'still commented out'),
    ],
)
def test_check_commented_cve(line, expected, tmp_path):
    path = tmp_path / 'entry.rst'
    path.write_text(f'.. gh-issue: 123456\n.. section: Security\n{line}\n\nBody.\n')
    result = _check_commented_cve(str(path))
    assert expected in result
    assert bool(result) == bool(expected)
