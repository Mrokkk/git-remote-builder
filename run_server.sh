#!/bin/bash

set -e

source utils.sh

operation=$1
name=$2
shift 2

while true; do
    case "$1" in
        -s|--building-script)
            building_script=${PWD}/$2
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
        ./runner.sh $name $building_script &
        info "Started runner with PID $!"
        ;;
    stop)
        ;;
    show)
        ;;
esac


