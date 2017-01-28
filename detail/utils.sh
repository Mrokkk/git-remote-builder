#!/bin/bash

star="\e[1;35m*\e[0m"

success="OK"
bad_message="BADM"
failed="FAIL"
start_transmission="START"
end_transmission="STOP"

info() {
    echo -e "$star $@"
}

error() {
    echo -e "$star $@"
}

die() {
    echo -e "$star $@"
    exit 1
}

get_server_port() {
    local name_=$1
    local workspace_=$(readlink -f $2)
    if [ -e $workspace_/$name_-workspace ]; then
        cat $workspace_/$name_-workspace/.lock 2>/dev/null
    fi
}

run_command() {
    local com=$@
    local log=/tmp/log-$(date +%s)
    info "Running: \"$com\""
    $com &>$log
    if [ ! $? ]; then
        cat $log
        info "Command \"$com\" FAILED"
    fi
    rm $log
}

get_free_port() {
    while true; do
        local port=$(((RANDOM % 20000) + 8000))
        if ! nc -z localhost $port; then
            echo $port
            break
        fi
    done
}

hostname_is_local() {
    if [ "$1" == "localhost" ] || [ "$1" == "$HOSTNAME" ] || [ "$1" == "127.0.0.1" ]; then
        return 0
    else
        return 1
    fi
}

