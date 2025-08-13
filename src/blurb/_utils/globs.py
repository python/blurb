import glob
import os

from blurb._template import (
    next_filename_unsanitize_sections, sanitize_section,
    sanitize_section_legacy, sections,
)


def glob_blurbs(version: str) -> list[str]:
    filenames = []
    base = os.path.join('Misc', 'NEWS.d', version)
    if version != 'next':
        wildcard = f'{base}.rst'
        filenames.extend(glob.glob(wildcard))
    else:
        sanitized_sections = set(map(sanitize_section, sections))
        sanitized_sections |= set(map(sanitize_section_legacy, sections))
        for section in sanitized_sections:
            wildcard = os.path.join(base, section, '*.rst')
            entries = glob.glob(wildcard)
            deletables = [x for x in entries if x.endswith('/README.rst')]
            for filename in deletables:
                entries.remove(filename)
            filenames.extend(entries)
    filenames.sort(reverse=True, key=next_filename_unsanitize_sections)
    return filenames
