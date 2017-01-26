#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
build_number=0
pipe=/tmp/$name-workerd-$(date +%s)

interrupt() {
    info "Shutting down worker..."
    rm $workspace/.lock
    rm $pipe
    exit 0
}

trigger() {
    local branch=$1
    old_pwd=$PWD
    log=$old_pwd/log
    info "$name/$branch build #$build_number @ `LANG=C date`" | tee $log
    if [ ! -e $name ]; then
        run_command git clone $name.git $name
    fi
    cd $name
    run_command git fetch origin $branch
    run_command git checkout origin/$branch
    run_command git submodule update --init --recursive
    unbuffer $building_script 2>&1 >> $old_pwd/log
    if [ $? -eq 0 ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m" >> $log
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m" >> $log
    fi
    cp $log $old_pwd/log.$build_number
    cd $old_pwd
    build_number=$((build_number+1))
}

trap interrupt SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD
building_script=$workspace/build.sh

if [ -e .lock ]; then
    die "Worker already running!"
fi

set -e

touch log

echo $$ > .lock

mknod $pipe p

create_repo $name $pipe

set +e

while [[ true ]]; do
    read branchname < $pipe
    trigger $branchname
done

