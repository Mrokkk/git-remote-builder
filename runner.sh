#!/bin/bash

name=$1
branch=$2
building_script=$3

star="\e[1;35m*\e[0m"

trap trigger SIGUSR1

build_number=0

trigger() {
    echo
    echo -e "$star $name build #$build_number @ `LANG=C date`"
    echo -e "$star Output is written also to file: $PWD/log.$build_number"
    old_pwd=$PWD
    if [ ! -e $name ]; then
        git clone $name.git $name
    fi
    cd $name
    git fetch origin $branch
    git reset --hard origin/$branch
    git submodule update --init --recursive
    unbuffer $building_script 2>&1 | tee $old_pwd/log.$build_number
    if [ "$?" == "0" ]; then
        echo -e "$star Build #$build_number \e[1;32mPASSED\e[0m"
    else
        echo -e "$star Build #$build_number \e[1;31mFAILED\e[0m"
    fi
    cd $old_pwd
    build_number=$((build_number+1))
}

while [[ true ]]; do
    sleep infinity &
    wait
done

