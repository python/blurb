import re

import pytest

import blurb._add
from blurb._add import (
    _blurb_template_text,
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
    ('section', 'expect'),
    [
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
        ('Buil', 'Build'),
        ('buil', 'Build'),
        ('build', 'Build'),
        ('Tool', 'Tools/Demos'),
        ('Tools', 'Tools/Demos'),
        ('Tools/', 'Tools/Demos'),
        ('core', 'Core and Builtins'),
    ],
)
def test_partial_words(section, expect):
    _check_section_name(section, expect)


@pytest.mark.parametrize(
    ('section', 'expect'),
    [
        ('builtin', 'Core and Builtins'),
        ('builtins', 'Core and Builtins'),
        ('api', 'C API'),
        ('c-api', 'C API'),
        ('c/api', 'C API'),
        ('c api', 'C API'),
        ('dem', 'Tools/Demos'),
        ('demo', 'Tools/Demos'),
        ('demos', 'Tools/Demos'),
    ],
)
def test_partial_special_names(section, expect):
    _check_section_name(section, expect)


@pytest.mark.parametrize(
    ('section', 'expect'),
    [
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
    ],
)
def test_partial_separators(section, expect):
    # normalize the separtors '_', '-', ' ' and '/'
    _check_section_name(section, expect)


@pytest.mark.parametrize(
    ('prefix', 'expect'),
    [
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
    ],
)
def test_partial_prefix_words(prefix, expect):
    # try to find a match using prefixes (without separators and lowercase)
    _check_section_name(prefix, expect)


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


@pytest.mark.parametrize(
    ('section', 'matches'),
    [
        # 'matches' must be a sorted sequence of matching section names
        ('c', ['C API', 'Core and Builtins']),
        ('C', ['C API', 'Core and Builtins']),
        ('t', ['Tests', 'Tools/Demos']),
        ('T', ['Tests', 'Tools/Demos']),
    ],
)
def test_ambiguous_section_name(section, matches):
    matching_list = ', '.join(map(repr, matches))
    error_message = re.escape(
        f'More than one match for: {section!r}\nMatches: {matching_list}'
    )
    error_message = re.compile(rf'{error_message}', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        _extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        _blurb_template_text(issue=None, section=section)
