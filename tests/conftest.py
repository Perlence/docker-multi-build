import pytest


@pytest.fixture
def isolated_filesystem(tmpdir):
    with tmpdir.as_cwd():
        yield tmpdir
