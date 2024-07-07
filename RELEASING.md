# Release Checklist

- [ ] check tests pass on [GitHub Actions](https://github.com/python/blurb/actions)
      [![GitHub Actions status](https://github.com/python/blurb/actions/workflows/test.yml/badge.svg)](https://github.com/python/blurb/actions/workflows/test.yml)

- [ ] Update [changelog](https://github.com/python/blurb/blob/main/CHANGELOG.md)

- [ ] Go to the [Releases page](https://github.com/python/blurb/releases) and

  - [ ] Click "Draft a new release"

  - [ ] Click "Choose a tag"

  - [ ] Type the next `vX.Y.Z` version and select "**Create new tag: vX.Y.Z** on publish"

  - [ ] Leave the "Release title" blank (it will be autofilled)

  - [ ] Click "Generate release notes" and amend as required

  - [ ] Click "Publish release"

- [ ] Check the tagged [GitHub Actions build](https://github.com/python/blurb/actions/workflows/release.yml)
      has deployed to [PyPI](https://pypi.org/project/blurb/#history)

- [ ] Check installation:

  ```bash
  python -m pip uninstall -y blurb && python -m pip install -U blurb && blurb help
  ```
