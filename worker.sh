#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/detail/utils.sh

operation=$1
name=$2

case "$operation" in
    start)
        nohup $base_dir/detail/workerd.sh $name 0<&- &>/dev/null &
        info "Started worker with PID $!"
        info "To use it: ssh://$USER@$HOSTNAME:$PWD/$name.git"
        ;;
    stop)
        pid=$(get_daemon_pid $name .)
        if [ "$pid" == "" ]; then
            die "No such worker!"
        fi
        kill $pid
        if [ "$?" == "0" ]; then
            info "Stopped worker with PID $pid"
        fi
        ;;
    rm|remove)
        info "Not supported yet!"
        ;;
    st|status)
        pid=$(get_daemon_pid $name .)
        if [ $pid ]; then
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

