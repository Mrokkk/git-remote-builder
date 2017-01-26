#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
build_number=0
building_script=$workspace/build.sh
pipe=/tmp/$name-serverd-$(date +%s)

interrupt() {
    info "Shutting down server..."
    run_command rm $workspace/.lock
    run_command rm $pipe
    exit 0
}

trigger() {
    local branch=$1
    old_pwd=$PWD
    log=$old_pwd/log
    if [ ! -e $name ]; then
        run_command git clone $name.git $name
    fi
    cd $name
    run_command git fetch origin $branch
    run_command git checkout $branch
    run_command git reset --hard origin/$branch
    run_command git submodule update --init --recursive
    for remote in $(cat ../remotes); do
        run_command git push $remote $branch --force
    done
    cd $old_pwd
}

trap interrupt SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

echo $$ > .lock

run_command mknod $pipe p

create_repo $name $pipe

while [[ true ]]; do
    read branchname < $pipe
    trigger $branchname
done

