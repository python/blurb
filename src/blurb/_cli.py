from __future__ import annotations

import inspect
import os
import re
import sys

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn, TypeAlias

    CommandFunc: TypeAlias = Callable[..., None]


subcommands: dict[str, CommandFunc] = {}
readme_re = re.compile(r'This is \w+ version \d+\.\d+').match


def error(msg: str, /) -> NoReturn:
    raise SystemExit(f'Error: {msg}')


def prompt(prompt: str, /) -> str:
    return input(f'[{prompt}> ')


def subcommand(fn: CommandFunc):
    global subcommands
    subcommands[fn.__name__] = fn
    return fn


def get_subcommand(subcommand: str, /) -> CommandFunc:
    fn = subcommands.get(subcommand)
    if not fn:
        error(f"Unknown subcommand: {subcommand}\nRun 'blurb help' for help.")
    return fn


@subcommand
def version() -> None:
    """Print blurb version."""
    print('blurb version', blurb.__version__)


@subcommand
def help(subcommand: str | None = None) -> None:
    """Print help for subcommands.

    Prints the help text for the specified subcommand.
    If subcommand is not specified, prints one-line summaries for every command.
    """

    if not subcommand:
        _blurb_help()
        raise SystemExit(0)

    fn = get_subcommand(subcommand)
    doc = fn.__doc__.strip()
    if not doc:
        error(f'help is broken, no docstring for {subcommand}')

    options = []
    positionals = []

    nesting = 0
    for name, p in inspect.signature(fn).parameters.items():
        if p.kind == inspect.Parameter.KEYWORD_ONLY:
            short_option = name[0]
            if isinstance(p.default, bool):
                options.append(f' [-{short_option}|--{name}]')
            else:
                if p.default is None:
                    metavar = f'{name.upper()}'
                else:
                    metavar = f'{name.upper()}[={p.default}]'
                options.append(f' [-{short_option}|--{name} {metavar}]')
        elif p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            positionals.append(' ')
            has_default = (p.default != inspect._empty)
            if has_default:
                positionals.append('[')
                nesting += 1
            positionals.append(f'<{name}>')
    positionals.append(']' * nesting)

    parameters = ''.join(options + positionals)
    print(f'blurb {subcommand}{parameters}')
    print()
    print(doc)
    raise SystemExit(0)


# Make 'blurb --help/--version/-V' work.
subcommands['--help'] = help
subcommands['--version'] = version
subcommands['-V'] = version


def _blurb_help() -> None:
    """Print default help for blurb."""

    print('blurb version', blurb.__version__)
    print()
    print('Management tool for CPython Misc/NEWS and Misc/NEWS.d entries.')
    print()
    print('Usage:')
    print('    blurb [subcommand] [options...]')
    print()

    # print list of subcommands
    summaries = []
    longest_name_len = -1
    for name, fn in subcommands.items():
        if name.startswith('-'):
            continue
        longest_name_len = max(longest_name_len, len(name))
        if not fn.__doc__:
            error(f'help is broken, no docstring for {fn.__name__}')
        fields = fn.__doc__.lstrip().split('\n')
        if not fields:
            first_line = '(no help available)'
        else:
            first_line = fields[0]
        summaries.append((name, first_line))
    summaries.sort()

    print('Available subcommands:')
    print()
    for name, summary in summaries:
        print(' ', name.ljust(longest_name_len), ' ', summary)

    print()
    print("If blurb is run without any arguments, this is equivalent to 'blurb add'.")


def main() -> None:
    global original_dir

    args = sys.argv[1:]

    if not args:
        args = ['add']
    elif args[0] == '-h':
        # slight hack
        args[0] = 'help'

    subcommand = args[0]
    args = args[1:]

    fn = get_subcommand(subcommand)

    # hack
    if fn in (help, version):
        raise SystemExit(fn(*args))

    try:
        original_dir = os.getcwd()
        chdir_to_repo_root()

        # map keyword arguments to options
        # we only handle boolean options
        # and they must have default values
        short_options = {}
        long_options = {}
        kwargs = {}
        for name, p in inspect.signature(fn).parameters.items():
            if p.kind == inspect.Parameter.KEYWORD_ONLY:
                if (p.default is not None
                        and not isinstance(p.default, (bool, str))):
                    raise SystemExit(
                        'blurb command-line processing cannot handle '
                        f'options of type {type(p.default).__qualname__}'
                    )

                kwargs[name] = p.default
                short_options[name[0]] = name
                long_options[name] = name

        filtered_args = []
        done_with_options = False
        consume_after = None

        def handle_option(s, dict):
            nonlocal consume_after
            name = dict.get(s, None)
            if not name:
                raise SystemExit(f'blurb: Unknown option for {subcommand}: "{s}"')

            value = kwargs[name]
            if isinstance(value, bool):
                kwargs[name] = not value
            else:
                consume_after = name

        for a in args:
            if consume_after:
                kwargs[consume_after] = a
                consume_after = None
                continue
            if done_with_options:
                filtered_args.append(a)
                continue
            if a.startswith('-'):
                if a == '--':
                    done_with_options = True
                elif a.startswith('--'):
                    handle_option(a[2:], long_options)
                else:
                    for s in a[1:]:
                        handle_option(s, short_options)
                continue
            filtered_args.append(a)

        if consume_after:
            raise SystemExit(
                f'Error: blurb: {subcommand} {consume_after} '
                'must be followed by an option argument'
            )

        raise SystemExit(fn(*filtered_args, **kwargs))
    except TypeError as e:
        # almost certainly wrong number of arguments.
        # count arguments of function and print appropriate error message.
        specified = len(args)
        required = optional = 0
        for p in inspect.signature(fn).parameters.values():
            if p.default == inspect._empty:
                required += 1
            else:
                optional += 1
        total = required + optional

        if required <= specified <= total:
            # whoops, must be a real type error, reraise
            raise e

        how_many = f'{specified} argument'
        if specified != 1:
            how_many += 's'

        if total == 0:
            middle = 'accepts no arguments'
        else:
            if total == required:
                middle = 'requires'
            else:
                plural = '' if required == 1 else 's'
                middle = f'requires at least {required} argument{plural} and at most'
            middle += f' {total} argument'
            if total != 1:
                middle += 's'

        print(f'Error: Wrong number of arguments!\n\nblurb {subcommand} {middle},\nand you specified {how_many}.')
        print()
        print('usage: ', end='')
        help(subcommand)


def chdir_to_repo_root() -> str:
    # find the root of the local CPython repo
    # note that we can't ask git, because we might
    # be in an exported directory tree!

    # we intentionally start in a (probably nonexistant) subtree
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

        if not (test_first_line('README', readme_re)
            or test_first_line('README.rst', readme_re)):
            continue

        if not test_first_line('LICENSE',  'A. HISTORY OF THE SOFTWARE'.__eq__):
            continue
        if not os.path.exists('Include/Python.h'):
            continue
        if not os.path.exists('Python/ceval.c'):
            continue

        break

    import blurb.blurb
    blurb.blurb.root = path
    return path
