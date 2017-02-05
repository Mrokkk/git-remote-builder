#!/bin/bash

base_dir=$(readlink -f `dirname $0`)
source $base_dir/utils.sh

name=$1
port=$2
build_number=0
tcp_in_pipe=/tmp/$(mktemp -u serverd.XXXX)
tcp_out_pipe=/tmp/$(mktemp -u serverd.XXXX)
workers=()
jobs=()
key=$(openssl rand -base64 32)
priv_key=$(openssl genrsa 2048 2>/dev/null) # FIXME: change key size

serverd_stop() {
    info "Shutting down server..."
    exec 3>&-
    exec 4>&-
    run_command rm -rf $tcp_in_pipe $tcp_out_pipe $workspace/.lock
    run_command kill $ncat_pid
    exit 0
}

read_job_log() {
    local worker=$1
    local port=$2
    local number=$3
    local log_name=${4//\//-}
    info "Reading build log from $worker:$port"
    sleep 1
    : > $log_name
    exec {build_socket}<>/dev/tcp/$worker/$port
    while read line <&$build_socket; do
        [[ "$line" == "$MSG_STOP_TRANSMISSION" ]] && break
        echo $line >> $log_name
    done
    exec {build_socket}>&-
    run_command "cp $log_name $log_name.$number"
}

serverd_build() {
    local branch=$1
    local log=$PWD/log
    for worker in ${workers[@]}; do
        info "Sending build #$build_number command to $worker"
        exec {workerd}<>/dev/tcp/$worker
        echo "build $build_number $branch" | openssl base64 -k $key >&$workerd
        sleep 0.5
        # FIXME: timeout value
        if ! read -t 60 response log_port <&$workerd; then
            error "Cannot read response from worker"
            continue
        fi
        exec {workerd}>&-
        local worker_hostname=$(dirname $worker)
        info "Got build log on $worker_hostname:$log_port"
        read_job_log $worker_hostname $log_port $build_number $worker &
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
    $MSG_START_TRANSMISSION $size" >/dev/tcp/$worker_address/$worker_port
    ncat $worker_address $worker_port <$building_script.gz.enc >&4
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

serverd_addjob() {
    local job_name=$1
    local job_script=$(readlink -f $2)
    info "Adding job $job_name with script $job_script"
    mkdir -p $name-workspace/jobs/$job_name
    cp $job_script $name-workspace/jobs/$job_name
    jobs+=("$job_name $job_script")
    echo "$MSG_SUCCESS" >&3
}

main() {
    while true; do
        msg=""
        read line <&4
        if [ "$line" != "$MSG_START_TRANSMISSION" ]; then
            echo "Fuck you!" >&3
            continue
        fi
        while read -t $TIMEOUT line <&4; do
            [[ "$line" == "$MSG_STOP_TRANSMISSION" ]] && break
            msg+="$line"
        done
        msg=$(echo "$msg" | base64 -d | openssl rsautl -decrypt -inkey <(echo "$priv_key"))
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

echo "$priv_key" | openssl rsa -pubout >.pub
chmod 600 .pub

run_command "echo $port >.lock"
run_command "mkfifo $tcp_in_pipe"
run_command "mkfifo $tcp_out_pipe"
run_command "exec 3<>$tcp_in_pipe"
run_command "exec 4<>$tcp_out_pipe"
ncat -l -m 1 -k -p $port <&3 >&4 &
ncat_pid=$!

run_command git init --bare $name.git

info "Creating post-receive hook"
cat > ${name}.git/hooks/post-receive <<EOF
#!/bin/bash
read oldrev newrev ref
echo "Adding a build \$newrev to the queue..."
exec {serverd}<>/dev/tcp/localhost/$port
echo "$MSG_START_TRANSMISSION" >&\$serverd
echo "build \${ref#refs/heads/}" | openssl rsautl -encrypt -pubin -inkey $workspace/.pub | base64 >&\$serverd
echo "$MSG_STOP_TRANSMISSION" >&\$serverd
if [ \$? ]; then
    echo "OK"
fi
exec {serverd}>&-
EOF
run_command chmod +x ${name}.git/hooks/post-receive

echo "$MSG_SUCCESS" >&3

set +e
main

