import re

import pytest

from blurb import blurb


def test_valid_no_issue_number():
    assert blurb._extract_issue_number(None) is None
    res = blurb._blurb_template_text(issue=None)
    lines = frozenset(res.splitlines())
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' in lines


@pytest.mark.parametrize('issue', (
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
))
def test_valid_issue_number_12345(issue):
    actual = blurb._extract_issue_number(issue)
    assert actual == 12345

    res = blurb._blurb_template_text(issue=issue)
    lines = frozenset(res.splitlines())
    assert '.. gh-issue:' not in lines
    assert '.. gh-issue: ' not in lines
    assert '.. gh-issue: 12345' in lines


@pytest.mark.parametrize('issue', (
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
))
def test_invalid_issue_number(issue):
    error_message = re.escape(f'Invalid GitHub issue: {issue}')
    with pytest.raises(SystemExit, match=error_message):
        blurb._blurb_template_text(issue=issue)


@pytest.mark.parametrize('invalid', (
    'gh-issue: ',
    'gh-issue: 1',
    'gh-issue',
))
def test_malformed_gh_issue_line(invalid, monkeypatch):
    template = blurb.template.replace('.. gh-issue:', invalid)
    error_message = re.escape("Can't find gh-issue line in the template!")
    with monkeypatch.context() as cm:
        cm.setattr(blurb, 'template', template)
        with pytest.raises(SystemExit, match=error_message):
            blurb._blurb_template_text(issue='1234')
