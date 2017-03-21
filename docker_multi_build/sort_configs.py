from collections import OrderedDict
import os
import shlex

from .dockerfile import parse


class DependencyError(Exception):
    pass


def sort_configs(configs):
    # Topological sort (Cormen/Tarjan algorithm) implementation is taken
    # from docker-compose
    unmarked = configs[:]
    temporary_marked = set()
    sorted_configs = []
    dependents = {config.tag: list(get_config_dependents(config, configs)) for config in configs}

    def visit(n):
        if n.tag in temporary_marked:
            if is_base_image(n, n):
                raise DependencyError('An image can not be based on itself: %s' % n.tag)
            # Skip other checks if image depends on itself
            if is_exported_file_copied(n, n):
                return
            raise DependencyError('Circular dependency between %s' % ' and '.join(temporary_marked))

        if n in unmarked:
            temporary_marked.add(n.tag)
            dependents
            for m in dependents[n.tag]:
                visit(m)
            temporary_marked.remove(n.tag)
            unmarked.remove(n)
            sorted_configs.insert(0, n)

    while unmarked:
        visit(unmarked[-1])

    return OrderedDict([(n.tag, dependents[n.tag]) for n in sorted_configs])


def get_config_dependents(config_a, all_configs):
    for config_b in all_configs:
        if is_base_image(config_a, config_b) or is_exported_file_copied(config_a, config_b):
            yield config_b


def is_base_image(config_a, config_b):
    return config_a.tag == get_base_image(config_b)


def get_base_image(config):
    instructions = parse(config.dockerfile.contents.splitlines())
    for instr in instructions:
        if instr.name == 'FROM':
            base_image = instr.arguments
            break
    else:
        raise ValueError("Dockerfile of image '{}' doesn't contain FROM-clause".format(config.tag))

    if '@' in base_image:
        parts = base_image.split('@', 1)
    elif ':' in base_image:
        parts = base_image.split(':', 1)
    else:
        parts = [base_image]
    return parts[0]


def is_exported_file_copied(config_a, config_b):
    for export in config_a.exports:
        exported_path = export.dest_path
        if exported_path == '.':
            exported_path = os.path.basename(export.container_src_path)
        exported_path = os.path.normpath(exported_path)

        for copied_path in get_copied_paths(config_b):
            copied_path = os.path.normpath(copied_path)
            if copied_path.startswith(exported_path):
                return True

    return False


def get_copied_paths(config):
    instructions = parse(config.dockerfile.contents.splitlines())
    for instr in instructions:
        if instr.name in ('COPY', 'ADD'):
            args = shlex.split(instr.arguments)
            yield args[0]
