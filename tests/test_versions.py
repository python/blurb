import pytest

from blurb._versions import glob_versions, printable_version, version_key


@pytest.mark.parametrize(
    "version1, version2",
    (
        ("2", "3"),
        ("3.5.0a1", "3.5.0b1"),
        ("3.5.0a1", "3.5.0rc1"),
        ("3.5.0a1", "3.5.0"),
        ("3.6.0b1", "3.6.0b2"),
        ("3.6.0b1", "3.6.0rc1"),
        ("3.6.0b1", "3.6.0"),
        ("3.7.0rc1", "3.7.0rc2"),
        ("3.7.0rc1", "3.7.0"),
        ("3.8", "3.8.1"),
    ),
)
def test_version_key(version1, version2):
    # Act
    key1 = version_key(version1)
    key2 = version_key(version2)

    # Assert
    assert key1 < key2


def test_glob_versions(fs):
    # Arrange
    fake_version_blurbs = (
        "Misc/NEWS.d/3.7.0.rst",
        "Misc/NEWS.d/3.7.0a1.rst",
        "Misc/NEWS.d/3.7.0a2.rst",
        "Misc/NEWS.d/3.7.0b1.rst",
        "Misc/NEWS.d/3.7.0b2.rst",
        "Misc/NEWS.d/3.7.0rc1.rst",
        "Misc/NEWS.d/3.7.0rc2.rst",
        "Misc/NEWS.d/3.9.0b1.rst",
        "Misc/NEWS.d/3.12.0a1.rst",
    )
    for fn in fake_version_blurbs:
        fs.create_file(fn)

    # Act
    versions = glob_versions()

    # Assert
    assert versions == [
        "3.12.0a1",
        "3.9.0b1",
        "3.7.0",
        "3.7.0rc2",
        "3.7.0rc1",
        "3.7.0b2",
        "3.7.0b1",
        "3.7.0a2",
        "3.7.0a1",
    ]


@pytest.mark.parametrize(
    "version, expected",
    (
        ("next", "next"),
        ("3.12.0a1", "3.12.0 alpha 1"),
        ("3.12.0b2", "3.12.0 beta 2"),
        ("3.12.0rc2", "3.12.0 release candidate 2"),
        ("3.12.0", "3.12.0 final"),
        ("3.12.1", "3.12.1 final"),
    ),
)
def test_printable_version(version, expected):
    # Act / Assert
    assert printable_version(version) == expected
