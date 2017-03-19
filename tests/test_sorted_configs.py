import attr

from docker_multi_build.config import BuildConfig, BuildExport
from docker_multi_build.sort_configs import (
    get_copied_paths, is_exported_file_copied, get_base_image, sort_configs)


def test_get_copied_paths():
    config = BuildConfig('image_a',
                         dockerfile='FROM busybox\nCOPY beep.txt /\nADD dist/ /dist/')
    assert list(get_copied_paths(config)) == ['beep.txt', 'dist/']


def test_is_exported_file_copied():
    config_a = BuildConfig('image_a', dockerfile='FROM busybox\nCOPY beep.txt /')
    config_b = BuildConfig('image_b', dockerfile='FROM busybox\nCMD ["/bin/true"]')
    assert not is_exported_file_copied(config_b, config_a)

    config_b = BuildConfig('image_b',
                           dockerfile='FROM busybox\n'
                                      'RUN mkdir /out && echo boop > /out/beep.txt\n'
                                      'CMD ["/bin/true"]\n',
                           exports=[BuildExport('/out/beep.txt', 'beep.txt')])
    assert is_exported_file_copied(config_b, config_a)

    config_b = BuildConfig('image_b',
                           dockerfile='FROM busybox\n'
                                      'RUN mkdir /out && echo boop > /out/beep.txt\n'
                                      'CMD ["/bin/true"]\n',
                           exports=[BuildExport('/out/beep.txt', '.')])
    assert is_exported_file_copied(config_b, config_a)

    config_a = BuildConfig('image_a', dockerfile='FROM busybox\nCOPY beeps/ .')
    config_b = BuildConfig('image_b',
                           dockerfile='FROM busybox\n'
                                      'RUN mkdir /out && echo beep > /out/beep.txt && echo boop > /out/boop.txt\n'
                                      'CMD ["/bin/true"]\n',
                           exports=[BuildExport('/out/.', 'beeps/')])
    assert is_exported_file_copied(config_b, config_a)


def test_get_base_image():
    config = BuildConfig('image_a',
                         dockerfile='FROM busybox')
    assert get_base_image(config) == 'busybox'

    config = attr.assoc(config, dockerfile='FROM busybox:latest')
    assert get_base_image(config) == 'busybox'

    config = attr.assoc(config, dockerfile='FROM busybox@00f017a8c2a6')
    assert get_base_image(config) == 'busybox'


def test_get_config_dependents():
    configs = {
        'image_a': BuildConfig(
            'image_a',
            dockerfile="""\
                FROM debian:jessie
                COPY wheelhouse/ wheelhouse/
                COPY dist/ wheelhouse/
                COPY dist/dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
            """),

        'build_dumb_init': BuildConfig(
            'build_dumb_init',
            exports=[BuildExport('/out/dumb-init_1.2.0_amd64', 'dist/')],
            dockerfile="""\
                FROM buildpack-deps:jessie

                RUN mkdir /out \
                    && cd /out \
                    && wget https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64
            """),

        'build_dep_wheels': BuildConfig(
            'build_dep_wheels',
            exports=[BuildExport('/out/.', 'wheelhouse/')],
            dockerfile="""\
                FROM builder
                COPY requirements.txt .
                COPY wheelhouse/ wheelhouse/
                RUN . py27/bin/activate \
                    && mkdir /out \
                    && pip wheel \
                       --wheel-dir=/out \
                       --find-links=wheelhouse \
                       -r requirements.txt
            """),

        'build_wheel': BuildConfig(
            'build_wheel',
            exports=[BuildExport('/out/.', 'dist/')],
            dockerfile="""\
                FROM builder

                COPY requirements.in .
                COPY setup.py .
                COPY package/ package/
                COPY MANIFEST.in .

                RUN . py27/bin/activate \
                    && mkdir /out \
                    && python setup.py bdist_wheel --dist-dir /out
            """),

        'builder': BuildConfig(
            'builder',
            dockerfile="""\
                FROM buildpack-deps:jessie

                RUN apt-get update \
                    && apt-get install -y --no-install-recommends \
                        libpython2.7-dev \
                        libxml2-dev \
                        libxslt1-dev \
                        python-pip \
                        python-wheel \
                        virtualenv \
                    && apt-get clean \
                    && rm -rf /var/lib/apt/lists/*

                WORKDIR /src

                RUN virtualenv py27 \
                    && . py27/bin/activate \
                    && pip install -U pip \
                    && pip install wheel
            """),
    }

    assert list(sort_configs(list(configs.values())).keys()) == [
        'build_dumb_init',
        'builder',
        'build_wheel',
        'build_dep_wheels',
        'image_a',
    ]
