import glob
import os
import sys
from pathlib import Path

from blurb._cli import require_ok, subcommand
from blurb._template import (
    next_filename_unsanitize_sections, sanitize_section,
    sanitize_section_legacy, sections,
)
from blurb._versions import glob_versions, printable_version
from blurb.blurb import Blurbs, textwrap_body

original_dir: str = os.getcwd()


@subcommand
def merge(output: str | None = None, *, forced: bool = False) -> None:
    """Merge all blurbs together into a single Misc/NEWS file.

    Optional output argument specifies where to write to.
    Default is <cpython-root>/Misc/NEWS.

    If overwriting, blurb merge will prompt you to make sure it's okay.
    To force it to overwrite, use -f.
    """
    if output:
        output = os.path.join(original_dir, output)
    else:
        output = 'Misc/NEWS'

    versions = glob_versions()
    if not versions:
        sys.exit("You literally don't have ANY blurbs to merge together!")

    if os.path.exists(output) and not forced:
        print(f'You already have a {output!r} file.')
        require_ok('Type ok to overwrite')

    write_news(output, versions=versions)


def write_news(output: str, *, versions: list[str]) -> None:
    buff = []

    def prnt(msg: str = '', /):
        buff.append(msg)

    prnt("""
+++++++++++
Python News
+++++++++++

""".strip())

    for version in versions:
        filenames = glob_blurbs(version)

        blurbs = Blurbs()
        if version == 'next':
            for filename in filenames:
                if os.path.basename(filename) == 'README.rst':
                    continue
                blurbs.load_next(filename)
            if not blurbs:
                continue
            metadata = blurbs[0][0]
            metadata['release date'] = 'XXXX-XX-XX'
        else:
            assert len(filenames) == 1
            blurbs.load(filenames[0])

        header = f"What's New in Python {printable_version(version)}?"
        prnt()
        prnt(header)
        prnt('=' * len(header))
        prnt()

        metadata, body = blurbs[0]
        release_date = metadata['release date']

        prnt(f'*Release date: {release_date}*')
        prnt()

        if 'no changes' in metadata:
            prnt(body)
            prnt()
            continue

        last_section = None
        for metadata, body in blurbs:
            section = metadata['section']
            if last_section != section:
                last_section = section
                prnt(section)
                prnt('-' * len(section))
                prnt()
            if metadata.get('gh-issue'):
                issue_number = metadata['gh-issue']
                if int(issue_number):
                    body = f'gh-{issue_number}: {body}'
            elif metadata.get('bpo'):
                issue_number = metadata['bpo']
                if int(issue_number):
                    body = f'bpo-{issue_number}: {body}'

            body = f'- {body}'
            text = textwrap_body(body, subsequent_indent='  ')
            prnt(text)
    prnt()
    prnt('**(For information about older versions, consult the HISTORY file.)**')

    new_contents = '\n'.join(buff)

    # Only write in `output` if the contents are different
    # This speeds up subsequent Sphinx builds
    try:
        previous_contents = Path(output).read_text(encoding='utf-8')
    except (FileNotFoundError, UnicodeError):
        previous_contents = None
    if new_contents != previous_contents:
        Path(output).write_text(new_contents, encoding='utf-8')
    else:
        print(output, 'is already up to date')


def glob_blurbs(version: str) -> list[str]:
    filenames = []
    base = os.path.join('Misc', 'NEWS.d', version)
    if version != 'next':
        wildcard = f'{base}.rst'
        filenames.extend(glob.glob(wildcard))
    else:
        sanitized_sections = (
                {sanitize_section(section) for section in sections} |
                {sanitize_section_legacy(section) for section in sections}
        )
        for section in sanitized_sections:
            wildcard = os.path.join(base, section, '*.rst')
            entries = glob.glob(wildcard)
            deletables = [x for x in entries if x.endswith('/README.rst')]
            for filename in deletables:
                entries.remove(filename)
            filenames.extend(entries)
    filenames.sort(reverse=True, key=next_filename_unsanitize_sections)
    return filenames
