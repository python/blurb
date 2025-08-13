from blurb._merge import glob_blurbs


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
    filenames = glob_blurbs("next")

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
    filenames = glob_blurbs("next")

    # Assert
    assert filenames == expected
