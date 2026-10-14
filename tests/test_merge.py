from pathlib import Path

from blurb._merge import write_news


def test_write_news_renders_cve(fs):
    # Arrange
    base = 'Misc/NEWS.d/next'
    fs.create_file(
        f'{base}/Security/2026-10-14-00-00-00.gh-issue-135661.abc123.rst',
        contents='.. cve: CVE-2025-6069\n\nFix a security issue.\n',
    )
    fs.create_file(
        f'{base}/Security/2026-10-14-00-00-01.gh-issue-135660.abc124.rst',
        contents='Fix another security issue without a CVE.\n',
    )
    fs.create_file(
        f'{base}/Library/2026-10-14-00-00-01.gh-issue-135662.abc125.rst',
        contents='Fix a library issue.\n',
    )

    # Act
    write_news('NEWS', versions=['next'])

    # Assert
    text = Path('NEWS').read_text(encoding='utf-8')
    assert '- gh-135661, CVE-2025-6069: Fix a security issue.\n' in text
    assert '- gh-135660: Fix another security issue without a CVE.\n' in text
    assert '- gh-135662: Fix a library issue.\n' in text
