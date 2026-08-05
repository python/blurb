from __future__ import annotations

import re

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


# Mapping from section names to additional allowed patterns
# which ignore whitespaces for composed section names.
#
# For instance, 'Core and Builtins' is represented by the
# pattern 'Core<SEP>?and<SEP>?Builtins' where <SEP> are the
# allowed user separators '_', '-', ' ' and '/'.
_section_special_patterns = {__: set() for __ in sections}

# Mapping from section names to sanitized names (no separators, lowercase).
#
# For instance, 'Core and Builtins' is mapped to 'coreandbuiltins', and
# passing a prefix of that would match to 'Core and Builtins'. Note that
# this is only used as a last resort.
_section_names_lower_nosep = {}

for _section in sections:
    # ' ' and '/' are the separators used by known sections
    _sanitized = re.sub(r'[ /]', ' ', _section)
    _section_words = re.split(r'\s+', _sanitized)
    _section_names_lower_nosep[_section] = ''.join(_section_words).lower()
    del _sanitized
    # '_', '-', ' ' and '/' are the allowed (user) separators
    _section_pattern = r'[_\- /]?'.join(map(re.escape, _section_words))
    # add '$' to avoid matching after the pattern
    _section_pattern = f'{_section_pattern}$'
    del _section_words
    _section_pattern = re.compile(_section_pattern, re.I)
    _section_special_patterns[_section].add(_section_pattern)
    del _section_pattern, _section

# the following statements will raise KeyError if the names are invalid
_section_special_patterns['C API'].add(re.compile(r'^((?<=c)[_\- /])?api$', re.I))
_section_special_patterns['Core and Builtins'].add(re.compile('^builtins?$', re.I))
_section_special_patterns['Tools/Demos'].add(re.compile('^dem(?:o|os)?$', re.I))
