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

# TODO
#
# automatic git adds and removes

import base64
import glob
import hashlib
import os
import sys
import time

from blurb._template import (
    next_filename_unsanitize_sections, sanitize_section,
    sanitize_section_legacy, sections,
)

def sortable_datetime():
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())


def nonceify(body):
    digest = hashlib.md5(body.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)[0:6].decode('ascii')


def glob_blurbs(version):
    filenames = []
    base = os.path.join("Misc", "NEWS.d", version)
    if version != "next":
        wildcard = base + ".rst"
        filenames.extend(glob.glob(wildcard))
    else:
        sanitized_sections = (
                {sanitize_section(section) for section in sections} |
                {sanitize_section_legacy(section) for section in sections}
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


class BlurbError(RuntimeError):
    pass

def error(*a):
    s = " ".join(str(x) for x in a)
    sys.exit("Error: " + s)


if __name__ == '__main__':
    from blurb._cli import main

    main()
