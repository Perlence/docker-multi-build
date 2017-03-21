import attr
import click

from . import config
from . import build


CLI_DEFAULT_FILE = 'docker-multi-build.yml'


@click.command()
@click.option('-f', '--file', metavar='PATH', type=click.Path(exists=True), default=CLI_DEFAULT_FILE,
              help='Specify an alternate multi-build file (default: {}'.format(CLI_DEFAULT_FILE))
def cli(file):
    cli = CLI(file)
    build.build_all(cli.configs)


@attr.s
class CLI:
    file = attr.ib(default=CLI_DEFAULT_FILE)

    configs = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        with open(self.file) as fp:
            self.configs = config.load(fp)
