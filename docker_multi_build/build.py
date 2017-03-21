from concurrent import futures
import os
from os import path
import re
import tarfile
import tempfile

import attr
import docker
import docker.utils
from docker.utils.json_stream import json_stream
from docker.errors import BuildError

from .sort_configs import sort_configs


def build_all(configs, multi_builder=None):
    if multi_builder is None:
        multi_builder = MultiBuilder()
    all_dependents = sort_configs(list(configs.values()))
    multi_builder.build_all(configs, all_dependents)


@attr.s
class MultiBuilder:
    builder = attr.ib(default=None)
    executor = attr.ib(default=None)

    configs = attr.ib(init=False, repr=False)
    all_dependents = attr.ib(init=False, repr=False)
    all_dependencies = attr.ib(init=False, repr=False)
    completed = attr.ib(default=attr.Factory(set), repr=False)

    def __attrs_post_init__(self):
        if self.builder is None:
            self.builder = Builder()
        if self.executor is None:
            self.executor = futures.ThreadPoolExecutor()

    def build_all(self, configs, all_dependents):
        self = attr.assoc(self, configs=configs, all_dependents=all_dependents)
        self.all_dependencies = self.setup_dependencies()
        self.completed = set()
        to_run = set(self.configs)
        with self.executor:
            while self.completed < to_run:
                fs = {self.executor.submit(self.builder.build, self.configs[tag]): tag
                      for tag in self.ready_to_build()}
                for f in futures.as_completed(fs):
                    f.result()
                    tag = fs[f]
                    self.completed.add(tag)

    def setup_dependencies(self):
        configs = {tag: [] for tag in self.all_dependents}
        for tag, dependents in self.all_dependents.items():
            for dependent in dependents:
                if dependent.tag == tag:
                    continue
                configs[dependent.tag].append(tag)
        return configs

    def ready_to_build(self):
        for tag in self.all_dependencies:
            if not self.is_image_built(tag) and self.are_dependencies_ready(tag):
                yield tag

    def is_image_built(self, tag):
        return tag in self.completed

    def are_dependencies_ready(self, tag):
        return all(dependency in self.completed
                   for dependency in self.all_dependencies[tag])


@attr.s
class Builder:
    client = attr.ib(default=attr.Factory(docker.from_env), repr=False)

    config = attr.ib(init=False, repr=False)
    dockerfile_path = attr.ib(init=False, repr=False)

    def build(self, config):
        self = attr.assoc(self, config=config)
        self.write_dockerfile()
        self.build_image()
        self.export()

    def write_dockerfile(self):
        if self.config.dockerfile.name is not None:
            return

        self.config.dockerfile.name = path.join(self.config.context, 'Dockerfile.' + self.config.tag)
        with open(self.config.dockerfile.name, 'w') as fp:
            fp.write(self.config.dockerfile.contents)

    def build_image(self, **kwargs):
        resp = self.client.api.build(path=self.config.context,
                                     dockerfile=path.basename(self.config.dockerfile.name),
                                     tag=self.config.tag,
                                     buildargs=self.config.args,
                                     rm=True)
        if isinstance(resp, str):
            return self.client.images.get(resp)

        events = []
        for event in json_stream(resp):
            # TODO: Redirect image pull logs
            line = event.get('stream', '')
            self.redirect_output(line)
            events.append(event)

        if not events:
            raise BuildError('Unknown')
        event = events[-1]
        if 'stream' in event:
            match = re.search(r'(Successfully built |sha256:)([0-9a-f]+)', event.get('stream', ''))
            if match:
                image_id = match.group(2)
                return self.client.images.get(image_id)

        raise BuildError(event.get('error') or event)

    def export(self):
        container = self.client.containers.create(self.config.tag)
        try:
            for exported_path in self.config.exports:
                docker_copy(container, exported_path.container_src_path, exported_path.dest_path)
        finally:
            container.remove()

    def redirect_output(self, line):
        print(self.config.tag, '|', line, end='')


def docker_copy(container, src_path, dest_path):
    copy_contents = False
    if src_path.endswith('/.'):
        src_path = path.dirname(src_path)
        copy_contents = True

    tar_stream, _ = container.get_archive(src_path)
    with tempfile.TemporaryFile() as tmp:
        for chunk in tar_stream:
            tmp.write(chunk)
        tmp.seek(0)

        with tarfile.TarFile(fileobj=tmp) as tf:
            member = tf.getmember(path.basename(src_path))

            if not member.isdir():
                if not path.exists(dest_path) and dest_path.endswith('/'):
                    raise Exception("the destination directory '{}' must exist".format(dest_path))
                if path.isdir(dest_path):
                    dest_path = path.join(dest_path, path.basename(member.name))
                member.name = dest_path
                tf.extract(member)

            else:
                dest_path_existed = path.exists(dest_path)
                if dest_path_existed:
                    if not path.isdir(dest_path):
                        raise Exception('cannot copy a directory to a file')
                else:
                    os.mkdir(dest_path)
                for m in tf.members:
                    if not copy_contents and dest_path_existed:
                        if m.name.startswith(member.name):
                            tf.extract(m, dest_path)
                    elif m != member and m.name.startswith(member.name):
                        m.name = m.name.replace(member.name + '/', '', 1)
                        tf.extract(m, dest_path)
