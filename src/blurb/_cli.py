from __future__ import annotations

import argparse
import inspect
import os
import re
import sys

import blurb

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import NoReturn

readme_re = re.compile(r'This is \w+ version \d+\.\d+').match


def error(msg: str, /) -> NoReturn:
    raise SystemExit(f'Error: {msg}')


def prompt(prompt: str, /) -> str:
    return input(f'[{prompt}> ')


def require_ok(prompt: str, /) -> str:
    prompt = f'[{prompt}> '
    while True:
        s = input(prompt).strip()
        if s == 'ok':
            return s


def build_parser() -> argparse.ArgumentParser:
    from blurb._add import add
    from blurb._export import export
    from blurb._merge import merge
    from blurb._populate import populate
    from blurb._release import release

    parser = argparse.ArgumentParser(
        prog='blurb',
        description='Management tool for CPython `Misc/NEWS` and `Misc/NEWS.d` entries.',
        epilog='If blurb is run without any arguments, this is equivalent to `blurb add`.',
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=f'blurb version {blurb.__version__}',
    )

    subparsers = parser.add_subparsers(
        dest='subcommand', metavar='subcommand', required=True
    )

    def add_subcommand(name: str, doc: str) -> argparse.ArgumentParser:
        doc = inspect.cleandoc(doc)
        return subparsers.add_parser(
            name,
            description=doc,
            help=doc.split('\n')[0],
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

    parser_add = add_subcommand('add', add.__doc__)
    parser_add.add_argument(
        '-i', '--issue', metavar='ISSUE', help='GitHub issue number or link'
    )
    parser_add.add_argument(
        '-s', '--section', metavar='SECTION', help='section name (case-insensitive)'
    )
    parser_add.set_defaults(func=lambda ns: add(issue=ns.issue, section=ns.section))

    parser_export = add_subcommand('export', export.__doc__)
    parser_export.set_defaults(func=lambda ns: export())

    parser_merge = add_subcommand('merge', merge.__doc__)
    parser_merge.add_argument(
        'output', nargs='?', help='where to write the NEWS file (default: Misc/NEWS)'
    )
    parser_merge.add_argument(
        '-f',
        '--forced',
        action='store_true',
        help='overwrite an existing file without prompting',
    )
    parser_merge.set_defaults(func=lambda ns: merge(ns.output, forced=ns.forced))

    parser_populate = add_subcommand('populate', populate.__doc__)
    parser_populate.set_defaults(func=lambda ns: populate())

    parser_release = add_subcommand('release', release.__doc__)
    parser_release.add_argument(
        'version', help="version number, or '.' to use the repo directory name"
    )
    parser_release.set_defaults(func=lambda ns: release(ns.version))

    return parser


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    if not args:
        args = ['add']
    # Keep the legacy 'help' and 'version' subcommands working as aliases.
    elif args[0] == 'help':
        print(
            "Warning: 'blurb help' is deprecated, use 'blurb --help' instead",
            file=sys.stderr,
        )
        args = [*args[1:2], '--help']
    elif args[0] == 'version':
        print(
            "Warning: 'blurb version' is deprecated, use 'blurb --version' instead",
            file=sys.stderr,
        )
        args = ['--version']

    parser = build_parser()
    ns = parser.parse_args(args)

    import blurb._merge

    blurb._merge.original_dir = os.getcwd()
    chdir_to_repo_root()

    ns.func(ns)


def chdir_to_repo_root() -> str:
    # find the root of the local CPython repo
    # note that we can't ask git, because we might
    # be in an exported directory tree!

    # we intentionally start in a (probably nonexistent) subtree
    # the first thing the while loop does is .., basically
    path = os.path.abspath('garglemox')
    while True:
        next_path = os.path.dirname(path)
        if next_path == path:
            raise SystemExit("You're not inside a CPython repo right now!")
        path = next_path

        os.chdir(path)

        def test_first_line(filename, test):
            if not os.path.exists(filename):
                return False
            with open(filename, encoding='utf-8') as file:
                lines = file.read().split('\n')
                if not (lines and test(lines[0])):
                    return False
            return True

        if not (
            test_first_line('README', readme_re)
            or test_first_line('README.rst', readme_re)
        ):
            continue

        if not test_first_line('LICENSE', 'A. HISTORY OF THE SOFTWARE'.__eq__):
            continue
        if not os.path.exists('Include/Python.h'):
            continue
        if not os.path.exists('Python/ceval.c'):
            continue

        break

    import blurb._blurb_file

    blurb._blurb_file.root = path
    return path
