#!/bin/bash

name=$1
branch=$2
building_script=$3

trap trigger SIGUSR1

build_number=0

trigger() {
    echo
    echo "* $name build #$build_number @ `LANG=C date`"
    echo "* Output is written also to file: $PWD/log.$build_number"
    old_pwd=$PWD
    if [ ! -e $name ]; then
        git clone $name.git $name
    fi
    cd $name
    git fetch origin $branch
    git reset --hard origin/$branch
    git submodule update --init --recursive
    $building_script 2>&1 | tee $old_pwd/log.$build_number
    if [ "$?" == "0" ]; then
        echo "* Built passed!"
    else
        echo "* Built failed!"
    fi
    cd $old_pwd
    build_number=$((build_number+1))
}

while [[ true ]]; do
    sleep 2
done

