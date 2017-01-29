#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/detail/utils.sh

operation=$1
name=$2

worker_start() {
    local port=$(get_free_port)
    $base_dir/detail/workerd.sh $name $port &
    info "Started worker at port $port"
    info "To use it: server.sh add-worker -a $HOSTNAME -p $port -s \${building_script}"
}

worker_stop() {
    local port=$(get_server_port $name .)
    if [ "$port" == "" ]; then
        die "No such worker!"
    fi
    echo "stop" > /dev/tcp/localhost/$port
    if [ $? ]; then
        info "Stopped worker with PID $pid"
    fi
}

worker_remove() {
    worker_stop
    rm -rf $name-workspace
}

worker_status() {
    local port=$(get_server_port $name .)
    if [ $port ]; then
        info "$name: running"
    fi
}

worker_list() {
    for d in $(ls -d $base_dir/*-workspace/); do
        if [ -e $d/.lock ]; then
            echo $(basename $d | sed 's/-.*//g')
        fi
    done
}

worker_help() {
    echo "Available commands:
    start \$name - starts worker with given name
    stop \$name - stops worker
    remove \$name - stops and removes data of worker
    status \$name - returns status of worker
    list - lists running workers"
}

eval "worker_$operation"

