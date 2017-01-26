#!/bin/bash

star="\e[1;35m*\e[0m"

info() {
    echo -e "$star $@"
}

die() {
    echo -e "$star $@"
    exit 1
}

create_repo() {
    local repo_name=$1
    local pipe_name=$2
    run_command git init --bare $repo_name.git
    echo "#!/bin/bash
    read oldrev newrev ref
    echo \"Triggering a server...\"
    echo \"\${ref#refs/heads/}\" >> $pipe_name
    if [ \$? == 0 ]; then
        echo \"Build triggered.\"
    fi
    " > ${repo_name}.git/hooks/post-receive
    run_command chmod +x ${repo_name}.git/hooks/post-receive
}

get_daemon_pid() {
    local name_=$1
    local workspace_=$(readlink -f $2)
    if [ -e $workspace_/$name_-workspace ]; then
        cat $workspace_/$name_-workspace/.lock 2>/dev/null
    fi
}

run_command() {
    local com=$@
    local log=/tmp/log-$(date +%s)
    info "Running: \"$com\""
    $com &>$log
    if [ $? -ne 0 ]; then
        cat $log
        info "Command \"$com\" FAILED"
    fi
    rm $log
}

