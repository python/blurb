from __future__ import annotations

#
# This template is the canonical list of acceptable section names!
# It's parsed internally into the "sections" set.
#

template = """

#
# Please enter the relevant GitHub issue number here:
#
.. gh-issue:

#
# Uncomment one of these "section:" lines to specify which section
# this entry should go in in Misc/NEWS.d.
#
#.. section: Security
#.. section: Core and Builtins
#.. section: Library
#.. section: Documentation
#.. section: Tests
#.. section: Build
#.. section: Windows
#.. section: macOS
#.. section: IDLE
#.. section: Tools/Demos
#.. section: C API

# Write your Misc/NEWS.d entry below.  It should be a simple ReST paragraph.
# Don't start with "- Issue #<n>: " or "- gh-issue-<n>: " or that sort of stuff.
###########################################################################


""".lstrip()

sections: list[str] = []
for line in template.split('\n'):
    line = line.strip()
    prefix, found, section = line.partition('#.. section: ')
    if found and not prefix:
        sections.append(section.strip())

_sanitize_section = {
    'C API': 'C_API',
    'Core and Builtins': 'Core_and_Builtins',
    'Tools/Demos': 'Tools-Demos',
}

_unsanitize_section = {
    'C_API': 'C API',
    'Core_and_Builtins': 'Core and Builtins',
    'Tools-Demos': 'Tools/Demos',
}


def sanitize_section(section: str, /) -> str:
    """Clean up a section string.

    This makes it viable as a directory name.
    """
    return _sanitize_section.get(section, section)


def sanitize_section_legacy(section: str, /) -> str:
    """Clean up a section string, allowing spaces.

    This makes it viable as a directory name.
    """
    return section.replace('/', '-')


def unsanitize_section(section: str, /) -> str:
    return _unsanitize_section.get(section, section)


def next_filename_unsanitize_sections(filename: str, /) -> str:
    for key, value in _unsanitize_section.items():
        for separator in ('/', '\\'):
            key = f'{separator}{key}{separator}'
            value = f'{separator}{value}{separator}'
            filename = filename.replace(key, value)
    return filename
