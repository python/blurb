import glob
import os
import unittest

from blurb.blurb import Blurbs, pushd


class TestParserPasses(unittest.TestCase):
    directory = "tests/pass"

    def filename_test(self, filename):
        b = Blurbs()
        b.load(filename)
        self.assertTrue(b)
        if os.path.exists(filename + ".res"):
            with open(filename + ".res", encoding="utf-8") as file:
                expected = file.read()
            self.assertEqual(str(b), expected)

    def test_files(self):
        with pushd(self.directory):
            for filename in glob.glob("*"):
                if filename[-4:] == ".res":
                    self.assertTrue(os.path.exists(filename[:-4]), filename)
                    continue
                self.filename_test(filename)


class TestParserFailures(TestParserPasses):
    directory = "tests/fail"

    def filename_test(self, filename):
        b = Blurbs()
        with self.assertRaises(Exception):
            b.load(filename)
