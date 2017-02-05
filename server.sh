#!/bin/bash

set -e

base_dir=$(readlink -f `dirname $0`)
source $base_dir/detail/utils.sh

operation=$1
name=$2
if [ "$name" != "" ]; then
    shift
fi
shift

while true; do
    case "$1" in
        -a|--address)
            address=$2
            shift 2
            ;;
        -p|--port)
            port=$2
            shift 2
            ;;
        -s|--building-script)
            building_script=$(readlink -f $2)
            shift 2
            ;;
        -c|--config)
            config_file=$2
            shift 2
            ;;
        -j|--job-name)
            job_name=$2
            shift 2
            ;;
        *)
            if [ "$1" == "" ]; then
                break
            fi
            die "Error parsing argument: $1"
            ;;
    esac
done

server_start() {
    if [ ! "$port" ]; then
        local port=$(get_free_port)
    fi
    $base_dir/detail/serverd.sh $name $port 0<&- &>$name-serverd-log &
    sleep 1
    read -t $TIMEOUT response < /dev/tcp/localhost/$port
    if [ "$response" == "$MSG_SUCCESS" ]; then
        info "Started server at port $port"
    else
        die "Cannot start server!"
    fi
    if [ "$config_file" ]; then
        while read address port building_script; do
            building_script=$(readlink -f $building_script)
            server_connect
        done < $config_file
    fi
}

server_stop() {
    local port=$(get_server_port $name .)
    if [ "$port" == "" ]; then
        die "No such server!"
    fi
    exec {serverd}<>/dev/tcp/localhost/$port
    echo "$MSG_START_TRANSMISSION" >&$serverd
    echo "$CMD_STOP" | openssl rsautl -encrypt -pubin -inkey $name-workspace/.pub | base64 >&$serverd
    echo "$MSG_STOP_TRANSMISSION" >&$serverd
    if [ $? ]; then
        info "Stopped server at port $port"
    fi
}

server_remove() {
    server_stop
    rm -rf $name*
}

server_connect() {
    local server_port=$(get_server_port $name .)
    exec {serverd}<>/dev/tcp/localhost/$server_port
    echo "$MSG_START_TRANSMISSION" >&$serverd
    echo "$CMD_CONNECT $address $port $building_script" | openssl rsautl -encrypt -pubin -inkey $name-workspace/.pub | base64 >&$serverd
    echo "$MSG_STOP_TRANSMISSION" >&$serverd
    read -t $TIMEOUT response <&$serverd
    if [ "$response" == "$MSG_SUCCESS" ]; then
        info "Added worker $address:$port for $name"
    else
        die "Cannot connect to worker!"
    fi
    exec {serverd}>&-
}

server_add_job() {
    local server_port=$(get_server_port $name .)
    exec {serverd}<>/dev/tcp/localhost/$server_port
    echo "$MSG_START_TRANSMISSION" >&$serverd
    echo "$CMD_ADD_JOB $job_name $building_script" | openssl rsautl -encrypt -pubin -inkey $name-workspace/.pub | base64 >&$serverd
    read -t $TIMEOUT response <&$serverd
    if [ "$response" == "$MSG_SUCCESS" ]; then
        info "Added job $job_name for $name"
    else
        die "Cannot add job!"
    fi
    exec {serverd}>&-
}

server_log() {
    less -r $name-serverd-log
}

server_list() {
    for d in $(ls -d $base_dir/*-workspace/); do
        if [ -e $d/.lock ]; then
            echo $(basename $d | sed 's/-.*//g')
        fi
    done
}

eval "server_$operation"

