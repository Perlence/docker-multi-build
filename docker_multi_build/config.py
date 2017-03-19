import io

import attr
from attr import NOTHING, Factory
import yaml


@attr.s
class BuildConfig:
    tag = attr.ib()
    dockerfile = attr.ib(repr=False)
    context = attr.ib(default='.')
    args = attr.ib(default=Factory(dict))
    exports = attr.ib(default=Factory(list))


@attr.s
class BuildExport:
    container_src_path = attr.ib()
    dest_path = attr.ib()


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
    try:
        path_or_stream.read
    except AttributeError:
        with open(path_or_stream) as fp:
            return fp.read()
    else:
        return path_or_stream.read()


def _load_exports(raw_exports):
    for raw_export in raw_exports:
        parts = raw_export.split(':', 1)
        if not len(parts) == 2:
            raise ValueError("exports value must be a tuple")
        yield BuildExport(*parts)


class CustomLoader(yaml.Loader):
    pass


def inline_constructor(loader, node):
    return io.StringIO(node.value)


CustomLoader.add_constructor('!inline', inline_constructor)
