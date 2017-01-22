#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
sleep_pid=
build_number=0
building_script=$workspace/build.sh

interrupt() {
    info "Shutting down server..."
    kill $sleep_pid > /dev/null
    rm $workspace/.lock
    exit 0
}

trigger() {
    old_pwd=$PWD
    log=$old_pwd/log
    kill -9 $sleep_pid
    branch=$(cat branchname)
    set -e
    if [ ! -e $name ]; then
        git clone $name.git $name
    fi
    cd $name
    git fetch origin $branch
    git checkout $branch
    git reset --hard origin/$branch
    git submodule update --init --recursive
    set +e
    for remote in $(cat ../remotes); do
        echo "Pushing to $remote..."
        git push $remote $branch --force
    done
    cd $old_pwd
}

trap interrupt SIGINT SIGTERM SIGHUP
trap trigger SIGUSR1

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

echo $$ > .lock

create_repo $name $$

while [[ true ]]; do
    sleep infinity &
    sleep_pid=$!
    wait $sleep_pid 2>/dev/null
done

