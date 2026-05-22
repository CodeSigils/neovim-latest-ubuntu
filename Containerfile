FROM ubuntu:24.04

LABEL description="Neovim build environment"

RUN apt-get update && apt-get install -y \
    ninja-build \
    gettext \
    cmake \
    curl \
    git \
    build-essential \
    lua5.1 \
    file \
    sudo \
    && rm -rf /var/lib/apt/lists/*

COPY build.sh /usr/local/bin/build-neovim

ENV VERSION=0.12.2
ENV OUTPUT_DIR=/output

WORKDIR /tmp/build

CMD ["build-neovim"]
