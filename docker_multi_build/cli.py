import os

import click
import docker

from . import config
from . import build


CLI_DEFAULT_FILE = 'docker-multi-build.yml'


@click.command()
@click.option('-f', '--file', metavar='PATH', type=click.File(), default=CLI_DEFAULT_FILE,
              help='Specify an alternate multi-build file (default: {}).'.format(CLI_DEFAULT_FILE))
@click.option('-H', '--host', metavar='HOST', envvar='DOCKER_HOST', default=None,
              help='Daemon socket to connect to.')
@click.option('--tls', is_flag=True,
              help='Use TLS; implied by --tlsverify.')
@click.option('--tlscacert', metavar='CA_PATH', type=click.Path(exists=True),
              help='Trust certs signed only by this CA.')
@click.option('--tlscert', metavar='CLIENT_CERT_PATH', type=click.Path(exists=True),
              help='Path to TLS certificate file.')
@click.option('--tlskey', metavar='TLS_KEY_PATH', type=click.Path(exists=True),
              help='Path to TLS key file.')
@click.option('--tlsverify', envvar='DOCKER_TLS_VERIFY', is_flag=True,
              help='Use TLS and verify the remote.')
def cli(file, host, tls, tlscacert, tlscert, tlskey, tlsverify):
    configs = config.load(file)
    tls_config = load_tls_config(tls, tlscacert, tlscert, tlskey, tlsverify)
    client = docker.DockerClient(host, tls=tls_config)
    b = build.Builder(client)
    mb = build.MultiBuilder(builder=b)
    build.build_all(configs, multi_builder=mb)


def load_tls_config(tls, tlscacert, tlscert, tlskey, tlsverify):
    if not tls and not tlsverify:
        return
    docker_cert_path = os.getenv('DOCKER_CERT_PATH')
    if docker_cert_path:
        if not tlscacert:
            tlscacert = os.path.join(docker_cert_path, 'ca.pem')
        if not tlscert:
            tlscert = os.path.join(docker_cert_path, 'cert.pem')
        if not tlskey:
            tlskey = os.path.join(docker_cert_path, 'key.pem')
    return docker.tls.TLSConfig(
        client_cert=(tlscert, tlskey),
        ca_cert=tlscacert,
        verify=tlsverify)
