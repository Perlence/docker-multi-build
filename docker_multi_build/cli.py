import attr
import click

from . import build_config


CLI_DEFAULT_FILE = 'docker-multi-build.yml'


@click.command()
@click.option('-f', '--file', metavar='PATH', type=click.Path(exists=True), default=CLI_DEFAULT_FILE,
              help='Specify an alternate multi-build file (default: docker-multi-build.yml')
@click.pass_context
def cli(ctx, file):
    ctx.obj = CLI(file)


@attr.s
class CLI:
    file = attr.ib(default=CLI_DEFAULT_FILE)

    configs = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        with open(self.file) as fp:
            self.configs = build_config.load(fp)
