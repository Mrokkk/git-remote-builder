#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
port=$2
build_number=0
tcp_in_pipe=/tmp/$name-worker-in-tcp-$(date +%s)
tcp_out_pipe=/tmp/$name-worker-out-tcp-$(date +%s)
workers=()

server_stop() {
    info "Shutting down server..."
    run_command rm -rf $tcp_in_pipe $tcp_out_pipe $workspace/.lock
    run_command kill $ncat_pid
    exit 0
}

server_build() {
    local branch=$1
    old_pwd=$PWD
    log=$old_pwd/log
    for worker in ${workers[@]}; do
        echo "build $branch" > /dev/tcp/$worker
    done
    cd $old_pwd
}

server_connect() {
    info "Connecting to $1:$2 and sending $3"
    local worker_address=$1
    local worker_port=$2
    local building_script=$3
    # FIXME
    echo "connect $workspace/$name.git
    START
    $(cat $building_script)
    STOP" > /dev/tcp/$worker_address/$worker_port
    if [ ! $? ]; then
        info "Cannot send data to worker!"
    fi
    workers+=("$worker_address/$worker_port")
}

main() {
    while true; do
        read msg <&4
        eval "server_$msg"
        if [ ! $? ]; then
            echo "$bad_message" >&3
        fi
    done
}

trap server_stop SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

echo $port > .lock

run_command mknod $tcp_in_pipe p
run_command mknod $tcp_out_pipe p

exec 3<>$tcp_in_pipe
exec 4<>$tcp_out_pipe
ncat -l -m 1 -k -p $port <&3 >&4 &
ncat_pid=$!

run_command git init --bare $name.git
info "Creating post-receive hook"
echo "#!/bin/bash
read oldrev newrev ref
echo \"Adding a build \$newrev to the queue...\"
echo \"build \${ref#refs/heads/}\" > /dev/tcp/localhost/$port
if [ \$? == 0 ]; then
    echo \"OK\"
fi
" > ${name}.git/hooks/post-receive
run_command chmod +x ${name}.git/hooks/post-receive

set +e
main

