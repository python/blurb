import blurb._template


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
