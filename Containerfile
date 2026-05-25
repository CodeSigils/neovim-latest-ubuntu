# Default Ubuntu version (override via --build-arg in CI).
# To update: docker pull ubuntu:${UBUNTU_VERSION}, then get the manifest list
# digest with `docker inspect --format='{{index .RepoDigests 0}}' ubuntu:${UBUNTU_VERSION}`.
ARG UBUNTU_VERSION=26.04
FROM ubuntu:${UBUNTU_VERSION}@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64

ARG UBUNTU_VERSION
ARG UBUNTU_CODENAME="Resolute Raccoon"
LABEL description="Neovim build environment"
LABEL ubuntu.version=${UBUNTU_VERSION}
LABEL ubuntu.codename=${UBUNTU_CODENAME}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY deps/ /tmp/deps/

# hadolint ignore=DL3008
RUN apt-get update \
    && grep -vE '^\s*(#|$)' /tmp/deps/ubuntu-build-deps.txt | xargs -r apt-get install -y --no-install-recommends \
    && grep -vE '^\s*(#|$)' /tmp/deps/ubuntu-ci-extra-deps.txt | xargs -r apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* /tmp/deps

COPY --chmod=755 build.sh /usr/local/bin/build-neovim

ENV VERSION=0.12.2 \
    OUTPUT_DIR=/output

WORKDIR /tmp/build

# hadolint ignore=DL3025
CMD build-neovim "${VERSION}" "${OUTPUT_DIR}"
