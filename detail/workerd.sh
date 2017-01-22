#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
sleep_pid=
build_number=0
workspace=$PWD
building_script=$workspace/build.sh

interrupt() {
    info "Shutting down worker..."
    kill $sleep_pid > /dev/null
    rm $workspace/.lock
    exit 0
}

trigger() {
    old_pwd=$PWD
    log=$old_pwd/log
    kill -9 $sleep_pid
    branch=$(cat branchname)
    info "$name/$branch build #$build_number @ `LANG=C date`" > $log
    set -e
    if [ ! -e $name ]; then
        git clone $name.git $name
    fi
    cd $name
    git fetch origin $branch 2> /dev/null
    git checkout origin/$branch 2> /dev/null
    git submodule update --init --recursive 2> /dev/null
    set +e
    unbuffer $building_script 2>&1 >> $old_pwd/log
    if [ "$PIPESTATUS" == "0" ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m" >> $log
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m" >> $log
    fi
    cp $log $old_pwd/log.$build_number
    cd $old_pwd
    build_number=$((build_number+1))
}

trap interrupt SIGINT SIGTERM SIGHUP
trap trigger SIGUSR1

while [[ true ]]; do
    sleep infinity &
    sleep_pid=$!
    wait $sleep_pid 2>/dev/null
done

