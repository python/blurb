# Changelog

## 2.1.0

- Add the `-i` / `--issue` option to the 'blurb add' command.
  This lets you pre-fill the `gh-issue` field in the template.

## 2.0.0

* Move 'blurb test' subcommand into test suite by @hugovk in https://github.com/python/blurb/pull/37
* Add support for Python 3.14 by @ezio-melotti in https://github.com/python/blurb/pull/40
* Validate gh-issue is int before checking range, and that gh-issue or bpo exists by @hugovk in https://github.com/python/blurb/pull/35
* Replace `safe_mkdir(path)` with `os.makedirs(path, exist_ok=True)` by @hugovk in https://github.com/python/blurb/pull/38
* Test version handling functions by @hugovk in https://github.com/python/blurb/pull/36
* CI: Lint and test via uv by @hugovk in https://github.com/python/blurb/pull/32

## 1.3.0

* Add support for Python 3.13 by @hugovk in https://github.com/python/blurb/pull/26
* Drop support for Python 3.8 by @hugovk in https://github.com/python/blurb/pull/27
* Generate digital attestations for PyPI (PEP 740) by @hugovk in https://github.com/python/blurb/pull/28
* Allow running blurb test from blurb-* directories by @hroncok in https://github.com/python/blurb/pull/24
* Add `version` subcommand by @hugovk in https://github.com/python/blurb/pull/29
* Generate `__version__` at build to avoid slow `importlib.metadata` import by @hugovk in https://github.com/python/blurb/pull/30

## 1.2.1

- Fix `python3 -m blurb`.
- Undocument removed `blurb split`.

## 1.2.0

- Replace spaces with underscores in news directory.
- Drop support for Python 3.7.
- Remove `blurb split` command.
- Replace `gh-issue-NNNN:` with `gh-NNNN:` in the output.
- Accept GitHub issues numbered only 32426 or above.
- Improve error checking when parsing a Blurb.
- Loosen README check for CPython forks.
- Move code from `python/core-workflow` to own `python/blurb` repo.
- Deploy to PyPI via Trusted Publishers.

## 1.1.0

- Support GitHub Issues in addition to b.p.o (bugs.python.org).
  If `gh-issue` is in the metadata, then the filename will contain
  `gh-issue-<number>` instead of `bpo-`.

## 1.0.7

- When word wrapping, don't break on long words or hyphens.
- Use the `-f` flag when adding **blurb** files to a Git
  commit.  This forces them to be added, even when the files
  might normally be ignored based on a `.gitignore` directive.
- Explicitly support the `-help` command-line option.
- Fix Travis CI integration.
