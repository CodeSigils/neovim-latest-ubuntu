# Default Ubuntu version (override via --build-arg in CI).
# To update: fetch and pin the multi-arch manifest-list digest, not an
# arch-specific image digest. Verify the pinned digest supports both amd64
# and arm64 before pushing.
ARG UBUNTU_VERSION=26.04
ARG UBUNTU_SHA256=f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64
FROM ubuntu:${UBUNTU_VERSION}@sha256:${UBUNTU_SHA256}

ARG UBUNTU_VERSION
ARG UBUNTU_CODENAME="Resolute Raccoon"
ARG UBUNTU_SHA256
ARG UBUNTU_APT_SNAPSHOT=""
ARG DEBIAN_FRONTEND=noninteractive
LABEL description="Neovim build environment"
LABEL ubuntu.version="${UBUNTU_VERSION}"
LABEL ubuntu.codename="${UBUNTU_CODENAME}"
LABEL ubuntu.image.digest="sha256:${UBUNTU_SHA256}"

COPY deps/ /tmp/deps/

# hadolint ignore=DL3008,DL4006
# Scheduled builds intentionally consume current Ubuntu updates; replay builds
# use a snapshot. Bash supplies pipefail without a Docker-only SHELL directive.
RUN /bin/bash -o pipefail -c '\
      if [ -n "$UBUNTU_APT_SNAPSHOT" ]; then \
        sed -i -E "s|^URIs: .*|URIs: https://snapshot.ubuntu.com/ubuntu/${UBUNTU_APT_SNAPSHOT}/|" /etc/apt/sources.list.d/ubuntu.sources; \
      fi \
      && apt-get update \
      && grep -vE "^\\s*(#|$)" /tmp/deps/ubuntu-build-deps.txt | xargs -r apt-get install -y --no-install-recommends \
      && grep -vE "^\\s*(#|$)" /tmp/deps/ubuntu-ci-extra-deps.txt | xargs -r apt-get install -y --no-install-recommends \
      && rm -rf /var/lib/apt/lists/* /tmp/deps \
    '

COPY --chmod=755 build.sh /usr/local/bin/build-neovim
COPY scripts/install-package-docs.cmake /usr/local/share/neovim-packaging/install-package-docs.cmake

ENV OUTPUT_DIR=/output
ENV PACKAGE_DOCS_SCRIPT=/usr/local/share/neovim-packaging/install-package-docs.cmake

WORKDIR /tmp/build

# hadolint ignore=DL3025
CMD build-neovim "${VERSION:-}" "${OUTPUT_DIR:-/output}"
