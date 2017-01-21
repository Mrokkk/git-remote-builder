#!/bin/bash

star="\e[1;35m*\e[0m"

info() {
    echo -e "$star $@"
}

die() {
    echo -e "$star $@"
    exit 1
}

