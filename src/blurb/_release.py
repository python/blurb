from __future__ import annotations

import os
import time

import blurb.blurb
from blurb._blurb_file import Blurbs
from blurb._cli import error, subcommand
from blurb._git import (flush_git_add_files, flush_git_rm_files,
                        git_rm_files, git_add_files)
from blurb.blurb import glob_blurbs, nonceify


@subcommand
def release(version: str) -> None:
    """Move all new blurbs to a single blurb file for the release.

    This is used by the release manager when cutting a new release.
    """
    if version == '.':
        # harvest version number from dirname of repo
        # I remind you, we're in the Misc subdir right now
        version = os.path.basename(blurb.blurb.root)

    existing_filenames = glob_blurbs(version)
    if existing_filenames:
        error("Sorry, can't handle appending 'next' files to an existing version (yet).")

    output = f'Misc/NEWS.d/{version}.rst'
    filenames = glob_blurbs('next')
    blurbs = Blurbs()
    date = current_date()

    if not filenames:
        print(f'No blurbs found.  Setting {version} as having no changes.')
        body = f'There were no new changes in version {version}.\n'
        metadata = {'no changes': 'True', 'gh-issue': '0', 'section': 'Library', 'date': date, 'nonce': nonceify(body)}
        blurbs.append((metadata, body))
    else:
        count = len(filenames)
        print(f'Merging {count} blurbs to "{output}".')

        for filename in filenames:
            if not filename.endswith('.rst'):
                continue
            blurbs.load_next(filename)

        metadata = blurbs[0][0]

    metadata['release date'] = date
    print('Saving.')

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
    print('Ready for commit.')


def current_date() -> str:
    return time.strftime('%Y-%m-%d', time.localtime())
