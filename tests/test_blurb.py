import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from blurb import blurb


UNCHANGED_SECTIONS = (
    "Library",
)


@pytest.mark.parametrize("section", UNCHANGED_SECTIONS)
def test_sanitize_section_no_change(section):
    sanitized = blurb.sanitize_section(section)
    assert sanitized == section


@pytest.mark.parametrize(
    "section, expected",
    (
        ("C API", "C_API"),
        ("Core and Builtins", "Core_and_Builtins"),
        ("Tools/Demos", "Tools-Demos"),
    ),
)
def test_sanitize_section_changed(section, expected):
    sanitized = blurb.sanitize_section(section)
    assert sanitized == expected


@pytest.mark.parametrize("section", UNCHANGED_SECTIONS)
def test_unsanitize_section_no_change(section):
    unsanitized = blurb.unsanitize_section(section)
    assert unsanitized == section


@pytest.mark.parametrize(
    "section, expected",
    (
        ("Tools-Demos", "Tools/Demos"),
    ),
)
def test_unsanitize_section_changed(section, expected):
    unsanitized = blurb.unsanitize_section(section)
    assert unsanitized == expected


def test_glob_blurbs_next(fs):
    # Arrange
    fake_news_entries = (
        "Misc/NEWS.d/next/Library/2022-04-11-18-34-33.gh-issue-11111.pC7gnM.rst",
        "Misc/NEWS.d/next/Core and Builtins/2023-03-17-12-09-45.gh-issue-33333.Pf_BI7.rst",
        "Misc/NEWS.d/next/Tools-Demos/2023-03-21-01-27-07.gh-issue-44444.2F1Byz.rst",
        "Misc/NEWS.d/next/C API/2023-03-27-22-09-07.gh-issue-66666.3SN8Bs.rst",
    )
    fake_readmes = (
        "Misc/NEWS.d/next/Library/README.rst",
        "Misc/NEWS.d/next/Core and Builtins/README.rst",
        "Misc/NEWS.d/next/Tools-Demos/README.rst",
        "Misc/NEWS.d/next/C API/README.rst",
    )
    for fn in fake_news_entries + fake_readmes:
        fs.create_file(fn)

    # Act
    filenames = blurb.glob_blurbs("next")

    # Assert
    assert set(filenames) == set(fake_news_entries)


def test_glob_blurbs_sort_order(fs):
    """
    It shouldn't make a difference to sorting whether
    section names have spaces or underscores.
    """
    # Arrange
    fake_news_entries = (
        "Misc/NEWS.d/next/Core and Builtins/2023-07-23-12-01-00.gh-issue-33331.Pf_BI1.rst",
        "Misc/NEWS.d/next/Core_and_Builtins/2023-07-23-12-02-00.gh-issue-33332.Pf_BI2.rst",
        "Misc/NEWS.d/next/Core and Builtins/2023-07-23-12-03-00.gh-issue-33333.Pf_BI3.rst",
        "Misc/NEWS.d/next/Core_and_Builtins/2023-07-23-12-04-00.gh-issue-33334.Pf_BI4.rst",
    )
    # As fake_news_entries, but reverse sorted by *filename* only
    expected = [
        "Misc/NEWS.d/next/Core_and_Builtins/2023-07-23-12-04-00.gh-issue-33334.Pf_BI4.rst",
        "Misc/NEWS.d/next/Core and Builtins/2023-07-23-12-03-00.gh-issue-33333.Pf_BI3.rst",
        "Misc/NEWS.d/next/Core_and_Builtins/2023-07-23-12-02-00.gh-issue-33332.Pf_BI2.rst",
        "Misc/NEWS.d/next/Core and Builtins/2023-07-23-12-01-00.gh-issue-33331.Pf_BI1.rst",
    ]
    fake_readmes = (
        "Misc/NEWS.d/next/Library/README.rst",
        "Misc/NEWS.d/next/Core and Builtins/README.rst",
        "Misc/NEWS.d/next/Tools-Demos/README.rst",
        "Misc/NEWS.d/next/C API/README.rst",
    )
    for fn in fake_news_entries + fake_readmes:
        fs.create_file(fn)

    # Act
    filenames = blurb.glob_blurbs("next")

    # Assert
    assert filenames == expected


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
    blurbs = blurb.Blurbs()

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
def test_extract_next_filename(news_entry, expected_path, fs):
    # Arrange
    fs.create_file(news_entry, contents="testing")
    blurb.root = "root"
    blurbs = blurb.Blurbs()
    blurbs.load_next(news_entry)

    # Act
    path = blurbs._extract_next_filename()

    # Assert
    assert path == expected_path


def test_version(capfd):
    # Act
    blurb.version()

    # Assert
    captured = capfd.readouterr()
    assert captured.out.startswith("blurb version ")


def test_parse():
    # Arrange
    contents = ".. gh-issue: 123456\n.. section: IDLE\nHello world!"
    blurbs = blurb.Blurbs()

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
            r"The gh-issue number must be 32426 or above, not a PR number",
        ),
        (
            ".. bpo: one-two\n.. section: IDLE\nHello world!",
            r"Invalid bpo issue number! \('one-two'\)",
        ),
        (
            ".. gh-issue: one-two\n.. section: IDLE\nHello world!",
            r"Invalid GitHub issue number! \('one-two'\)",
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
    ),
)
def test_parse_no_body(contents, expected_error):
    # Arrange
    blurbs = blurb.Blurbs()

    # Act / Assert
    with pytest.raises(blurb.BlurbError, match=expected_error):
        blurbs.parse(contents)
