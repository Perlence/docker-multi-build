import io

import attr
from attr import NOTHING, Factory
from attr.validators import instance_of
import yaml


@attr.s
class Dockerfile:
    contents = attr.ib()
    name = attr.ib(default=None)


@attr.s
class BuildExport:
    container_src_path = attr.ib()
    dest_path = attr.ib()


@attr.s
class BuildConfig:
    tag = attr.ib()
    dockerfile = attr.ib(validator=instance_of(Dockerfile), repr=False)
    context = attr.ib(default='.')
    args = attr.ib(default=Factory(dict))
    exports = attr.ib(default=Factory(list))


def load(stream):
    data = yaml.load(stream, CustomLoader)
    if not isinstance(data, dict):
        raise ValueError("contents of 'docker-multi-build.yml' must be a dictionary")

    configs = {}
    for tag, raw_config in data.items():
        if raw_config is None:
            raw_config = {}
        config = _load_build_config(tag, raw_config)
        configs[tag] = config
    return configs


def _load_build_config(tag, raw_config):
    dockerfile = _load_dockerfile(raw_config.get('dockerfile', 'Dockerfile'))
    context = raw_config.get('context', BuildConfig.context.default)
    args = raw_config.get('args', NOTHING)
    raw_exports = raw_config.get('exports', NOTHING)
    if raw_exports is not NOTHING:
        exports = list(_load_exports(raw_exports))
    else:
        exports = NOTHING
    return BuildConfig(tag, dockerfile, context, args, exports)


def _load_dockerfile(path_or_stream):
    contents = ''
    name = None
    try:
        path_or_stream.read
    except AttributeError:
        with open(path_or_stream) as fp:
            contents = fp.read()
    else:
        contents = path_or_stream.read()
        try:
            name = path_or_stream.name
        except AttributeError:
            pass
    return Dockerfile(contents, name=name)


def _load_exports(raw_exports):
    for raw_export in raw_exports:
        parts = raw_export.split(':', 1)
        if not len(parts) == 2:
            raise ValueError("exports value must be a tuple")
        yield BuildExport(*parts)


class CustomLoader(yaml.Loader):
    pass


def inline_constructor(loader, node):
    # TODO: Raise an error when user tries to use '!inline' in other
    # place than 'dockerfile'
    return io.StringIO(node.value)


CustomLoader.add_constructor('!inline', inline_constructor)
