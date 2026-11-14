def pytest_addoption(parser):
    parser.addoption("--dist-dir", default=None)

import uuid
from pathlib import Path
import pytest

@pytest.fixture
def tmp_path():
    # Avoid pytest's mode=0700 directories under the restricted Windows token.
    path=Path(__file__).parents[1]/'qa'/'test-runs'/uuid.uuid4().hex
    path.mkdir(parents=True)
    return path
