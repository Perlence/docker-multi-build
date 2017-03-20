from concurrent import futures
from os import path
import re
import subprocess
import tarfile

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
        self.configs = configs
        self.all_dependents = all_dependents
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
    client = attr.ib(default=None, repr=False)

    config = attr.ib(init=False, repr=False)
    dockerfile_path = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        if self.client is None:
            self.client = docker.from_env()

    def build(self, config):
        self.config = config
        self.dockerfile_path = path.join(self.config.context, 'Dockerfile.' + self.config.tag)
        self.write_dockerfile()
        self.build_image()
        self.export()

    def write_dockerfile(self):
        with open(self.dockerfile_path, 'w') as fp:
            fp.write(self.config.dockerfile)

    def build_image(self, **kwargs):
        resp = self.client.api.build(path=self.config.context,
                                     dockerfile=path.basename(self.dockerfile_path),
                                     tag=self.config.tag,
                                     buildargs=self.config.args)
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
        for exported_path in self.config.exports:
            # TODO: Implement 'docker cp' in Python
            docker_host = self.client.api.base_url.replace('http://', 'tcp://')
            src_path = exported_path.container_src_path
            dest_path = path.join(self.config.context, exported_path.dest_path)
            process = subprocess.Popen(['docker', '-H', docker_host, 'cp',
                                        '{}:{}'.format(container.id, src_path),
                                        dest_path], stdout=subprocess.PIPE)
            with process:
                for line in process.stdout:
                    self.redirect_output(line)
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, process.args)
        container.remove()

    def redirect_output(self, line):
        print(self.config.tag, '|', line, end='')


def docker_copy(container, src_path, dest_path):
    tar_stream, _ = container.get_archive(src_path)
    with tarfile.TarFile(fileobj=tar_stream) as tf:
        member = tf.getmember(src_path)
        if not member.isdir():
            if not path.exists(dest_path):
                if dest_path.endswith('/'):
                    raise ValueError("the destination directory '{}' must exist".format(dest_path))
                tf.extract(member, dest_path)
            else:
                if path.isfile(dest_path):
                    tf.extract(member, dest_path)
                else:
                    # TODO: Join two clauses?
                    tf.extract(member, dest_path)
        else:
            if not path.exists(dest_path):
                ...
