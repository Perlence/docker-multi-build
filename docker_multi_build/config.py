import io
import os

import attr
from attr import NOTHING, Factory
from attr.validators import instance_of
import yaml


@attr.s
class Dockerfile:
    contents = attr.ib(repr=False)
    name = attr.ib(default=None)


@attr.s
class BuildExport:
    container_src_path = attr.ib()
    dest_path = attr.ib()


@attr.s
class BuildConfig:
    tag = attr.ib()
    dockerfile = attr.ib(validator=instance_of(Dockerfile))
    context = attr.ib(default='.')
    args = attr.ib(default=Factory(dict))
    exports = attr.ib(default=Factory(list))


def load(stream):
    data = yaml.load(stream, CustomLoader)
    if not isinstance(data, dict):
        raise TypeError("contents of 'docker-multi-build.yml' must be a dictionary")

    try:
        stream_name = stream.name
    except AttributeError:
        default_context = '.'
    else:
        default_context = os.path.dirname(stream_name) or '.'

    configs = {}
    for tag, raw_config in data.items():
        if raw_config is None:
            raw_config = {}
        config = _load_build_config(tag, raw_config, default_context)
        configs[tag] = config
    return configs


def _load_build_config(tag, raw_config, default_context):
    context = _load_context(raw_config, default_context)
    dockerfile = _load_dockerfile(raw_config, context)
    args = raw_config.get('args', NOTHING)
    exports = _load_exports(raw_config)
    return BuildConfig(tag, dockerfile, context, args, exports)


def _load_context(raw_config, default_context):
    try:
        context = raw_config['context']
    except KeyError:
        context = default_context
    else:
        if not os.path.isabs(context):
            context = os.path.normpath(os.path.join(default_context, context))
    return context


def _load_dockerfile(raw_config, context):
    path_or_stream = raw_config.get('dockerfile', 'Dockerfile')
    name = None
    try:
        path_or_stream.read
    except AttributeError:
        name = os.path.normpath(os.path.join(context, path_or_stream))
        with open(name) as fp:
            contents = fp.read()
    else:
        contents = path_or_stream.read()
    return Dockerfile(contents, name=name)


def _load_exports(raw_config):
    try:
        raw_exports = raw_config['exports']
    except KeyError:
        return NOTHING
    else:
        return list(map(_parse_export, raw_exports))


def _parse_export(raw_export):
    parts = raw_export.split(':', 1)
    if not len(parts) == 2:
        raise ValueError("exports value must be a tuple")
    return BuildExport(*parts)


class CustomLoader(yaml.Loader):
    pass


def inline_constructor(loader, node):
    # TODO: Raise an error when user tries to use '!inline' in other
    # places than 'dockerfile'
    return io.StringIO(node.value)


CustomLoader.add_constructor('!inline', inline_constructor)
