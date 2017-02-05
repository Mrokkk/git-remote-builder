#!/bin/bash

TIMEOUT=10
MSG_SUCCESS="OK"
MSG_BAD_MESSAGE="BADM"
MSG_FAILED="FAIL"
MSG_START_TRANSMISSION="START"
MSG_STOP_TRANSMISSION="STOP"
CMD_BUILD="build"
CMD_CONNECT="connect"
CMD_TEST="test"
CMD_STOP="stop"

info() {
    echo -e "INFO: $@"
}

error() {
    echo -e "ERROR: $@"
}

die() {
    error "$@"
    exit 1
}

get_server_port() {
    local name_=$1
    local workspace_=$(readlink -f $2)
    if [ -e $workspace_/$name_-workspace ]; then
        cat $workspace_/$name_-workspace/.lock 2>/dev/null
    fi
}

get_worker_pid() {
    local name=$1
    local pid_file=$(readlink -f $2)/$name-workspace/.pid
    [[ -e $pid_file ]]; cat $pid_file
}

run_command() {
    local com=$@
    local log=$(mktemp)
    if ! eval "$com" &>$log; then
        cat $log
        error "Command \"$com\" FAILED"
        rm $log
        return 1
    fi
    rm $log
    return 0
}

get_free_port() {
    while true; do
        local port=$(((RANDOM % 20000) + 8000))
        if ! ncat -z localhost $port; then
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

