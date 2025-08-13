from __future__ import annotations

import atexit
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

from blurb._blurb_file import BlurbError, Blurbs
from blurb._cli import error, prompt, subcommand
from blurb._git import flush_git_add_files, git_add_files
from blurb._template import sections, template

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence

if sys.platform == 'win32':
    FALLBACK_EDITORS = ('notepad.exe',)
else:
    FALLBACK_EDITORS = ('/etc/alternatives/editor', 'nano')


@subcommand
def add(*, issue: str | None = None, section: str | None = None):
    """Add a blurb (a Misc/NEWS.d/next entry) to the current CPython repo.

    Use -i/--issue to specify a GitHub issue number or link, e.g.:

        blurb add -i 12345
        # or
        blurb add -i https://github.com/python/cpython/issues/12345

    Use -s/--section to specify the section name (case-insensitive), e.g.:

        blurb add -s Library
        # or
        blurb add -s library

    The known sections names are defined as follows and
    spaces in names can be substituted for underscores:

{sections}
    """  # fmt: skip

    handle, tmp_path = tempfile.mkstemp('.rst')
    os.close(handle)
    atexit.register(lambda: os.unlink(tmp_path))

    text = _blurb_template_text(issue=issue, section=section)
    with open(tmp_path, 'w', encoding='utf-8') as file:
        file.write(text)

    args = _editor_args()
    args.append(tmp_path)

    while True:
        blurb = _add_blurb_from_template(args, tmp_path)
        if blurb is None:
            try:
                prompt('Hit return to retry (or Ctrl-C to abort)')
            except KeyboardInterrupt:
                print()
                return
            print()
            continue
        break

    path = blurb.save_next()
    git_add_files.append(path)
    flush_git_add_files()
    print('Ready for commit.')


add.__doc__ = add.__doc__.format(sections='\n'.join(f'* {s}' for s in sections))


def _editor_args() -> list[str]:
    editor = _find_editor()

    # We need to be clever about EDITOR.
    # On the one hand, it might be a legitimate path to an
    #   executable containing spaces.
    # On the other hand, it might be a partial command-line
    #   with options.
    if shutil.which(editor):
        args = [editor]
    else:
        args = list(shlex.split(editor))
        if not shutil.which(args[0]):
            raise SystemExit(f'Invalid GIT_EDITOR / EDITOR value: {editor}')
    return args


def _find_editor() -> str:
    for var in 'GIT_EDITOR', 'EDITOR':
        editor = os.environ.get(var)
        if editor is not None:
            return editor
    for fallback in FALLBACK_EDITORS:
        if os.path.isabs(fallback):
            found_path = fallback
        else:
            found_path = shutil.which(fallback)
        if found_path and os.path.exists(found_path):
            return found_path
    error('Could not find an editor! Set the EDITOR environment variable.')


def _blurb_template_text(*, issue: str | None, section: str | None) -> str:
    issue_number = _extract_issue_number(issue)
    section_name = _extract_section_name(section)

    text = template

    # Ensure that there is a trailing space after '.. gh-issue:' to make
    # filling in the template easier, unless an issue number was given
    # through the --issue command-line flag.
    issue_line = '.. gh-issue:'
    without_space = f'\n{issue_line}\n'
    if without_space not in text:
        raise SystemExit("Can't find gh-issue line in the template!")
    if issue_number is None:
        with_space = f'\n{issue_line} \n'
        text = text.replace(without_space, with_space)
    else:
        with_issue_number = f'\n{issue_line} {issue_number}\n'
        text = text.replace(without_space, with_issue_number)

    # Uncomment the section if needed.
    if section_name is not None:
        pattern = f'.. section: {section_name}'
        text = text.replace(f'#{pattern}', pattern)

    return text


def _extract_issue_number(issue: str | None, /) -> int | None:
    if issue is None:
        return None
    issue = issue.strip()

    if issue.startswith(('GH-', 'gh-')):
        stripped = issue[3:]
    else:
        stripped = issue.removeprefix('#')
    try:
        if stripped.isdecimal():
            return int(stripped)
    except ValueError:
        pass

    # Allow GitHub URL with or without the scheme
    stripped = issue.removeprefix('https://')
    stripped = stripped.removeprefix('github.com/python/cpython/issues/')
    try:
        if stripped.isdecimal():
            return int(stripped)
    except ValueError:
        pass

    raise SystemExit(f'Invalid GitHub issue number: {issue}')


def _extract_section_name(section: str | None, /) -> str | None:
    if section is None:
        return None

    section = section.strip()
    if not section:
        raise SystemExit('Empty section name!')

    matches = []
    # Try an exact or lowercase match
    for section_name in sections:
        if section in {section_name, section_name.lower()}:
            matches.append(section_name)

    if not matches:
        section_list = '\n'.join(f'* {s}' for s in sections)
        raise SystemExit(
            f'Invalid section name: {section!r}\n\nValid names are:\n\n{section_list}'
        )

    if len(matches) > 1:
        multiple_matches = ', '.join(f'* {m}' for m in sorted(matches))
        raise SystemExit(f'More than one match for {section!r}:\n\n{multiple_matches}')

    return matches[0]


def _add_blurb_from_template(args: Sequence[str], tmp_path: str) -> Blurbs | None:
    subprocess.run(args)

    failure = ''
    blurb = Blurbs()
    try:
        blurb.load(tmp_path)
    except BlurbError as e:
        failure = str(e)

    if not failure:
        assert len(blurb)  # if parse_blurb succeeds, we should always have a body
        if len(blurb) > 1:
            failure = "Too many entries!  Don't specify '..' on a line by itself."

    if failure:
        print()
        print(f'Error: {failure}')
        print()
        return None
    return blurb
