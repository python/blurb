from __future__ import annotations

import glob
import sys

if sys.version_info[:2] >= (3, 11):
    from contextlib import chdir
else:
    import os

    class chdir:
        def __init__(self, path: str, /) -> None:
            self.path = path

        def __enter__(self) -> None:
            self.previous_cwd = os.getcwd()
            os.chdir(self.path)

        def __exit__(self, *args) -> None:
            os.chdir(self.previous_cwd)


def glob_versions() -> list[str]:
    versions = []
    with chdir('Misc/NEWS.d'):
        for wildcard in ('2.*.rst', '3.*.rst', 'next'):
            versions += [x.partition('.rst')[0] for x in glob.glob(wildcard)]
    versions.sort(key=version_key, reverse=True)
    return versions


def version_key(element: str, /) -> str:
    fields = list(element.split('.'))
    if len(fields) == 1:
        return element

    # in sorted order,
    # 3.5.0a1 < 3.5.0b1 < 3.5.0rc1 < 3.5.0
    # so for sorting purposes we transform
    # "3.5." and "3.5.0" into "3.5.0zz0"
    last = fields.pop()
    for s in ('a', 'b', 'rc'):
        if s in last:
            last, stage, stage_version = last.partition(s)
            break
    else:
        stage = 'zz'
        stage_version = '0'

    fields.append(last)
    while len(fields) < 3:
        fields.append('0')

    fields.extend([stage, stage_version])
    fields = [s.rjust(6, '0') for s in fields]

    return '.'.join(fields)


def printable_version(version: str, /) -> str:
    if version == 'next':
        return version
    if 'a' in version:
        return version.replace('a', ' alpha ')
    if 'b' in version:
        return version.replace('b', ' beta ')
    if 'rc' in version:
        return version.replace('rc', ' release candidate ')
    return version + ' final'
