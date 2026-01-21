import os
import tempfile

import pytest

# Create isolated functions directory BEFORE any sgpt modules are imported.
# This prevents loading user's custom functions during tests.
_test_functions_dir = tempfile.mkdtemp(prefix="sgpt_test_functions_")
os.environ["TWCC_FUNCTIONS_PATH"] = _test_functions_dir


@pytest.fixture(autouse=True)
def mock_os_name(monkeypatch):
    monkeypatch.setattr(os, "name", "test")
