Docker Multi Builder
====================

Multi Builder is a tool for multi-stage Docker builds. Think of it as Docker Compose for images. With Multi Builder, you
use a Multi Builder file to split images into build stages, specify dependences between them and thus better utilize
Docker image cache. Then, using a single command, you build all the images from your configuration.

A ``docker-multi-build.yml`` looks like this:

.. code-block:: yaml

   dumb-init:
     dockerfile: !inline |
       FROM alpine:3.5
       COPY dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
       RUN chmod +x /usr/local/bin/dumb-init
       ENTRYPOINT ["dumb-init", "--"]

   download-dumb-init:
     exports:
       - /out/dumb-init_1.2.0_amd64:.
     dockerfile: !inline |
       FROM alpine:3.5
       RUN apk add --no-cache ca-certificates curl
       RUN mkdir /out \
           && cd /out \
           && curl -LO https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64
       CMD ['bin/sh']

Check out docker-multi-build.yml_ for a more "real life" example of build configuration.

.. _docker-multi-build.yml: https://github.com/Perlence/docker-multi-builder/blob/master/docker-multi-build.yml

.. contents::


Rationale
---------

Building Docker images often involves building applications from source, downloading huge amount of packages from the
network. In first case, to build an application, we install build tools inside an image via Dockerfile instructions.
But after application is built, those tools are still present in the image and add to its size. In second case it just
takes much time for packages to download, and, most importantly, networks are known to be down.

One of the solutions is to create a *builder image*, install the build utilities there, feed it sources via volumes, run
the builder container to build the application, and get results from another volume. Also, more volumes can be added,
e.g. to cache downloaded dependencies. Then we ``COPY`` the application that was just built in another ``Dockerfile``,
build and distribute it.

This approach was detailed, for example, in `Deploying Python Applications with Docker - A Suggestion`_.

.. _Deploying Python Applications with Docker - A Suggestion: https://glyph.twistedmatrix.com/2015/03/docker-deploy-double-dutch.html

One of the drawbacks of this approach is that it does not utilize Docker cache for actual builds. The command that we
start in builder container is not cached and must be restarted every time we want to build an application.

Another drawback is that it requires some means of managing multiple Dockerfiles and keeping dependencies between them
in sync. Sometimes it's just hard to manipulate 4 or more Dockerfiles and keep correct order of their building.

First drawback can be resolved by running building command in a ``RUN`` step of builder Dockerfile, and copying
resulting paths from image via ``docker cp`` to host file system. Basically, start ``docker build`` every time, replace
``CMD`` with ``RUN``, and replace volumes with ``docker cp``.

Also to better utilize Docker cache we may want to split Dockerfiles into more stages, making some of them base images
of others. For example, we may create a custom base image with Python and use it both to fetch some package's
requirements, and to build distribution for this package. Each of these two steps can have different dependencies in
form of ``COPY`` instructions, and results of each of them will be cached.

Second drawback can be mitigated with a Makefile, where we write recipes of images and their dependencies.
Unfortunately, these Makefiles usually contain lots of boilerplate.

Docker Multi Builder is created to address these drawbacks and to provide an easy to use solution.


Installation
------------

Install ``docker-multi-build`` with ``pip``:

.. code-block:: bash

   pip install git+https://github.com/Perlence/docker-multi-build#egg=docker_multi_build

OR use a Docker image:

.. code-block:: bash

   docker pull Perlence/docker-multi-build:0.1


Usage
-----

``docker-multi-build [OPTIONS]``

Options:

- ``-f``, ``--file PATH`` Specify an alternate multi build file (default: ``docker-multi-build.yml``).
- ``--help`` Show this message and exit.

To use Multi Build in a container start the following command in a folder with ``docker-multi-build.yml``:

.. code-block:: bash

   docker run --rm -t \
       -v /var/run/docker.sock:/var/run/docker.sock \
       -v $PWD:/src \
       Perlence/docker-multi-build:0.1 -f /src/docker-multi-builder.yml


Multi Builder file reference
----------------------------

Top-level keys define a single build configuration and give it a name. The order in which builds will be started is
determined by the same topological sort algorithm that's used in Docker Compose. An image A depends on image B, if

- image B is base image of image A
- image B exports files that are copied by image A

If multiple builds can be started, e.g. two or more images don't have dependencies, or their dependencies have been
already built, they will be started concurrently.

Each build configuration can have the following settings.

exports
```````

A list of paths to be copied from resulting image to host.

.. code-block:: yaml

   exports:
     - /out/dumb-init:.

This setting instructs Multi Builder to create a container from resulting image, copy ``/out/dumb-init`` from inside of
it to ``.`` on the host and remove the container.

Please refer to `docker cp`_ documentation to see how given source container and destination paths will be handled.

.. _docker cp: https://docs.docker.com/engine/reference/commandline/cp/#extended-description

context
```````

A path to a directory containing a Dockerfile.

When the value supplied is a relative path, it is interpreted as relative to the location of the Compose file. This
directory is also the build context that is sent to the Docker daemon.

dockerfile
``````````

Either a path to a Dockerfile, or an in-line Dockerfile. Defaults to ``Dockerfile`` if not set.

If in-line Dockerfile is specified, then it will be saved to disk as ``Dockerfile.<tag>`` before sending the build
context to Docker daemon.

Example of a path:

.. code-block:: yaml

   dockerfile: Dockerfile.image_a

Example of in-line Dockerfile:

.. code-block:: yaml

   dockerfile: !inline |
     FROM busybox
     CMD ["/bin/true"]

args
````

Add build arguments, which are environment variables accessible only during the build process.

.. vim: tw=120 cc=121
