#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/detail/utils.sh

name=$1

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Worker already running!"
fi

touch log

nohup $base_dir/detail/workerd.sh $name 0<&- &>/dev/null &

pid=$!
echo $pid > .lock

create_repo $name $pid

info "To use it: ssh://$USER@$HOSTNAME:$PWD/$name.git"

