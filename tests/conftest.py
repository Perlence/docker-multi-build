from click.testing import CliRunner
import pytest


@pytest.fixture
def isolated_filesystem():
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        yield fs
