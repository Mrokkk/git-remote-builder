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
        -f|--force-remove)
            force=y
            shift
            ;;
        *)
            if [ "$1" == "" ]; then
                break
            fi
            die "Error parsing argument: $1"
            ;;
    esac
done

case "$operation" in
    start)
        port=$(get_free_port)
        $base_dir/detail/serverd.sh $name $port 0<&- &>$name-serverd-log &
        sleep 1
        read -t $timeout response < /dev/tcp/localhost/$port
        if [ "$response" == "$success" ]; then
            info "Started server at port $port"
        else
            die "Cannot start server!"
        fi
        ;;
    stop)
        port=$(get_server_port $name .)
        if [ "$port" == "" ]; then
            die "No such server!"
        fi
        echo "stop" > /dev/tcp/localhost/$port
        if [ $? ]; then
            info "Stopped server with PID $pid"
        fi
        ;;
    connect)
        server_port=$(get_server_port $name .)
        echo "connect $address $port $building_script" > /dev/tcp/localhost/$server_port
        read -t $timeout response < /dev/tcp/localhost/$server_port
        if [ "$response" == "$success" ]; then
            info "Added worker $address:$port for $name"
        else
            die "Cannot connect to worker!"
        fi
        ;;
    ls|list)
        for d in $(ls -d $base_dir/*-workspace/); do
            if [ -e $d/.lock ]; then
                echo $(basename $d | sed 's/-.*//g')
            fi
        done
        ;;
esac

