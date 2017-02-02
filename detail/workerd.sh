#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
port=$2
tcp_in_pipe=/tmp/$(mktemp -u workerd.XXXXX)
tcp_out_pipe=/tmp/$(mktemp -u workerd.XXXXX)
repo_address=""
connected=
key=

workerd_stop() {
    info "Shutting down worker..."
    run_command "rm -rf $workspace/.lock"
    exec 3>&-
    exec 4>&-
    run_command "rm -rf $tcp_in_pipe $tcp_out_pipe"
    run_command "kill $ncat_pid"
    exit 0
}

workerd_test() {
    echo "$MSG_SUCCESS" >&3
}

workerd_connect() {
    if [ $connected ]; then
        echo "$MSG_FAILED" >&3
        info "Already connected to server!"
    fi
    key=$1
    repo_address=$2
    read -t $TIMEOUT line chars <&4
    info "Reading $chars bytes"
    if [ "$line" != "$MSG_START_TRANSMISSION" ]; then
        return
    fi
    rm -rf $building_script*
    dd of=$building_script.gz.enc bs=$chars count=1 &>/dev/null <&4
    [[ ! $? ]] && echo "$MSG_FAILED" >&3
    openssl base64 -d -k $key -in $building_script.gz.enc -out $building_script.gz
    run_command "gzip -d $building_script.gz"
    run_command "chmod +x $building_script"
    run_command "rm -f $building_script.gz*"
    echo "$MSG_SUCCESS" >&3
    info "Successfully read script!"
    connected=true
}

workerd_build() {
    local build_number=$1
    local branch=$2
    local commit=$3
    if [ ! -e build.sh ]; then
        error "No building script!"
        return
    fi
    old_pwd=$PWD
    log=$old_pwd/log
    if [ ! -d $name ]; then
        run_command "git clone $repo_address $name"
        if [ ! $? ]; then
            error "Cannot clone repo!"
            echo "$MSG_FAILED" >&3
        fi
    fi
    cd $name
    local temp_fifo=$(mktemp -u)
    run_command "mkfifo $temp_fifo"
    local log_port=$(get_free_port)
    exec {pipe}<>$temp_fifo
    ncat -l -p $log_port <&$pipe &
    pid=$!
    echo "$MSG_SUCCESS $log_port" >&3
    run_command "git fetch origin $branch"
    run_command "git checkout origin/$branch"
    run_command "git submodule update --init --recursive"
    info "$name build #$build_number @ `LANG=C date`" | tee $log >&$pipe
    unbuffer $building_script | tee -a $log >&$pipe
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m" | tee -a $log >&$pipe
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m" | tee -a $log >&$pipe
    fi
    echo "$MSG_STOP_TRANSMISSION" >&$pipe
    wait $pid
    exec {pipe}>&-
    rm -f $temp_fifo
    cp $log $old_pwd/log.$build_number
    cd $old_pwd
}

main() {
    while true; do
        read msg <&4
        if ! grep -Eq 'connect|test|stop' <<< $msg; then
            msg=$(openssl base64 -d -k $key <<< $msg)
        fi
        if [ "$msg" == "" ]; then
            error "Bad data"
            echo "$MSG_FAILED" >&3
            continue
        fi
        eval "workerd_$msg"
        if [ ! $? ]; then
            echo "$MSG_BAD_MESSAGE" >&3
        fi
    done
}

trap workerd_stop SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD
building_script=$workspace/build.sh

if [ -e .lock ]; then
    die "Worker already running at port $(cat .lock)!"
fi

set -e

run_command "touch log"
run_command "echo $port > .lock"
run_command mkfifo $tcp_in_pipe
run_command mkfifo $tcp_out_pipe
run_command "exec 3<>$tcp_in_pipe"
run_command "exec 4<>$tcp_out_pipe"
ncat -l -m 1 -k -p $port <&3 >&4 &
ncat_pid=$!

echo "$MSG_SUCCESS" >&3

set +e
main

