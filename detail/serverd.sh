#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
build_number=0
building_script=$workspace/build.sh
pipe=/tmp/$name-serverd-$(date +%s)

interrupt() {
    info "Shutting down server..."
    rm $workspace/.lock
    rm $pipe
    exit 0
}

trigger() {
    old_pwd=$PWD
    log=$old_pwd/log
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

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

echo $$ > .lock

mknod $pipe p

create_repo $name $pipe

while [[ true ]]; do
    read line < $pipe
    trigger
done

