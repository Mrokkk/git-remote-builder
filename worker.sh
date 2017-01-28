#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/detail/utils.sh

operation=$1
name=$2

case "$operation" in
    start)
        port=$(get_free_port)
        $base_dir/detail/workerd.sh $name $port &
        info "Started worker at port $port"
        info "To use it: server.sh add-worker -a $HOSTNAME -p $port -s \${building_script}"
        ;;
    stop)
        port=$(get_server_port $name .)
        if [ "$port" == "" ]; then
            die "No such worker!"
        fi
        echo "stop" > /dev/tcp/localhost/$port
        if [ $? ]; then
            info "Stopped worker with PID $pid"
        fi
        ;;
    rm|remove)
        info "Not supported yet!"
        ;;
    st|status)
        port=$(get_server_port $name .)
        if [ $port ]; then
            info "$name: running"
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

