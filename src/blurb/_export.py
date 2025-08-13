import os
import shutil

from blurb._cli import subcommand


@subcommand
def export() -> None:
    """Removes blurb data files, for building release tarballs/installers."""
    os.chdir('Misc')
    shutil.rmtree('NEWS.d', ignore_errors=True)
