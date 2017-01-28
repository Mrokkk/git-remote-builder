#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
build_number=0
tcp_in_pipe=/tmp/$name-intcp-$(date +%s)
tcp_out_pipe=/tmp/$name-outtcp-$(date +%s)

interrupt() {
    info "Shutting down worker..."
    run_command rm -rf $workspace/.lock
    exec 3>&-
    exec 4>&-
    run_command rm -rf $tcp_in_pipe $tcp_out_pipe
    run_command kill $ncat_pid
    exit 0
}

worker_test() {
    echo "$success" >&3
}

worker_connect() {
    repo_address=$1
    read -t 10 line <&4
    if [ "$line" != "$start_transmission" ]; then
        return
    fi
    touch $building_script
    while read text <&4; do
        if [ "$text" == "$end_transmission" ]; then
            break;
        fi
        echo $text >> $building_script
    done
    chmod +x $building_script
    echo "$success" >&3
}

worker_build() {
    local branch=$1
    local commit=$2
    old_pwd=$PWD
    log=$old_pwd/log
    if [ ! -e $name ]; then
        run_command git clone $repo_address $name
    fi
    cd $name
    run_command git fetch origin $branch
    run_command git checkout origin/$branch
    run_command git submodule update --init --recursive
    echo "$start_transmission" >&3
    info "$name build #$build_number @ `LANG=C date`" | tee $log >&3
    unbuffer $building_script 2>&1 | tee -a $log >&3
    if [ $? ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m" | tee -a $log >&3
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m" | tee -a $log >&3
    fi
    cp $log $old_pwd/log.$build_number
    cd $old_pwd
    build_number=$((build_number+1))
    echo "$end_transmission" >&3
}

tcp_server() {
    while true; do
        read msg <&4
        eval "worker_$msg"
        if [ ! $? ]; then
            echo "$bad_message" >&3
        fi
    done
}

trap interrupt SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD
building_script=$workspace/build.sh

if [ -e .lock ]; then
    die "Worker PID $(cat .lock) already running!"
fi

set -e

touch log
echo $$ > .lock

mknod $tcp_in_pipe p
mknod $tcp_out_pipe p

exec 3<>$tcp_in_pipe
exec 4<>$tcp_out_pipe
ncat -l -m 1 -k -p 8080 <&3 >&4 &
ncat_pid=$!

set +e
tcp_server

