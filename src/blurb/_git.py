import os
import subprocess

git_add_files: list[str] = []
git_rm_files: list[str] = []


def flush_git_add_files() -> None:
    if not git_add_files:
        return
    args = ('git', 'add', '--force', *git_add_files)
    subprocess.run(args, check=True)
    git_add_files.clear()


def flush_git_rm_files() -> None:
    if not git_rm_files:
        return
    args = ('git', 'rm', '--quiet', '--force', *git_rm_files)
    subprocess.run(args, check=False)

    # clean up
    for path in git_rm_files:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    git_rm_files.clear()
