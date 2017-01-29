#!/bin/bash

set -e

base_dir=$(readlink -f `dirname $0`)
source $base_dir/detail/utils.sh

interrupt() {
    rm -f $worker_config $temp
}

trap interrupt SIGHUP SIGINT SIGTERM

builder_branch=$(git rev-parse --abbrev-ref HEAD)
scripts=()

operation=$1
name=$2
source $3

server_workers_start() {
    worker_config=$(mktemp)
    for line in "${workers[@]}"; do
        read worker_name hostname location script <<< $line
        scripts+=("$script")
        if hostname_is_local $hostname; then
            mkdir -p $location && cd $location
            git clone https://github.com/mrokkk/git-remote-builder repo && cd repo && git checkout $builder_branch && cd ..
            port=$(repo/worker.sh start $name | grep Started | awk '{print $NF}')
            echo "$hostname $port $script" >> $worker_config
        else
            ssh "$hostname" "mkdir -p $location && cd $location
            git clone https://github.com/mrokkk/git-remote-builder repo && cd repo && git checkout $builder_branch && cd ..
            port=\$(repo/worker.sh start $name | grep Started | awk '{print \$NF}')
            echo \"$hostname \$port $server_path/$(basename $script)\" > worker"
            temp=$(mktemp)
            scp $hostname:$location/worker $temp
            cat $temp >> $worker_config
            rm $temp
        fi
    done
    sleep 3
    if hostname_is_local $server; then
       mkdir -p $server_path && cd $server_path
       for script in "${scripts[@]}"; do
           cp $script .
       done
       git clone https://github.com/mrokkk/git-remote-builder repo && cd repo && git checkout $builder_branch && cd ..
       cp $worker_config ./workers
       repo/server.sh start $name -c workers
    else
        ssh $server "mkdir -p $server_path
        cd $server_path
        git clone https://github.com/mrokkk/git-remote-builder repo && cd repo && git checkout $builder_branch && cd .."
        scp $worker_config $server:$server_path/workers
        set -x
        for script in "${scripts[@]}"; do
            scp $script $server:$server_path/$(basename $script)
        done
        ssh $server "cd $server_path; repo/server.sh start $name -c workers"
    fi
    rm -f $worker_config
}

server_workers_stop() {
    if hostname_is_local $server; then
        cd $server_path
        repo/server.sh stop $name
    else
        ssh $server "cd $server_path
        repo/server.sh stop $name"
    fi
    for line in "${workers[@]}"; do
        read worker_name hostname location script <<< $line
        if hostname_is_local $hostname; then
            cd $location
            repo/worker.sh stop $name
        else
            ssh $hostname "cd $location
            repo/worker.sh stop $name"
        fi
    done
}

server_workers_remove() {
    server_workers_stop
    if hostname_is_local $server; then
        rm -rf $server_path
    else
        ssh $server "rm -rf $server_path"
    fi
    for line in "${workers[@]}"; do
        read worker_name hostname location script <<< $line
        if hostname_is_local $hostname; then
            rm -rf $location
        else
            ssh $hostname "rm -rf $location"
        fi
    done
}

eval "server_workers_$1"

