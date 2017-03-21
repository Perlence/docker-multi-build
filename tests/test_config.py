import io
import os

import pytest
import yaml

from docker_multi_build.config import BuildConfig, Dockerfile, BuildExport, load

table_load = [(
    'image_a:\n',
    {
        'image_a': BuildConfig(
            tag='image_a',
            dockerfile=Dockerfile('FROM busybox\nCMD ["/bin/true"]\n', name='Dockerfile'),
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
            dockerfile=Dockerfile('FROM debian:jessie\nCMD ["/bin/true"]\n'),
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


def test_context_path(isolated_filesystem):
    name = 'docker-multi-build.yml'
    dockerfile_contents = 'FROM busybox'
    os.mkdir('beep')
    os.makedirs('blarp/beep')

    # context is set, dockerfile is not set
    raw_configs = {
        'image_a': {
            'context': 'beep',
        },
    }
    with open('beep/Dockerfile', 'w') as fp:
        fp.write(dockerfile_contents)
    with open(name, 'w+') as fp:
        yaml.dump(raw_configs, fp)
        fp.seek(0)
        configs = load(fp)
    assert configs['image_a'].context == 'beep'
    assert configs['image_a'].dockerfile == Dockerfile(dockerfile_contents, 'beep/Dockerfile')

    # context is not set, dockerfile is set
    raw_configs = {
        'image_a': {
            'dockerfile': 'Dockerfile.image_a',
        },
    }
    with open('Dockerfile.image_a', 'w') as fp:
        fp.write(dockerfile_contents)
    with open(name, 'w+') as fp:
        yaml.dump(raw_configs, fp)
        fp.seek(0)
        configs = load(fp)
    assert configs['image_a'].context == '.'
    assert configs['image_a'].dockerfile == Dockerfile(dockerfile_contents, 'Dockerfile.image_a')

    # context is set, dockerfile is set
    raw_configs = {
        'image_a': {
            'context': 'beep',
            'dockerfile': 'Dockerfile.boop',
        },
    }
    with open('beep/Dockerfile.boop', 'w') as fp:
        fp.write(dockerfile_contents)
    with open(name, 'w+') as fp:
        yaml.dump(raw_configs, fp)
        fp.seek(0)
        configs = load(fp)
    assert configs['image_a'].context == 'beep'
    assert configs['image_a'].dockerfile == Dockerfile(dockerfile_contents, 'beep/Dockerfile.boop')

    # context is set, dockerfile is set, custom docker-multi-build.yml
    # path
    name = 'blarp/docker-multi-build.yml'
    raw_configs = {
        'image_a': {
            'context': 'beep',
            'dockerfile': 'Dockerfile.boop',
        },
    }
    with open('blarp/beep/Dockerfile.boop', 'w') as fp:
        fp.write(dockerfile_contents)
    with open(name, 'w+') as fp:
        yaml.dump(raw_configs, fp)
        fp.seek(0)
        configs = load(fp)
    assert configs['image_a'].context == 'blarp/beep'
    assert configs['image_a'].dockerfile == Dockerfile(dockerfile_contents, 'blarp/beep/Dockerfile.boop')


@pytest.fixture
def dockerfile(isolated_filesystem):
    with open('Dockerfile', 'w') as fp:
        fp.write('FROM busybox\nCMD ["/bin/true"]\n')
    yield 'Dockerfile'
