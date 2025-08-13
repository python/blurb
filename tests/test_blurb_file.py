import pytest
import time_machine

import blurb._blurb_file
from blurb._blurb_file import Blurbs, BlurbError, sortable_datetime


@pytest.mark.parametrize(
    "news_entry, expected_section",
    (
        (
            "Misc/NEWS.d/next/Library/2022-04-11-18-34-33.gh-issue-33333.pC7gnM.rst",
            "Library",
        ),
        (
            "Misc/NEWS.d/next/Core_and_Builtins/2023-03-17-12-09-45.gh-issue-44444.Pf_BI7.rst",
            "Core and Builtins",
        ),
        (
            "Misc/NEWS.d/next/Core and Builtins/2023-03-17-12-09-45.gh-issue-55555.Pf_BI7.rst",
            "Core and Builtins",
        ),
        (
            "Misc/NEWS.d/next/Tools-Demos/2023-03-21-01-27-07.gh-issue-66666.2F1Byz.rst",
            "Tools/Demos",
        ),
        (
            "Misc/NEWS.d/next/C_API/2023-03-27-22-09-07.gh-issue-77777.3SN8Bs.rst",
            "C API",
        ),
        (
            "Misc/NEWS.d/next/C API/2023-03-27-22-09-07.gh-issue-88888.3SN8Bs.rst",
            "C API",
        ),
    ),
)
def test_load_next(news_entry, expected_section, fs):
    # Arrange
    fs.create_file(news_entry, contents="testing")
    blurbs = Blurbs()

    # Act
    blurbs.load_next(news_entry)

    # Assert
    metadata = blurbs[0][0]
    assert metadata["section"] == expected_section


@pytest.mark.parametrize(
    "news_entry, expected_path",
    (
        (
            "Misc/NEWS.d/next/Library/2022-04-11-18-34-33.gh-issue-33333.pC7gnM.rst",
            "root/Misc/NEWS.d/next/Library/2022-04-11-18-34-33.gh-issue-33333.pC7gnM.rst",
        ),
        (
            "Misc/NEWS.d/next/Core and Builtins/2023-03-17-12-09-45.gh-issue-44444.Pf_BI7.rst",
            "root/Misc/NEWS.d/next/Core_and_Builtins/2023-03-17-12-09-45.gh-issue-44444.Pf_BI7.rst",
        ),
        (
            "Misc/NEWS.d/next/Tools-Demos/2023-03-21-01-27-07.gh-issue-55555.2F1Byz.rst",
            "root/Misc/NEWS.d/next/Tools-Demos/2023-03-21-01-27-07.gh-issue-55555.2F1Byz.rst",
        ),
        (
            "Misc/NEWS.d/next/C API/2023-03-27-22-09-07.gh-issue-66666.3SN8Bs.rst",
            "root/Misc/NEWS.d/next/C_API/2023-03-27-22-09-07.gh-issue-66666.3SN8Bs.rst",
        ),
    ),
)
def test_extract_next_filename(news_entry, expected_path, fs, monkeypatch):
    # Arrange
    monkeypatch.setattr(blurb._blurb_file, 'root', 'root')
    fs.create_file(news_entry, contents="testing")
    blurbs = Blurbs()
    blurbs.load_next(news_entry)

    # Act
    path = blurbs._extract_next_filename()

    # Assert
    assert path == expected_path


def test_parse():
    # Arrange
    contents = ".. gh-issue: 123456\n.. section: IDLE\nHello world!"
    blurbs = Blurbs()

    # Act
    blurbs.parse(contents)

    # Assert
    metadata, body = blurbs[0]
    assert metadata["gh-issue"] == "123456"
    assert metadata["section"] == "IDLE"
    assert body == "Hello world!\n"


@pytest.mark.parametrize(
    "contents, expected_error",
    (
        (
            "",
            r"Blurb 'body' text must not be empty!",
        ),
        (
            "gh-issue: Hello world!",
            r"Blurb 'body' can't start with 'gh-'!",
        ),
        (
            ".. gh-issue: 1\n.. section: IDLE\nHello world!",
            r"Invalid gh-issue number: '1' \(must be >= 32426\)",
        ),
        (
            ".. bpo: one-two\n.. section: IDLE\nHello world!",
            r"Invalid bpo number: 'one-two'",
        ),
        (
            ".. gh-issue: one-two\n.. section: IDLE\nHello world!",
            r"Invalid GitHub number: 'one-two'",
        ),
        (
            ".. gh-issue: 123456\n.. section: Funky Kong\nHello world!",
            r"Invalid section 'Funky Kong'!  You must use one of the predefined sections",
        ),
        (
            ".. gh-issue: 123456\nHello world!",
            r"No 'section' specified.  You must provide one!",
        ),
        (
            ".. gh-issue: 123456\n.. section: IDLE\n.. section: IDLE\nHello world!",
            r"Blurb metadata sets 'section' twice!",
        ),
        (
            ".. section: IDLE\nHello world!",
            r"'gh-issue:' or 'bpo:' must be specified in the metadata!",
        ),
    ),
)
def test_parse_no_body(contents, expected_error):
    # Arrange
    blurbs = Blurbs()

    # Act / Assert
    with pytest.raises(BlurbError, match=expected_error):
        blurbs.parse(contents)


@time_machine.travel("2025-01-07 16:28:41")
def test_sortable_datetime():
    assert sortable_datetime() == "2025-01-07-16-28-41"
