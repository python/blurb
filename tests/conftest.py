"""pytest configuration and fixtures."""

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher


@pytest.fixture
def fs():
    """Pyfakefs fixture compatible with pytest."""
    with Patcher() as patcher:
        yield patcher.fs
