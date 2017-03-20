from setuptools import setup, find_packages

try:
    long_description = open("README.rst").read()
except IOError:
    long_description = ""

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
    install_requires=[
        'attr',
        'click>=6',
        'docker',
        'PyYAML',
    ],
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
