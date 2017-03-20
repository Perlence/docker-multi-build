from os import path

import docker
import pytest

from docker_multi_build.config import BuildConfig, BuildExport
from docker_multi_build.build import MultiBuilder, Builder, build_all


DIRNAME = path.dirname(__file__)


def test_build_all(isolated_filesystem, docker_in_docker):
    configs = {
        'download-dumb-init': BuildConfig(
            tag='download-dumb-init',
            dockerfile="""\
FROM alpine:3.5
RUN apk add --no-cache ca-certificates curl
RUN mkdir /out \
    && cd /out \
    && curl -LO https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64
CMD ['bin/sh']
""",
            exports=[BuildExport('/out/dumb-init_1.2.0_amd64', '.')]),
        'dumb-init': BuildConfig(
            tag='dumb-init',
            dockerfile="""\
FROM alpine:3.5
COPY dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init
ENTRYPOINT ["dumb-init", "--"]
"""),
    }

    b = Builder(client=docker_in_docker)
    cb = MultiBuilder(builder=b)
    build_all(configs, multi_builder=cb)

    docker_in_docker.images.get('download-dumb-init')
    docker_in_docker.images.get('dumb-init')
    assert path.exists('dumb-init_1.2.0_amd64')


@pytest.fixture
def docker_in_docker():
    host_client = docker.from_env()
    host, port = '127.0.0.1', 2375

    name = 'docker_multi_docker_dind'
    try:
        dind = host_client.containers.get(name)
    except docker.errors.NotFound:
        dind = host_client.containers.run('docker:17.03.0-ce-dind', name=name,
                                          detach=True, privileged=True,
                                          ports={'2375/tcp': (host, port)})
    else:
        dind.start()

    docker_host = 'tcp://{}:{}'.format(host, port)
    yield docker.DockerClient(docker_host)

    dind.stop()
