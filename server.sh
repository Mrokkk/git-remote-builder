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
        $base_dir/detail/serverd.sh $name $port & #0<&- &>$name-serverd-log
        info "Started server at port $port"
        ;;
    stop)
        pid=$(get_daemon_pid $name .)
        if [ "$pid" == "" ]; then
            die "No such server!"
        fi
        kill $pid
        if [ $? ]; then
            info "Stopped server with PID $pid"
        fi
        ;;
    add-worker)
        if [ ! $name-workspace/workers ]; then
            touch $name-workspace/workers
        fi
        echo $address $port $building_script >> $name-workspace/workers
        pid=$(get_daemon_pid $name .)
        kill -s SIGUSR1 $pid
        info "Added worker $address:$port for $name"
        ;;
    rm|remove)
        info "Not supported yet!"
        ;;
    st|status)
        info "Not supported yet!"
        ;;
    ls|list)
        for d in $(ls -d $base_dir/*-workspace/); do
            if [ -e $d/.lock ]; then
                echo $(basename $d | sed 's/-.*//g')
            fi
        done
        ;;
esac

