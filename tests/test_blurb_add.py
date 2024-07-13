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
        ]
    )
    def test_partial_words(self, section, expect):
        # test that partial matching from the beginning is supported
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('section', 'expect'), [
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
    def test_partial_special_names(self, section, expect):
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('section', 'expect'), [
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
    def test_partial_separators(self, section, expect):
        self.check(section, expect)

    @pytest.mark.parametrize(
        ('prefix', 'expect'), [
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
    def test_partial_prefix_words(self, prefix, expect):
        # spaces are not needed if we cannot find a correct match
        self.check(prefix, expect)

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


@pytest.mark.parametrize('section', [
    # invalid
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

    with pytest.raises(SystemExit, match=error_message):
        blurb._update_blurb_template(issue=None, section=section)


@pytest.mark.parametrize(('section', 'matches'), [
    # 'matches' must be a sorted sequence of matching section names
    ('c', ['C API', 'Core and Builtins']),
    ('C', ['C API', 'Core and Builtins']),
    ('t', ['Tests', 'Tools/Demos']),
    ('T', ['Tests', 'Tools/Demos']),
])
def test_ambiguous_section_name(section, matches):
    matching_list = ', '.join(map(repr, matches))
    error_message = re.escape(f'More than one match for: {section!r}\n'
                              f'Matches: {matching_list}')
    error_message = re.compile(rf'{error_message}', re.MULTILINE)
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
