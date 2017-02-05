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
[[ $2 ]] && source $2

[[ ! $name ]] && die "No project name given!"

clone_and_checkout="git clone -b $builder_branch https://github.com/mrokkk/git-remote-builder repo"
star_worker_and_read_port="port=\$(repo/worker.sh start $name | grep Started | awk '{print \$NF}')"
stop_server="cd $server_path; repo/server.sh stop $name"

server_workers_start() {
    info "Creating server and workers for project $name"
    worker_config=$(mktemp)
    for line in "${workers[@]}"; do
        read hostname location script <<< $line
        scripts+=("$script")
        if hostname_is_local $hostname; then
            run_command "mkdir -p $location && cd $location"
            run_command "$clone_and_checkout"
            run_command "$star_worker_and_read_port"
            run_command "echo \"$hostname $port $script\" >> $worker_config"
        else
            ssh $hostname "mkdir -p $location && cd $location
            $clone_and_checkout
            $star_worker_and_read_port
            echo \"$hostname \$port $server_path/$(basename $script)\" > worker"
            temp=$(mktemp)
            scp $hostname:$location/worker $temp
            cat $temp >> $worker_config
            rm $temp
        fi
    done
    sleep 3
    if hostname_is_local $server; then
       run_command "mkdir -p $server_path && cd $server_path"
       for script in "${scripts[@]}"; do
           run_command "cp $script ."
       done
       run_command "$clone_and_checkout"
       run_command "cp $worker_config ./workers"
       repo/server.sh start $name -c workers
       for job in "${jobs[@]}"; do
           read job_name building_script <<<$job
           repo/server.sh add_job $name -j job_name -s $building_script
       done
    else
        ssh $server "mkdir -p $server_path && cd $server_path
        $clone_and_checkout"
        run_command "scp $worker_config $server:$server_path/workers"
        for script in "${scripts[@]}"; do
            run_command "scp $script $server:$server_path/"
        done
        ssh $server "cd $server_path; repo/server.sh start $name -c workers"
    fi
    run_command "rm -f $worker_config"
    info "Now you can add path $server:$server_path/$name-workspace/$name.git to yours Git project remote"
    info "On every push to that remote, builds will be run"
}

server_workers_stop() {
    if hostname_is_local $server; then
        eval "$stop_server"
    else
        ssh $server "$stop_server"
    fi
    for line in "${workers[@]}"; do
        read hostname location script <<< $line
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
        read hostname location script <<< $line
        if hostname_is_local $hostname; then
            rm -rf $location
        else
            ssh $hostname "rm -rf $location"
        fi
    done
}

server_workers_help() {
    echo "Usage: server_compose.sh {command} {name} {config_file}
Available commands: start stop remove help"
}

eval "server_workers_$1"

