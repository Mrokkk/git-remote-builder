#!/bin/bash

set -e

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

operation=$1
name=$2
shift 2

while true; do
    case "$1" in
        -s|--building-script)
            building_script=$(readlink -f $2)
            shift 2
            ;;
        -f|--force-remove)
            force=y
            shift
            ;;
        --)
            shift
            break
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
        $base_dir/runner.sh $name $building_script &
        info "Started runner with PID $!"
        ;;
    stop)
        pid=$(cat $base_dir/$name-workspace/.lock)
        if [ "$pid" == "" ]; then
            die "No such runner!"
        fi
        kill $pid
        ;;
    ls)
        ;;
esac

