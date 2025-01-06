import glob
import os

import pytest

from blurb.blurb import Blurbs, pushd


class TestParserPasses:
    directory = "tests/pass"

    def filename_test(self, filename):
        b = Blurbs()
        b.load(filename)
        assert b
        if os.path.exists(filename + ".res"):
            with open(filename + ".res", encoding="utf-8") as file:
                expected = file.read()
            assert str(b) == expected

    def test_files(self):
        with pushd(self.directory):
            for filename in glob.glob("*"):
                if filename.endswith(".res"):
                    assert os.path.exists(filename[:-4]), filename
                    continue
                self.filename_test(filename)


class TestParserFailures(TestParserPasses):
    directory = "tests/fail"

    def filename_test(self, filename):
        b = Blurbs()
        with pytest.raises(Exception):
            b.load(filename)
