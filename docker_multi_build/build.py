from concurrent import futures

import attr

from .sort_configs import sort_configs


MAX_WORKERS = None


def build_all(configs):
    all_dependents = sort_configs(list(configs.values()))
    with futures.ThreadPoolExecutor(MAX_WORKERS) as pool:
        builder = ConcurrentBuilder(pool)
        builder.build_all(configs, all_dependents)


@attr.s
class ConcurrentBuilder:
    pool = attr.ib()

    all_dependencies = attr.ib(init=False, repr=False)
    completed = attr.ib(default=attr.Factory(set), repr=False)

    def build_all(self, configs, all_dependents):
        self.all_dependencies = self.setup_dependencies(all_dependents)
        self.completed = set()
        to_run = set(configs)
        while self.completed < to_run:
            fs = {self.pool.submit(build, configs[tag]): tag
                  for tag in self.ready_to_build()}
            for f in futures.as_completed(fs):
                f.result()
                tag = fs[f]
                self.completed.add(tag)

    def setup_dependencies(self, all_dependents):
        configs = {tag: [] for tag in all_dependents}
        for tag, dependents in all_dependents.items():
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


def build(config):
    print('Building image from', config)
