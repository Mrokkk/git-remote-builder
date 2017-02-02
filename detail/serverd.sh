#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
port=$2
build_number=0
tcp_in_pipe=/tmp/$(mktemp -u serverd.XXXX)
tcp_out_pipe=/tmp/$(mktemp -u serverd.XXXX)
workers=()
key=$(openssl rand -base64 32)

serverd_stop() {
    info "Shutting down server..."
    exec &3>-
    exec &4>-
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
        exec &$worker_fd>-
        return
    fi
    run_command "rm -f $log_name"
    while read -t $TIMEOUT line <&${worker_fd}; do
        if [ "$line" == "$MSG_STOP_TRANSMISSION" ]; then
            break
        fi
        echo $line >> $log_name
    done
    exec &$worker_fd>-
    run_command "cp $log_name $log_name.$number"
}

serverd_build() {
    local branch=$1
    local log=$PWD/log
    for worker in ${workers[@]}; do
        info "Sending build #$build_number command to $worker"
        echo "build $build_number $branch" | openssl base64 -k $key >/dev/tcp/$worker
        if ! read -t $TIMEOUT response log_port </dev/tcp/$worker; then
            error "Cannot read response from worker"
            continue
        fi
        local worker_hostname=$(dirname $worker)
        info "Got build log on $worker:$log_port"
        # read_build_log $worker $build_number $log_port &
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
        hostname="ssh://$HOSTNAME:"
    fi
    run_command "gzip -k $building_script"
    openssl base64 -k $key -in $building_script.gz -out $building_script.gz.enc
    local size=$(wc -c $building_script.gz.enc | awk '{print $1}')
    echo "connect $key $hostname$workspace/$name.git
    $MSG_START_TRANSMISSION $size" > /dev/tcp/$worker_address/$worker_port
    ncat $worker_address $worker_port < $building_script.gz.enc >&4
    if [ ! $? ]; then
        error "Cannot send data to worker!"
    fi
    rm -f $building_script.gz*
    read -t $TIMEOUT status </dev/tcp/$worker_address/$worker_port
    if [ "$status" != "$MSG_SUCCESS" ]; then
        error "Connecting to worker failed - no response!"
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
cat > ${name}.git/hooks/post-receive << EOF
#!/bin/bash
read oldrev newrev ref
echo "Adding a build \$newrev to the queue..."
echo "build \${ref#refs/heads/}" > /dev/tcp/localhost/$port
if [ \$? ]; then
    echo "OK"
fi
EOF
run_command chmod +x ${name}.git/hooks/post-receive

echo "$MSG_SUCCESS" >&3

set +e
main

