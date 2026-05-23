# Pin to multi-arch manifest list digest so the same Containerfile works
# on both x86_64 and arm64 runners (Docker auto-selects per platform).
# To update: docker pull ubuntu:24.04, then get the manifest list digest with
# `docker inspect --format='{{index .RepoDigests 0}}' ubuntu:24.04`.
FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b

LABEL description="Neovim build environment"

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    ninja-build \
    gettext \
    cmake \
    curl \
    ca-certificates \
    git \
    build-essential \
    lua5.1 \
    file \
    sudo \
    && rm -rf /var/lib/apt/lists/*

COPY --chmod=755 build.sh /usr/local/bin/build-neovim

ENV VERSION=0.12.2 \
    OUTPUT_DIR=/output

WORKDIR /tmp/build

# hadolint ignore=DL3025
CMD build-neovim "${VERSION}" "${OUTPUT_DIR}"
