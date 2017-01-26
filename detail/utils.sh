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
    git init --bare $repo_name.git > /dev/null
    echo "#!/bin/bash
    read oldrev newrev ref
    echo \"Triggering a server...\"
    echo \"\${ref#refs/heads/}\" > ../branchname
    echo \"\$repo_name\" >> $pipe_name
    if [ \$? == 0 ]; then
        echo \"Build triggered.\"
    fi
    " > ${repo_name}.git/hooks/post-receive
    chmod +x ${repo_name}.git/hooks/post-receive
}

get_daemon_pid() {
    local name_=$1
    local workspace_=$(readlink -f $2)
    if [ -e $workspace_/$name_-workspace ]; then
        cat $workspace_/$name_-workspace/.lock 2>/dev/null
    fi
}

