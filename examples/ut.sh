#!/bin/bash

set -e

mkdir -p build && cd build
if [ ! -e Makefile ]; then
    cmake ..
fi
make tests-run -j$(nproc) -l$(nproc)

