#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/detail/utils.sh

name=$1
path=$2

if echo $path | grep -q "ssh"; then
    die "Not supported yet!"
else
    tail -f $path/$name-workspace/log 2>/dev/null &
fi

