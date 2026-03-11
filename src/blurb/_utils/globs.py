from __future__ import annotations

import glob
import os

from blurb._template import (
    next_filename_unsanitize_sections,
    sanitize_section,
    sanitize_section_legacy,
    sections,
)


def glob_blurbs(version: str) -> list[str]:
    filenames = []
    base = os.path.join('Misc', 'NEWS.d', version)

    if version != 'next':
        wildcard = f'{base}.rst'
        filenames.extend(glob.glob(wildcard))
        return filenames

    for section in sections:
        entries = []
        seen_dirs = set()
        for dir_name in (
            sanitize_section(section),
            sanitize_section_legacy(section),
        ):
            if dir_name in seen_dirs:
                continue

            seen_dirs.add(dir_name)
            wildcard = os.path.join(base, dir_name, '*.rst')
            for entry in glob.glob(wildcard):
                if not entry.endswith('/README.rst'):
                    entries.append(entry)

        entries.sort(reverse=True, key=next_filename_unsanitize_sections)
        filenames.extend(entries)

    return filenames
