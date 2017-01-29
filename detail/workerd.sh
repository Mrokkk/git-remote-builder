#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
port=$2
tcp_in_pipe=/tmp/$name-$((RANDOM % 200))-workerd-in-$(date +%s)
tcp_out_pipe=/tmp/$name-$((RANDOM % 200))-workerd-out-$(date +%s)
repo_address=""

workerd_stop() {
    info "Shutting down worker..."
    run_command rm -rf $workspace/.lock
    exec 3>&-
    exec 4>&-
    run_command rm -rf $tcp_in_pipe $tcp_out_pipe
    run_command kill $ncat_pid
    exit 0
}

workerd_test() {
    echo "$MSG_SUCCESS" >&3
}

workerd_connect() {
    repo_address=$1
    read -t $TIMEOUT line <&4
    if [ "$line" != "$MSG_START_TRANSMISSION" ]; then
        return
    fi
    touch $building_script
    while read -t $TIMEOUT text <&4; do
        if [ "$text" == "$MSG_STOP_TRANSMISSION" ]; then
            break;
        fi
        echo $text >> $building_script
    done
    chmod +x $building_script
    echo "$MSG_SUCCESS" >&3
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
        run_command git clone $repo_address $name
    fi
    cd $name
    run_command git fetch origin $branch
    run_command git checkout origin/$branch
    run_command git submodule update --init --recursive
    info "$name build #$build_number @ `LANG=C date`" > $log
    unbuffer $building_script | tee -a $log
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m" >> $log
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m" >> $log
    fi
    cp $log $old_pwd/log.$build_number
    cd $old_pwd
}

main() {
    while true; do
        read msg <&4
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

