from os.path import join, dirname
from setuptools import setup, find_packages


def get_package_name(line):
    """Parse package name from 'requirements.in' line."""
    parts = line.strip().split('#egg=', 1)
    if len(parts) > 1:
        return parts[1]
    else:
        return parts[0]


DIRNAME = dirname(__file__)

try:
    long_description = open(join(DIRNAME, 'README.rst')).read()
except IOError:
    long_description = ''

with open(join(DIRNAME, 'requirements.in')) as fp:
    install_requires = [get_package_name(line) for line in fp]

setup(
    name="docker-multi-build",
    version="0.1.0",
    description="Multi-stage Docker builds",
    license="BSD",
    author="Sviatoslav Abakumov",
    author_email='dust.harvesting@gmail.com',
    url='https://github.com/Perlence/docker-multi-build',
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'docker-multi-build = docker_multi_build.cli:cli',
        ],
    },
    setup_requires=[
        'pytest-runner'
    ],
    install_requires=install_requires,
    tests_require=[
        'pytest',
    ],
    long_description=long_description,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ]
)
