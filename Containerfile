# Pin to SHA256 digest for reproducible builds.
# Update periodically: docker pull ubuntu:24.04, then get the digest.
FROM ubuntu:24.04@sha256:cdb5fd928fced577cfecf12c8966e830fcdf42ee481fb0b91904eeddc2fe5eff

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

COPY build.sh /usr/local/bin/build-neovim
RUN chmod +x /usr/local/bin/build-neovim

ENV VERSION=0.12.2
ENV OUTPUT_DIR=/output

WORKDIR /tmp/build

# hadolint ignore=DL3025
CMD build-neovim "${VERSION}" "${OUTPUT_DIR}"
