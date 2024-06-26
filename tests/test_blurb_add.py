import re

import pytest

from blurb import blurb


def test_valid_no_issue_number():
    assert blurb._extract_issue_number(None) is None
    res = blurb._update_blurb_template(issue=None, section=None)
    lines = res.splitlines()
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' in lines
    for line in lines:
        assert not line.startswith('.. section: ')


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

    res = blurb._update_blurb_template(issue=issue, section=None)

    lines = res.splitlines()
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' not in lines
    assert '.. gh-issue: 12345' in lines

    for line in lines:
        assert not line.startswith('.. section: ')


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

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=issue, section=None)


@pytest.mark.parametrize(('section_index', 'section_id', 'section_name'), (
    (0, '1', 'Security'),
    (1, '2', 'Core and Builtins'),
    (2, '3', 'Library'),
    (3, '4', 'Documentation'),
    (4, '5', 'Tests'),
    (5, '6', 'Build'),
    (6, '7', 'Windows'),
    (7, '8', 'macOS'),
    (8, '9', 'IDLE'),
    (9, '10', 'Tools/Demos'),
    (10, '11', 'C API'),
))
def test_valid_section_id(section_index, section_id, section_name):
    actual = blurb._extract_section_name(section_id)
    assert actual == section_name
    assert actual == blurb.sections[section_index]

    res = blurb._update_blurb_template(issue=None, section=section_id)
    res = res.splitlines()


    for index, _ in enumerate(blurb.sections):
        if index == section_index:
            assert f'.. section: {blurb.sections[index]}' in res
        else:
            assert f'#.. section: {blurb.sections[index]}' in res
            assert f'.. section: {blurb.sections[index]}' not in res


@pytest.mark.parametrize('section', ['-1', '0', '1337'])
def test_invalid_section_id(section):
    error_message = re.escape(f'Invalid section ID: {int(section)}')
    error_message = re.compile(rf'{error_message}\n\n.+', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=None, section=section)


class TestValidSectionNames:
    @staticmethod
    def check(section, expect):
        actual = blurb._extract_section_name(section)
        assert actual == expect

        res = blurb._update_blurb_template(issue=None, section=section)
        res = res.splitlines()
        for section_name in blurb.sections:
            if section_name == expect:
                assert f'.. section: {section_name}' in res
            else:
                assert f'#.. section: {section_name}' in res
                assert f'.. section: {section_name}' not in res

    @pytest.mark.parametrize(
        ('section', 'expect'),
        tuple(zip(blurb.sections, blurb.sections))
    )
    def test_exact_names(self, section, expect):
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('section', 'expect'), [
            ('Lib', 'Library'),
            ('Tools', 'Tools/Demos'),
            ('doc', 'Documentation'),
            ('Core-and-Builtins', 'Core and Builtins'),
            ('Core_and_Builtins', 'Core and Builtins'),
            ('Core_and-Builtins', 'Core and Builtins'),
            ('Core and', 'Core and Builtins'),
            ('Core_and', 'Core and Builtins'),
            ('core_and', 'Core and Builtins'),
            ('core-and', 'Core and Builtins'),
            ('Core   and   Builtins', 'Core and Builtins'),
            ('cOre _ and - bUILtins', 'Core and Builtins'),
        ]
    )
    def test_partial_names(self, section, expect):
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('section', 'expect'),
        [(name.lower(), name) for name in blurb.sections],
    )
    def test_exact_names_lowercase(self, section, expect):
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('section', 'expect'),
        [(name.upper(), name) for name in blurb.sections],
    )
    def test_exact_names_uppercase(self, section, expect):
        self.check(section, expect)


@pytest.mark.parametrize('section', ['', ' ', '      '])
def test_empty_section_name(section):
    error_message = re.escape('Empty section name!')
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name('')

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=None, section='')


@pytest.mark.parametrize('section', ['libraryy', 'Not a section'])
def test_invalid_section_name(section):
    error_message = re.escape(f'Invalid section name: {section}')
    error_message = re.compile(rf'{error_message}\n\n.+', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=None, section=section)


@pytest.mark.parametrize(('section', 'matches'), [
    # 'matches' must be a sorted sequence of matching section names
    ('C', ['C API', 'Core and Builtins']),
    ('T', ['Tests', 'Tools/Demos']),
])
def test_ambiguous_section_name(section, matches):
    matching_list = ', '.join(map(repr, matches))
    error_message = re.escape(f'More than one match for: {section}\n'
                              f'Matches: {matching_list}')
    error_message = re.compile(rf'{error_message}\n\n.+', re.MULTILINE)
    with pytest.raises(SystemExit, match=error_message):
        blurb._extract_section_name(section)

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=None, section=section)


@pytest.mark.parametrize('invalid', [
    'gh-issue: ',
    'gh-issue: 1',
    'gh-issue',
])
def test_illformed_gh_issue_line(invalid, monkeypatch):
    template = blurb.template.replace('.. gh-issue:', invalid)
    error_message = re.escape("Can't find gh-issue line to fill!")
    with monkeypatch.context() as cm:
        cm.setattr(blurb, 'template', template)
        with pytest.raises(SystemExit, match=error_message):
            blurb._update_blurb_template(issue='1234', section=None)
