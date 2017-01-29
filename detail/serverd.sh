#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
port=$2
build_number=0
tcp_in_pipe=/tmp/$name-$((RANDOM % 200))-serverd-in-$(date +%s)
tcp_out_pipe=/tmp/$name-$((RANDOM % 200))-serverd-out-$(date +%s)
workers=()

serverd_stop() {
    info "Shutting down server..."
    run_command rm -rf $tcp_in_pipe $tcp_out_pipe $workspace/.lock
    run_command kill $ncat_pid
    exit 0
}

read_build_log() {
    local worker=$1
    local number=$2
    local log_name=${worker//\//-}
    info "Reading build log from $worker"
    exec {worker_fd}<>/dev/tcp/$worker
    read -t $TIMEOUT start_code <&${worker_fd}
    if [ "$start_code" != "$MSG_START_TRANSMISSION" ]; then
        return
    fi
    run_command "touch $log_name"
    while read -t $TIMEOUT line <&${worker_fd}; do
        if [ "$line" == "$MSG_STOP_TRANSMISSION" ]; then
            break
        fi
        echo $line >> $log_name
    done
    run_command "cp $log_name $log_name.$number"
}

serverd_build() {
    local branch=$1
    log=$PWD/log
    for worker in ${workers[@]}; do
        echo "build $build_number $branch" > /dev/tcp/$worker
        read_build_log $worker $build_number &
    done
    build_number=$((build_number+1))
}

serverd_connect() {
    info "Connecting to $1/$2 and sending building script $3"
    local worker_address=$1
    local worker_port=$2
    local building_script=$3
    local hostname=""
    if hostname_is_local $worker_address; then
        hostname=""
    else
        hostname="$worker_address:"
    fi
    echo "connect $hostname$workspace/$name.git
    $MSG_START_TRANSMISSION
    $(cat $building_script)
    $MSG_STOP_TRANSMISSION" > /dev/tcp/$worker_address/$worker_port
    if [ ! $? ]; then
        error "Cannot send data to worker!"
    fi
    read -t $TIMEOUT status </dev/tcp/$worker_address/$worker_port
    if [ "$status" != "$MSG_SUCCESS" ]; then
        error "Didn't connect to worker - no response!"
        echo "$failed" >&3
        return
    fi
    workers+=("$worker_address/$worker_port")
    echo "$MSG_SUCCESS" >&3
    info "Successfully connected worker!"
}

main() {
    while true; do
        read msg <&4
        eval "serverd_$msg"
        if [ ! $? ]; then
            echo "$MSG_BAD_MESSAGE" >&3
        fi
    done
}

trap serverd_stop SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

run_command "echo $port > .lock"
run_command "mkfifo $tcp_in_pipe"
run_command "mkfifo $tcp_out_pipe"
run_command "exec 3<>$tcp_in_pipe"
run_command "exec 4<>$tcp_out_pipe"
ncat -l -m 1 -k -p $port <&3 >&4 &
ncat_pid=$!

run_command git init --bare $name.git
info "Creating post-receive hook"
echo "#!/bin/bash
read oldrev newrev ref
echo \"Adding a build \$newrev to the queue...\"
echo \"build \${ref#refs/heads/}\" > /dev/tcp/localhost/$port
if [ \$? ]; then
    echo \"OK\"
fi
" > ${name}.git/hooks/post-receive
run_command chmod +x ${name}.git/hooks/post-receive

echo "$MSG_SUCCESS" >&3

set +e
main

