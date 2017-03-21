import os
import time

import docker
import pytest
import requests

from docker_multi_build.config import BuildConfig, Dockerfile, BuildExport
from docker_multi_build.build import MultiBuilder, Builder, build_all, docker_copy


DIRNAME = os.path.dirname(__file__)


def test_docker_copy(isolated_filesystem, docker_in_docker):
    container = docker_in_docker.containers.run(
        'alpine:3.5',
        ['sh', '-c', 'mkdir /folder && echo beep > /boop && echo son > /folder/barp'],
        detach=True)

    # SRC_PATH specifies a file, DEST_PATH does not exist
    docker_copy(container, '/boop', 'boop')
    with open('boop') as fp:
        assert fp.read() == 'beep\n'

    # SRC_PATH specifies a file, DEST_PATH does not exist and ends with
    # '/'
    with pytest.raises(Exception) as exc_info:
        docker_copy(container, '/boop', 'beep/')
    assert "destination directory 'beep/' must exist" in str(exc_info.value)
    with open('boop') as fp:
        assert fp.read() == 'beep\n'

    # SRC_PATH specifies a file, DEST_PATH exists and is a file
    docker_copy(container, '/boop', 'boop')
    with open('boop') as fp:
        assert fp.read() == 'beep\n'

    # SRC_PATH specifies a file, DEST_PATH exists and is a directory
    os.mkdir('blarp')
    docker_copy(container, '/boop', 'blarp')
    with open('blarp/boop') as fp:
        assert fp.read() == 'beep\n'

    # SRC_PATH specifies a directory, DEST_PATH does not exist
    docker_copy(container, '/folder', 'folder')
    with open('folder/barp') as fp:
        assert fp.read() == 'son\n'

    # SRC_PATH specifies a directory, DEST_PATH exists and is a file
    with pytest.raises(Exception) as exc_info:
        docker_copy(container, '/folder', 'boop')
    assert 'cannot copy a directory to a file' in str(exc_info.value)

    # SRC_PATH specifies a directory and does not end with '/.',
    # DEST_PATH exists and is a directory
    os.mkdir('folder2')
    docker_copy(container, '/folder', 'folder2')
    with open('folder2/folder/barp') as fp:
        assert fp.read() == 'son\n'

    # SRC_PATH specifies a directory and ends with '/.', DEST_PATH
    # exists and is a directory
    os.mkdir('folder3')
    docker_copy(container, '/folder/.', 'folder3')
    with open('folder3/barp') as fp:
        assert fp.read() == 'son\n'


def test_write_dockerfile(isolated_filesystem):
    builder = Builder(client=None)

    config_with_inline = BuildConfig(
        tag='image_a',
        dockerfile=Dockerfile('FROM busybox\nCMD ["/bin/sh"]'),
    )
    builder.config = config_with_inline
    builder.write_dockerfile()
    with open('Dockerfile.image_a') as fp:
        assert fp.read() == config_with_inline.dockerfile.contents

    config_without_inline = BuildConfig(
        tag='image_b',
        dockerfile=Dockerfile(contents='...', name='Dockerfile.image_b'),
    )
    builder.config = config_without_inline
    builder.write_dockerfile()
    assert not os.path.exists('Dockerfile.image_b')


def test_build_all(isolated_filesystem, docker_in_docker):
    configs = {
        'download-dumb-init': BuildConfig(
            tag='download-dumb-init',
            dockerfile=Dockerfile("""\
FROM alpine:3.5
RUN apk add --no-cache ca-certificates curl
RUN mkdir /out \
    && cd /out \
    && curl -LO https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64
CMD ['bin/sh']
"""),
            exports=[BuildExport('/out/dumb-init_1.2.0_amd64', '.')]),

        'dumb-init': BuildConfig(
            tag='dumb-init',
            dockerfile=Dockerfile("""\
FROM alpine:3.5
COPY dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init
ENTRYPOINT ["dumb-init", "--"]
""")),
    }

    b = Builder(client=docker_in_docker)
    cb = MultiBuilder(builder=b)
    build_all(configs, multi_builder=cb)

    docker_in_docker.images.get('download-dumb-init')
    docker_in_docker.images.get('dumb-init')
    assert os.path.exists('dumb-init_1.2.0_amd64')


@pytest.fixture(scope='session')
def docker_in_docker():
    host_client = docker.from_env()
    host, port = '127.0.0.1', 2375

    name = 'docker_multi_build_dind'
    dind = host_client.containers.run(
        'docker:17.03.0-ce-dind', name=name, detach=True, privileged=True,
        volumes={'docker_multi_build_dind_data': {'bind': '/var/lib/docker', 'mode': 'rw'}},
        ports={'2375/tcp': (host, port)})

    docker_host = 'tcp://{}:{}'.format(host, port)
    client = docker.DockerClient(docker_host)
    while True:
        try:
            client.ping()
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)

    yield client

    dind.stop()
    dind.remove()
