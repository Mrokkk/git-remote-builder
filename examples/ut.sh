#!/bin/bash

set -e

export TERM=xterm-256color

mkdir -p build && cd build
if [ ! -e Makefile ]; then
    cmake ..
fi
unbuffer make tests-run -j$(nproc) -l$(nproc)

