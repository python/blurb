"""

The format of a blurb file:

    ENTRY
    [ENTRY2
    ENTRY3
    ...]

In other words, you may have one or more ENTRYs (entries) in a blurb file.

The format of an ENTRY:

    METADATA
    BODY

The METADATA section is optional.
The BODY section is mandatory and must be non-empty.

Format of the METADATA section:

  * Lines starting with ".." are metadata lines of the format:
        .. name: value
  * Lines starting with "#" are comments:
        # comment line
  * Empty and whitespace-only lines are ignored.
  * Trailing whitespace is removed.  Leading whitespace is not removed
    or ignored.

The first nonblank line that doesn't start with ".." or "#" automatically
terminates the METADATA section and is the first line of the BODY.

Format of the BODY section:

  * The BODY section should be a single paragraph of English text
    in ReST format.  It should not use the following ReST markup
    features:
      * section headers
      * comments
      * directives, citations, or footnotes
      * Any features that require significant line breaks,
        like lists, definition lists, quoted paragraphs, line blocks,
        literal code blocks, and tables.
    Note that this is not (currently) enforced.
  * Trailing whitespace is stripped.  Leading whitespace is preserved.
  * Empty lines between non-empty lines are preserved.
    Trailing empty lines are stripped.
  * The BODY mustn't start with "Issue #", "gh-", or "- ".
    (This formatting will be inserted when rendering the final output.)
  * Lines longer than 76 characters will be wordwrapped.
      * In the final output, the first line will have
        "- gh-issue-<gh-issue-number>: " inserted at the front,
        and subsequent lines will have two spaces inserted
        at the front.

To terminate an ENTRY, specify a line containing only "..".  End of file
also terminates the last ENTRY.

-----------------------------------------------------------------------------

The format of a "next" file is exactly the same, except that we're storing
four pieces of metadata in the filename instead of in the metadata section.
Those four pieces of metadata are: section, gh-issue, date, and nonce.

-----------------------------------------------------------------------------

In addition to the four conventional metadata (section, gh-issue, date, and nonce),
there are two additional metadata used per-version: "release date" and
"no changes".  These may only be present in the metadata block in the *first*
blurb in a blurb file.
  * "release date" is the day a particular version of Python was released.
  * "no changes", if present, notes that there were no actual changes
    for this version.  When used, there are two more things that must be
    true about the the blurb file:
      * There should only be one entry inside the blurb file.
      * That entry's gh-issue number must be 0.

"""

from __future__ import annotations

import os
import re
import time

from blurb._template import sanitize_section, sections, unsanitize_section
from blurb._utils.text import generate_nonce, textwrap_body

root = None  # Set by chdir_to_repo_root()
lowest_possible_gh_issue_number = 32426


class BlurbError(RuntimeError):
    pass


class Blurbs(list):
    def parse(self, text: str, *, metadata: dict[str, str] | None = None,
              filename: str = 'input') -> None:
        """Parses a string.

        Appends a list of blurb ENTRIES to self, as tuples: (metadata, body)
        metadata is a dict.  body is a string.
        """

        metadata = metadata or {}
        body = []
        in_metadata = True

        line_number = None

        def throw(s: str):
            raise BlurbError(f'Error in {filename}:{line_number}:\n{s}')

        def finish_entry() -> None:
            nonlocal body
            nonlocal in_metadata
            nonlocal metadata
            nonlocal self

            if not body:
                throw("Blurb 'body' text must not be empty!")
            text = textwrap_body(body)
            for naughty_prefix in ('- ', 'Issue #', 'bpo-', 'gh-', 'gh-issue-'):
                if re.match(naughty_prefix, text, re.I):
                    throw(f"Blurb 'body' can't start with {naughty_prefix!r}!")

            no_changes = metadata.get('no changes')

            issue_keys = {
                'gh-issue': 'GitHub',
                'bpo': 'bpo',
            }
            for key, value in metadata.items():
                # Iterate over metadata items in order.
                # We parsed the blurb file line by line,
                # so we'll insert metadata keys in the
                # order we see them.  So if we issue the
                # errors in the order we see the keys,
                # we'll complain about the *first* error
                # we see in the blurb file, which is a
                # better user experience.
                if key in issue_keys:
                    try:
                        int(value)
                    except (TypeError, ValueError):
                        throw(f'Invalid {issue_keys[key]} number: {value!r}')

                if key == 'gh-issue' and int(value) < lowest_possible_gh_issue_number:
                    throw(f'Invalid gh-issue number: {value!r} (must be >= {lowest_possible_gh_issue_number})')

                if key == 'section':
                    if no_changes:
                        continue
                    if value not in sections:
                        throw(f'Invalid section {value!r}!  You must use one of the predefined sections.')

            if 'gh-issue' not in metadata and 'bpo' not in metadata:
                throw("'gh-issue:' or 'bpo:' must be specified in the metadata!")

            if 'section' not in metadata:
                throw("No 'section' specified.  You must provide one!")

            self.append((metadata, text))
            metadata = {}
            body = []
            in_metadata = True

        for line_number, line in enumerate(text.split('\n')):
            line = line.rstrip()
            if in_metadata:
                if line.startswith('..'):
                    line = line[2:].strip()
                    name, colon, value = line.partition(':')
                    assert colon
                    name = name.lower().strip()
                    value = value.strip()
                    if name in metadata:
                        throw(f'Blurb metadata sets {name!r} twice!')
                    metadata[name] = value
                    continue
                if line.startswith('#') or not line:
                    continue
                in_metadata = False

            if line == '..':
                finish_entry()
                continue
            body.append(line)

        finish_entry()

    def load(self, filename: str, *, metadata: dict[str, str] | None = None) -> None:
        """Read a blurb file.

        Broadly equivalent to blurb.parse(open(filename).read()).
        """
        with open(filename, encoding='utf-8') as file:
            text = file.read()
        self.parse(text, metadata=metadata, filename=filename)

    def __str__(self) -> str:
        output = []
        add = output.append
        add_separator = False
        for metadata, body in self:
            if add_separator:
                add('\n..\n\n')
            else:
                add_separator = True
            if metadata:
                for name, value in sorted(metadata.items()):
                    add(f'.. {name}: {value}\n')
                add('\n')
            add(textwrap_body(body))
        return ''.join(output)

    def save(self, path: str) -> None:
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)

        text = str(self)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(text)

    @staticmethod
    def _parse_next_filename(filename: str) -> dict[str, str]:
        """Returns a dict of blurb metadata from a parsed "next" filename."""
        components = filename.split(os.sep)
        section, filename = components[-2:]
        section = unsanitize_section(section)
        assert section in sections, f'Unknown section {section}'

        fields = [x.strip() for x in filename.split('.')]
        assert len(fields) >= 4, f"Can't parse 'next' filename! filename {filename!r} fields {fields}"
        assert fields[-1] == 'rst'

        metadata = {'date': fields[0], 'nonce': fields[-2], 'section': section}

        for field in fields[1:-2]:
            for name in ('gh-issue', 'bpo'):
                _, got, value = field.partition(f'{name}-')
                if got:
                    metadata[name] = value.strip()
                    break
            else:
                assert False, f"Found unparsable field in 'next' filename: {field!r}"

        return metadata

    def load_next(self, filename: str) -> None:
        metadata = self._parse_next_filename(filename)
        o = type(self)()
        o.load(filename, metadata=metadata)
        assert len(o) == 1
        self.extend(o)

    def ensure_metadata(self) -> None:
        metadata, body = self[-1]
        assert 'section' in metadata
        for name, default in (
            ('gh-issue', '0'),
            ('bpo', '0'),
            ('date', sortable_datetime()),
            ('nonce', generate_nonce(body)),
            ):
            if name not in metadata:
                metadata[name] = default

    def _extract_next_filename(self) -> str:
        """Changes metadata!"""
        self.ensure_metadata()
        metadata, body = self[-1]
        metadata['section'] = sanitize_section(metadata['section'])
        metadata['root'] = root
        if int(metadata['gh-issue']) > 0:
            path = '{root}/Misc/NEWS.d/next/{section}/{date}.gh-issue-{gh-issue}.{nonce}.rst'.format_map(metadata)
        elif int(metadata['bpo']) > 0:
            # assume it's a GH issue number
            path = '{root}/Misc/NEWS.d/next/{section}/{date}.bpo-{bpo}.{nonce}.rst'.format_map(metadata)
        for name in ('root', 'section', 'date', 'gh-issue', 'bpo', 'nonce'):
            del metadata[name]
        return path

    def save_next(self) -> str:
        assert len(self) == 1
        blurb = type(self)()
        metadata, body = self[0]
        metadata = dict(metadata)
        blurb.append((metadata, body))
        filename = blurb._extract_next_filename()
        blurb.save(filename)
        return filename


def sortable_datetime() -> str:
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
