import pytest

import blurb._template
from blurb._template import sanitize_section, unsanitize_section

UNCHANGED_SECTIONS = ('Library',)


def test_section_names():
    assert tuple(blurb._template.sections) == (
        'Security',
        'Core and Builtins',
        'Library',
        'Documentation',
        'Tests',
        'Build',
        'Windows',
        'macOS',
        'IDLE',
        'Tools/Demos',
        'C API',
    )


@pytest.mark.parametrize('section', UNCHANGED_SECTIONS)
def test_sanitize_section_no_change(section):
    sanitized = sanitize_section(section)
    assert sanitized == section


@pytest.mark.parametrize(
    'section, expected',
    (
        ('C API', 'C_API'),
        ('Core and Builtins', 'Core_and_Builtins'),
        ('Tools/Demos', 'Tools-Demos'),
    ),
)
def test_sanitize_section_changed(section, expected):
    sanitized = sanitize_section(section)
    assert sanitized == expected


@pytest.mark.parametrize('section', UNCHANGED_SECTIONS)
def test_unsanitize_section_no_change(section):
    unsanitized = unsanitize_section(section)
    assert unsanitized == section


@pytest.mark.parametrize(
    'section, expected',
    (('Tools-Demos', 'Tools/Demos'),),
)
def test_unsanitize_section_changed(section, expected):
    unsanitized = unsanitize_section(section)
    assert unsanitized == expected
