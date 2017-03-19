import io

from click.testing import CliRunner
import pytest

from docker_multi_build.config import BuildConfig, BuildExport, load

table_load = [(
    'image_a:\n',
    {
        'image_a': BuildConfig(
            tag='image_a',
            dockerfile='FROM busybox\nCMD ["/bin/true"]\n',
            context='.',
            args={},
            exports=[]),
     }
), (
    'image_a:\n'
    '  dockerfile: !inline |\n'
    '    FROM debian:jessie\n'
    '    CMD ["/bin/true"]\n'
    '  args:\n'
    '    beep: boop\n'
    '  exports:\n'
    '    - /out/dumb-init_1.2.0_amd64:vendor/\n',
    {
        'image_a': BuildConfig(
            tag='image_a',
            dockerfile='FROM debian:jessie\nCMD ["/bin/true"]\n',
            context='.',
            args={'beep': 'boop'},
            exports=[BuildExport('/out/dumb-init_1.2.0_amd64', 'vendor/')]),
    }
)]


@pytest.mark.parametrize('source, expected', table_load)
def test_load(dockerfile, source, expected):
    config_io = io.StringIO(source)
    loaded = load(config_io)
    assert loaded == expected


@pytest.fixture
def dockerfile():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('Dockerfile', 'w') as fp:
            fp.write('FROM busybox\nCMD ["/bin/true"]\n')
        yield 'Dockerfile'
