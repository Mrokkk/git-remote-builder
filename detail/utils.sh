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

die() {
    echo -e "$star $@"
    exit 1
}

get_daemon_pid() {
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
    if [ $? -ne 0 ]; then
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

