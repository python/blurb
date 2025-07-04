#!/usr/bin/env python3
"""Command-line tool to manage CPython Misc/NEWS.d entries."""
##
## Part of the blurb package.
## Copyright 2015-2018 by Larry Hastings
##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##
## 1. Redistributions of source code must retain the above copyright
## notice, this list of conditions and the following disclaimer.
##
## 2. Redistributions in binary form must reproduce the above copyright
## notice, this list of conditions and the following disclaimer in the
## documentation and/or other materials provided with the distribution.
##
## 3. Neither the name of the copyright holder nor the names of its
## contributors may be used to endorse or promote products derived from
## this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
## IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
## TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
## PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
## TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
## PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
## LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
## NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
## SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
##
##
## Licensed to the Python Software Foundation under a contributor agreement.
##


import atexit
import base64
import builtins
import glob
import hashlib
import io
import itertools
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Optional, Annotated

from cyclopts import App, Parameter

from . import __version__


LOWEST_POSSIBLE_GH_ISSUE_NUMBER = 32426

#
# This template is the canonical list of acceptable section names!
# It is parsed internally into SECTIONS.  String replacement on the
# formatted comments is done later.  Beware when editing.
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

root = None  # Set by chdir_to_repo_root()
original_dir = None  # Set by main()
SECTIONS = sorted([
    line.partition("#.. section: ")[2].strip()
    for line in template.split('\n')
    if line.strip().startswith("#.. section: ")
])


_sanitize_section = {
    "C API": "C_API",
    "Core and Builtins": "Core_and_Builtins",
    "Tools/Demos": "Tools-Demos",
    }


def sanitize_section(section):
    """
    Clean up a section string, making it viable as a directory name.
    """
    return _sanitize_section.get(section, section)


def sanitize_section_legacy(section):
    """
    Clean up a section string, making it viable as a directory name (allow spaces).
    """
    return section.replace("/", "-")


_unsanitize_section = {
    "C_API": "C API",
    "Core_and_Builtins": "Core and Builtins",
    "Tools-Demos": "Tools/Demos",
    }


def unsanitize_section(section):
    return _unsanitize_section.get(section, section)

def next_filename_unsanitize_sections(filename):
    for key, value in _unsanitize_section.items():
        for separator in "/\\":
            key = f"{separator}{key}{separator}"
            value = f"{separator}{value}{separator}"
            filename = filename.replace(key, value)
    return filename


def textwrap_body(body, *, subsequent_indent=''):
    """
    Accepts either a string or an iterable of strings.
    (Iterable is assumed to be individual lines.)
    Returns a string.
    """
    if isinstance(body, str):
        text = body
    else:
        text = "\n".join(body).rstrip()

    # textwrap merges paragraphs, ARGH

    # step 1: remove trailing whitespace from individual lines
    #   (this means that empty lines will just have \n, no invisible whitespace)
    lines = []
    for line in text.split("\n"):
        lines.append(line.rstrip())
    text = "\n".join(lines)
    # step 2: break into paragraphs and wrap those
    paragraphs = text.split("\n\n")
    paragraphs2 = []
    kwargs = {'break_long_words': False, 'break_on_hyphens': False}
    if subsequent_indent:
        kwargs['subsequent_indent'] = subsequent_indent
    dont_reflow = False
    for paragraph in paragraphs:
        # don't reflow bulleted / numbered lists
        dont_reflow = dont_reflow or paragraph.startswith(("* ", "1. ", "#. "))
        if dont_reflow:
            initial = kwargs.get("initial_indent", "")
            subsequent = kwargs.get("subsequent_indent", "")
            if initial or subsequent:
                lines = [line.rstrip() for line in paragraph.split("\n")]
                indents = itertools.chain(
                    itertools.repeat(initial, 1),
                    itertools.repeat(subsequent),
                    )
                lines = [indent + line for indent, line in zip(indents, lines)]
                paragraph = "\n".join(lines)
            paragraphs2.append(paragraph)
        else:
            # Why do we reflow the text twice?  Because it can actually change
            # between the first and second reflows, and we want the text to
            # be stable.  The problem is that textwrap.wrap is deliberately
            # dumb about how many spaces follow a period in prose.
            #
            # We're reflowing at 76 columns, but let's pretend it's 30 for
            # illustration purposes.  If we give textwrap.wrap the following
            # text--ignore the line of 30 dashes, that's just to help you
            # with visualization:
            #
            #  ------------------------------
            #  xxxx xxxx xxxx xxxx xxxx.  xxxx
            #
            # The first textwrap.wrap will return this:
            #  "xxxx xxxx xxxx xxxx xxxx.\nxxxx"
            #
            # If we reflow it again, textwrap will rejoin the lines, but
            # only with one space after the period!  So this time it'll
            # all fit on one line, behold:
            #  ------------------------------
            #  xxxx xxxx xxxx xxxx xxxx. xxxx
            # and so it now returns:
            #  "xxxx xxxx xxxx xxxx xxxx. xxxx"
            #
            # textwrap.wrap supports trying to add two spaces after a peroid:
            #    https://docs.python.org/3/library/textwrap.html#textwrap.TextWrapper.fix_sentence_endings
            # But it doesn't work all that well, because it's not smart enough
            # to do a really good job.
            #
            # Since blurbs are eventually turned into ReST and rendered anyway,
            # and since the Zen says "In the face of ambiguity, refuse the
            # temptation to guess", I don't sweat it.  I run textwrap.wrap
            # twice, so it's stable, and this means occasionally it'll
            # convert two spaces to one space, no big deal.

            paragraph = "\n".join(textwrap.wrap(paragraph.strip(), width=76, **kwargs)).rstrip()
            paragraph = "\n".join(textwrap.wrap(paragraph.strip(), width=76, **kwargs)).rstrip()
            paragraphs2.append(paragraph)
        # don't reflow literal code blocks (I hope)
        dont_reflow = paragraph.endswith("::")
        if subsequent_indent:
            kwargs['initial_indent'] = subsequent_indent
    text = "\n\n".join(paragraphs2).rstrip()
    if not text.endswith("\n"):
        text += "\n"
    return text


def current_date():
    return time.strftime("%Y-%m-%d", time.localtime())

def sortable_datetime():
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())


def prompt(prompt):
    return input(f"[{prompt}> ")

def require_ok(prompt):
    prompt = f"[{prompt}> "
    while True:
        s = input(prompt).strip()
        if s == 'ok':
            return s

class pushd:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.previous_cwd = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, *args):
        os.chdir(self.previous_cwd)


def version_key(element):
    fields = list(element.split("."))
    if len(fields) == 1:
        return element

    # in sorted order,
    # 3.5.0a1 < 3.5.0b1 < 3.5.0rc1 < 3.5.0
    # so for sorting purposes we transform
    # "3.5." and "3.5.0" into "3.5.0zz0"
    last = fields.pop()
    for s in ("a", "b", "rc"):
        if s in last:
            last, stage, stage_version = last.partition(s)
            break
    else:
        stage = 'zz'
        stage_version = "0"

    fields.append(last)
    while len(fields) < 3:
        fields.append("0")

    fields.extend([stage, stage_version])
    fields = [s.rjust(6, "0") for s in fields]

    return ".".join(fields)


def nonceify(body):
    digest = hashlib.md5(body.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)[0:6].decode('ascii')


def glob_versions():
    with pushd("Misc/NEWS.d"):
        versions = []
        for wildcard in ("2.*.rst", "3.*.rst", "next"):
            files = [x.partition(".rst")[0] for x in glob.glob(wildcard)]
            versions.extend(files)
    xform = [version_key(x) for x in versions]
    xform.sort(reverse=True)
    versions = sorted(versions, key=version_key, reverse=True)
    return versions


def glob_blurbs(version):
    filenames = []
    base = os.path.join("Misc", "NEWS.d", version)
    if version != "next":
        wildcard = base + ".rst"
        filenames.extend(glob.glob(wildcard))
    else:
        sanitized_sections = (
                {sanitize_section(section) for section in SECTIONS} |
                {sanitize_section_legacy(section) for section in SECTIONS}
        )
        for section in sanitized_sections:
            wildcard = os.path.join(base, section, "*.rst")
            entries = glob.glob(wildcard)
            deletables = [x for x in entries if x.endswith("/README.rst")]
            for filename in deletables:
                entries.remove(filename)
            filenames.extend(entries)
    filenames.sort(reverse=True, key=next_filename_unsanitize_sections)
    return filenames


def printable_version(version):
    if version == "next":
        return version
    if "a" in version:
        return version.replace("a", " alpha ")
    if "b" in version:
        return version.replace("b", " beta ")
    if "rc" in version:
        return version.replace("rc", " release candidate ")
    return version + " final"


class BlurbError(RuntimeError):
    pass

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

class Blurbs(list):

    def parse(self, text, *, metadata=None, filename="input"):
        """
        Parses a string.  Appends a list of blurb ENTRIES to self, as tuples:
          (metadata, body)
        metadata is a dict.  body is a string.
        """

        metadata = metadata or {}
        body = []
        in_metadata = True

        line_number = None

        def throw(s):
            raise BlurbError(f"Error in {filename}:{line_number}:\n{s}")

        def finish_entry():
            nonlocal body
            nonlocal in_metadata
            nonlocal metadata
            nonlocal self

            if not body:
                throw("Blurb 'body' text must not be empty!")
            text = textwrap_body(body)
            for naughty_prefix in ("- ", "Issue #", "bpo-", "gh-", "gh-issue-"):
                if re.match(naughty_prefix, text, re.I):
                    throw("Blurb 'body' can't start with " + repr(naughty_prefix) + "!")

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
                        throw(f"Invalid {issue_keys[key]} number: {value!r}")

                if key == "gh-issue" and int(value) < LOWEST_POSSIBLE_GH_ISSUE_NUMBER:
                    throw(f"Invalid gh-issue number: {value!r} (must be >= {LOWEST_POSSIBLE_GH_ISSUE_NUMBER})")

                if key == "section":
                    if no_changes:
                        continue
                    if value not in SECTIONS:
                        throw(f"Invalid section {value!r}!  You must use one of the predefined sections.")

            if "gh-issue" not in metadata and "bpo" not in metadata:
                throw("'gh-issue:' or 'bpo:' must be specified in the metadata!")

            if 'section' not in metadata:
                throw("No 'section' specified.  You must provide one!")

            self.append((metadata, text))
            metadata = {}
            body = []
            in_metadata = True

        for line_number, line in enumerate(text.split("\n")):
            line = line.rstrip()
            if in_metadata:
                if line.startswith('..'):
                    line = line[2:].strip()
                    name, colon, value = line.partition(":")
                    assert colon
                    name = name.lower().strip()
                    value = value.strip()
                    if name in metadata:
                        throw("Blurb metadata sets " + repr(name) + " twice!")
                    metadata[name] = value
                    continue
                if line.startswith("#") or not line:
                    continue
                in_metadata = False

            if line == "..":
                finish_entry()
                continue
            body.append(line)

        finish_entry()

    def load(self, filename, *, metadata=None):
        """
Read a blurb file.

Broadly equivalent to blurb.parse(open(filename).read()).
        """
        with open(filename, encoding="utf-8") as file:
            text = file.read()
        self.parse(text, metadata=metadata, filename=filename)

    def __str__(self):
        output = []
        add = output.append
        add_separator = False
        for metadata, body in self:
            if add_separator:
                add("\n..\n\n")
            else:
                add_separator = True
            if metadata:
                for name, value in sorted(metadata.items()):
                    add(f".. {name}: {value}\n")
                add("\n")
            add(textwrap_body(body))
        return "".join(output)

    def save(self, path):
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)

        text = str(self)
        with open(path, "wt", encoding="utf-8") as file:
            file.write(text)

    @staticmethod
    def _parse_next_filename(filename):
        """
        Parses a "next" filename into its equivalent blurb metadata.
        Returns a dict.
        """
        components = filename.split(os.sep)
        section, filename = components[-2:]
        section = unsanitize_section(section)
        assert section in SECTIONS, f"Unknown section {section}"

        fields = [x.strip() for x in filename.split(".")]
        assert len(fields) >= 4, f"Can't parse 'next' filename! filename {filename!r} fields {fields}"
        assert fields[-1] == "rst"

        metadata = {"date": fields[0], "nonce": fields[-2], "section": section}

        for field in fields[1:-2]:
            for name in ("gh-issue", "bpo"):
                _, got, value = field.partition(name + "-")
                if got:
                    metadata[name] = value.strip()
                    break
            else:
                assert False, "Found unparsable field in 'next' filename: " + repr(field)

        return metadata

    def load_next(self, filename):
        metadata = self._parse_next_filename(filename)
        o = type(self)()
        o.load(filename, metadata=metadata)
        assert len(o) == 1
        self.extend(o)

    def ensure_metadata(self):
        metadata, body = self[-1]
        assert 'section' in metadata
        for name, default in (
            ("gh-issue", "0"),
            ("bpo", "0"),
            ("date", sortable_datetime()),
            ("nonce", nonceify(body)),
            ):
            if name not in metadata:
                metadata[name] = default

    def _extract_next_filename(self):
        """
        changes metadata!
        """
        self.ensure_metadata()
        metadata, body = self[-1]
        metadata['section'] = sanitize_section(metadata['section'])
        metadata['root'] = root
        if int(metadata["gh-issue"]) > 0:
            path = "{root}/Misc/NEWS.d/next/{section}/{date}.gh-issue-{gh-issue}.{nonce}.rst".format_map(metadata)
        elif int(metadata["bpo"]) > 0:
            # assume it's a GH issue number
            path = "{root}/Misc/NEWS.d/next/{section}/{date}.bpo-{bpo}.{nonce}.rst".format_map(metadata)
        for name in "root section date gh-issue bpo nonce".split():
            del metadata[name]
        return path


    def save_next(self):
        assert len(self) == 1
        blurb = type(self)()
        metadata, body = self[0]
        metadata = dict(metadata)
        blurb.append((metadata, body))
        filename = blurb._extract_next_filename()
        blurb.save(filename)
        return filename


readme_re = re.compile(r"This is \w+ version \d+\.\d+").match

def chdir_to_repo_root():
    global root

    # find the root of the local CPython repo
    # note that we can't ask git, because we might
    # be in an exported directory tree!

    # we intentionally start in a (probably nonexistant) subtree
    # the first thing the while loop does is .., basically
    path = os.path.abspath("garglemox")
    while True:
        next_path = os.path.dirname(path)
        if next_path == path:
            sys.exit('You\'re not inside a CPython repo right now!')
        path = next_path

        os.chdir(path)

        def test_first_line(filename, test):
            if not os.path.exists(filename):
                return False
            with open(filename, encoding="utf-8") as file:
                lines = file.read().split('\n')
                if not (lines and test(lines[0])):
                    return False
            return True

        if not (test_first_line("README", readme_re)
            or test_first_line("README.rst", readme_re)):
            continue

        if not test_first_line("LICENSE",  "A. HISTORY OF THE SOFTWARE".__eq__):
            continue
        if not os.path.exists("Include/Python.h"):
            continue
        if not os.path.exists("Python/ceval.c"):
            continue

        break

    root = path
    return root


def error(*a):
    s = " ".join(str(x) for x in a)
    sys.exit("Error: " + s)


app = App(
    help="Management tool for CPython Misc/NEWS and Misc/NEWS.d entries.",
    version_flags=["--version", "-V"],
    version=f"blurb version {__version__}",
)




@app.command(name="version")
def version():
    """Print blurb version."""
    print("blurb version", __version__)



@app.command(name="help")
def help(subcommand: Optional[str] = None):
    """Print help for subcommands.

    Parameters
    ----------
    subcommand : str, optional
        Subcommand to get help for. If not specified, shows all commands.
    """

    if subcommand:
        # Show help for specific subcommand
        app([subcommand, "--help"])
    else:
        # Show overall help
        app(["--help"])



def _find_blurb_dir():
    if os.path.isdir("blurb"):
        return "blurb"
    for path in glob.iglob("blurb-*"):
        if os.path.isdir(path):
            return path
    return None


def find_editor():
    for var in 'GIT_EDITOR', 'EDITOR':
        editor = os.environ.get(var)
        if editor is not None:
            return editor
    if sys.platform == 'win32':
        fallbacks = ['notepad.exe']
    else:
        fallbacks = ['/etc/alternatives/editor', 'nano']
    for fallback in fallbacks:
        if os.path.isabs(fallback):
            found_path = fallback
        else:
            found_path = shutil.which(fallback)
        if found_path and os.path.exists(found_path):
            return found_path
    error('Could not find an editor! Set the EDITOR environment variable.')




def prepare_template(tmp_path, issue_number, section_name, rst_content):
    """Write the template file with substitutions."""
    text = template

    # Ensure gh-issue line ends with space (or fill in issue number)
    issue_line = ".. gh-issue:"
    pattern = f"\n{issue_line}\n"
    if issue_number:
        replacement = f"\n{issue_line} {issue_number}\n"
    else:
        replacement = f"\n{issue_line} \n"
    text = text.replace(pattern, replacement)

    # Apply section substitution
    if section_name:
        text = text.replace(f"#.. section: {section_name}\n", f".. section: {section_name}\n")

    # Apply content substitution
    if rst_content:
        marker = "#################\n\n"
        text = text.replace(marker, f"{marker}{rst_content}\n")

    with open(tmp_path, "wt", encoding="utf-8") as file:
        file.write(text)


def get_editor_args(editor, tmp_path):
    """Prepare editor command arguments."""
    if shutil.which(editor):
        args = [editor]
    else:
        args = list(shlex.split(editor))
        if not shutil.which(args[0]):
            sys.exit(f"Invalid GIT_EDITOR / EDITOR value: {editor}")
    args.append(tmp_path)
    return args


def edit_until_valid(editor, tmp_path):
    """Run editor until we get a valid blurb."""
    args = get_editor_args(editor, tmp_path)

    while True:
        subprocess.run(args)

        blurb = Blurbs()
        try:
            blurb.load(tmp_path)
            if len(blurb) > 1:
                raise BlurbError("Too many entries! Don't specify '..' on a line by itself.")
            return blurb
        except BlurbError as e:
            print(f"\nError: {e}\n")
            try:
                prompt("Hit return to retry (or Ctrl-C to abort)")
            except KeyboardInterrupt:
                print()
                return None
            print()


def _extract_issue_number(issue):
    """Extract issue number from various formats like '12345', 'gh-12345', or GitHub URLs."""
    if issue is None:
        return None

    issue = raw_issue = str(issue).strip()
    if issue.startswith('gh-'):
        issue = issue[3:]
    if issue.isdigit():
        return issue

    match = re.match(r'^(?:https://)?github\.com/python/cpython/issues/(\d+)$', issue)
    if match is None:
        error(f"Invalid GitHub issue: {raw_issue}")
    return match.group(1)


def _extract_section_name(section):
    """Extract section name with smart matching."""
    if section is None:
        return None

    section = raw_section = section.strip()
    if not section:
        error("Empty section name!")

    matches = []
    # Try simple case-insensitive substring matching
    section_lower = section.lower()
    for section_name in SECTIONS:
        if section_lower in section_name.lower():
            matches.append(section_name)

    # If no matches, try more complex matching
    if not matches:
        matches = _find_smart_matches(section)

    if not matches:
        sections_list = '\n'.join(f'  - {s}' for s in SECTIONS)
        error(f"Invalid section name: {raw_section!r}\n\nValid sections are:\n{sections_list}")

    if len(matches) > 1:
        multiple_matches = ', '.join(map(repr, sorted(matches)))
        error(f"More than one match for: {raw_section!r}\nMatches: {multiple_matches}")

    return matches[0]


def _find_smart_matches(section):
    """Find matches using advanced pattern matching."""
    # Normalize separators
    sanitized = re.sub(r'[_\- /]', ' ', section).strip()
    if not sanitized:
        return []

    matches = []
    section_words = re.split(r'\s+', sanitized)

    # Build pattern to match against known sections
    section_pattern = r'[\s/]*'.join(map(re.escape, section_words))
    section_pattern = re.compile(section_pattern, re.I)

    for section_name in SECTIONS:
        if section_pattern.search(section_name):
            matches.append(section_name)

    # Special cases and aliases
    normalized = ''.join(section_words).lower()

    # Check special aliases
    aliases = {
        'api': 'C API',
        'capi': 'C API',
        'builtin': 'Core and Builtins',
        'builtins': 'Core and Builtins',
        'core': 'Core and Builtins',
        'demo': 'Tools/Demos',
        'demos': 'Tools/Demos',
        'tool': 'Tools/Demos',
        'tools': 'Tools/Demos',
    }

    for alias, section_name in aliases.items():
        if normalized.startswith(alias):
            if section_name not in matches:
                matches.append(section_name)

    # Try matching by removing spaces/separators
    if not matches:
        for section_name in SECTIONS:
            section_normalized = re.sub(r'[^a-zA-Z0-9]', '', section_name).lower()
            if section_normalized.startswith(normalized):
                matches.append(section_name)

    return matches


@app.command(name="add")
def add(*, issue: Annotated[Optional[str], Parameter(alias=["-i"])] = None,
        section: Annotated[Optional[str], Parameter(alias=["-s"])] = None,
        rst_on_stdin: bool = False):
    # This docstring template is formatted after the function definition.
    """Add a new Misc/NEWS entry.

    Opens an editor to create a new entry for Misc/NEWS unless all
    automation parameters are provided.

    Use -i/--issue to specify a GitHub issue number or link.
    Use -s/--section to specify the NEWS section (case insensitive with partial matching).

    Parameters
    ----------
    issue : str, optional
        GitHub issue number or URL (e.g. '12345', 'gh-12345', or 'https://github.com/python/cpython/issues/12345').
    section : str, optional
        NEWS section. Can use partial matching (e.g. 'lib' for 'Library'). One of {sections_csv}.
    rst_on_stdin : bool
        Read restructured text entry from stdin (requires issue and section).
    """

    # Extract and validate issue number
    issue_number = _extract_issue_number(issue) if issue else None
    if issue_number and int(issue_number) < LOWEST_POSSIBLE_GH_ISSUE_NUMBER:
        error(f"Invalid issue number: {issue_number} (must be >= {LOWEST_POSSIBLE_GH_ISSUE_NUMBER})")

    # Extract and validate section
    section_name = _extract_section_name(section) if section else None

    # Validate parameters for stdin mode
    if rst_on_stdin and (not issue_number or not section_name):
        error("--issue and --section required with --rst-on-stdin")

    chdir_to_repo_root()

    # Prepare content source
    if rst_on_stdin:
        rst_content = sys.stdin.read().strip()
        if not rst_content:
            error("No content provided on stdin")
        editor = None
    else:
        rst_content = None
        editor = find_editor()

    # Create temp file
    handle, tmp_path = tempfile.mkstemp(".rst")
    os.close(handle)
    atexit.register(lambda: os.path.exists(tmp_path) and os.unlink(tmp_path))

    # Prepare template
    prepare_template(tmp_path, issue_number, section_name, rst_content)

    # Get blurb content
    if editor:
        blurb = edit_until_valid(editor, tmp_path)
        if not blurb:
            return 1
    else:
        blurb = Blurbs()
        try:
            blurb.load(tmp_path)
        except BlurbError as e:
            error(str(e))

    # Save and commit
    path = blurb.save_next()
    git_add_files.append(path)
    flush_git_add_files()
    print(f"Ready for commit. {path!r} created and git added.")


add.__doc__ = add.__doc__.format(
    sections_csv=", ".join(repr(s) for s in SECTIONS)
)


@app.command(name="release")
def release(version: str):
    """Move all new blurbs to a single blurb file for the release.

    This is used by the release manager when cutting a new release.

    Parameters
    ----------
    version : str
        Version to release (use '.' for current directory name)
    """
    chdir_to_repo_root()

    if version == ".":
        version = os.path.basename(root)

    existing_filenames = glob_blurbs(version)
    if existing_filenames:
        error("Sorry, can't handle appending 'next' files to an existing version (yet).")

    output = f"Misc/NEWS.d/{version}.rst"
    filenames = glob_blurbs("next")
    blurbs = Blurbs()
    date = current_date()

    if not filenames:
        print(f"No blurbs found.  Setting {version} as having no changes.")
        body = f"There were no new changes in version {version}.\n"
        metadata = {"no changes": "True", "gh-issue": "0", "section": "Library", "date": date, "nonce": nonceify(body)}
        blurbs.append((metadata, body))
    else:
        count = len(filenames)
        print(f'Merging {count} blurbs to "{output}".')

        for filename in filenames:
            if not filename.endswith(".rst"):
                continue
            blurbs.load_next(filename)

        metadata = blurbs[0][0]

    metadata['release date'] = date
    print("Saving.")

    blurbs.save(output)
    git_add_files.append(output)
    flush_git_add_files()

    how_many = len(filenames)
    print(f"Removing {how_many} 'next' files from git.")
    git_rm_files.extend(filenames)
    flush_git_rm_files()

    # sanity check: ensuring that saving/reloading the merged blurb file works.
    blurbs2 = Blurbs()
    blurbs2.load(output)
    assert blurbs2 == blurbs, f"Reloading {output} isn't reproducible?!"

    print()
    print("Ready for commit.")



@app.command(name="merge")
def merge(
    output: Optional[str] = None,
    *,
    forced: Annotated[bool, Parameter(alias=["-f"])] = False
):
    """Merge all blurbs together into a single Misc/NEWS file.

    Parameters
    ----------
    output : str, optional
        Output file path (default: Misc/NEWS)
    forced : bool, optional
        Force overwrite without prompting (-f)
    """
    chdir_to_repo_root()

    if output:
        output = os.path.join(original_dir, output)
    else:
        output = "Misc/NEWS"

    versions = glob_versions()
    if not versions:
        sys.exit("You literally don't have ANY blurbs to merge together!")

    if os.path.exists(output) and not forced:
        builtins.print("You already have a", repr(output), "file.")
        require_ok("Type ok to overwrite")

    write_news(output, versions=versions)


def write_news(output, *, versions):
    buff = io.StringIO()

    def print(*a, sep=" "):
        s = sep.join(str(x) for x in a)
        return builtins.print(s, file=buff)

    print ("""
+++++++++++
Python News
+++++++++++

""".strip())

    for version in versions:
        filenames = glob_blurbs(version)

        blurbs = Blurbs()
        if version == "next":
            for filename in filenames:
                if os.path.basename(filename) == "README.rst":
                    continue
                blurbs.load_next(filename)
            if not blurbs:
                continue
            metadata = blurbs[0][0]
            metadata['release date'] = "XXXX-XX-XX"
        else:
            assert len(filenames) == 1
            blurbs.load(filenames[0])

        header = "What's New in Python " + printable_version(version) + "?"
        print()
        print(header)
        print("=" * len(header))
        print()


        metadata, body = blurbs[0]
        release_date = metadata["release date"]

        print(f"*Release date: {release_date}*")
        print()

        if "no changes" in metadata:
            print(body)
            print()
            continue

        last_section = None
        for metadata, body in blurbs:
            section = metadata['section']
            if last_section != section:
                last_section = section
                print(section)
                print("-" * len(section))
                print()
            if metadata.get("gh-issue"):
                issue_number = metadata['gh-issue']
                if int(issue_number):
                    body = "gh-" + issue_number + ": " + body
            elif metadata.get("bpo"):
                issue_number = metadata['bpo']
                if int(issue_number):
                    body = "bpo-" + issue_number + ": " + body

            body = "- " + body
            text = textwrap_body(body, subsequent_indent='  ')
            print(text)
    print()
    print("**(For information about older versions, consult the HISTORY file.)**")


    new_contents = buff.getvalue()

    # Only write in `output` if the contents are different
    # This speeds up subsequent Sphinx builds
    try:
        previous_contents = Path(output).read_text(encoding="UTF-8")
    except (FileNotFoundError, UnicodeError):
        previous_contents = None
    if new_contents != previous_contents:
        Path(output).write_text(new_contents, encoding="UTF-8")
    else:
        builtins.print(output, "is already up to date")


git_add_files = []
def flush_git_add_files():
    if git_add_files:
        subprocess.run(["git", "add", "--force", *git_add_files]).check_returncode()
        git_add_files.clear()

git_rm_files = []
def flush_git_rm_files():
    if git_rm_files:
        try:
            subprocess.run(["git", "rm", "--quiet", "--force", *git_rm_files]).check_returncode()
        except subprocess.CalledProcessError:
            pass

        # clean up
        for path in git_rm_files:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

        git_rm_files.clear()


@app.command(name="populate")
def populate():
    """Creates and populates the Misc/NEWS.d directory tree."""
    chdir_to_repo_root()

    os.chdir("Misc")
    os.makedirs("NEWS.d/next", exist_ok=True)

    for section in SECTIONS:
        dir_name = sanitize_section(section)
        dir_path = f"NEWS.d/next/{dir_name}"
        os.makedirs(dir_path, exist_ok=True)
        readme_path = f"NEWS.d/next/{dir_name}/README.rst"
        with open(readme_path, "wt", encoding="utf-8") as readme:
            readme.write(f"Put news entry ``blurb`` files for the *{section}* section in this directory.\n")
        git_add_files.append(dir_path)
        git_add_files.append(readme_path)
    flush_git_add_files()


@app.command(name="export")
def export():
    """Removes blurb data files, for building release tarballs/installers."""
    chdir_to_repo_root()

    os.chdir("Misc")
    shutil.rmtree("NEWS.d", ignore_errors=True)


@app.default
def default_command():
    """Default to 'add' command when no subcommand specified."""
    add()


def main():
    """Main entry point for the CLI using cyclopts."""
    global original_dir

    try:
        original_dir = os.getcwd()
        app()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit("Interrupted")
    except Exception as e:
        error(str(e))


if __name__ == '__main__':
    main()
