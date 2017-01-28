#!/bin/bash

base_dir=$(readlink -f `dirname $0`)

source $base_dir/utils.sh

name=$1
build_number=0
pipe=/tmp/$name-serverd-$(date +%s)

interrupt() {
    info "Shutting down server..."
    run_command rm $workspace/.lock
    run_command rm $pipe
    exit 0
}

trigger() {
    local branch=$1
    old_pwd=$PWD
    log=$old_pwd/log
    # TODO
    cd $old_pwd
}

trap interrupt SIGINT SIGTERM SIGHUP

mkdir -p $name-workspace
cd $name-workspace
workspace=$PWD

if [ -e .lock ]; then
    die "Server exists!"
fi

echo $$ > .lock

run_command mknod $pipe p

run_command git init --bare $name.git
info "Creating post-receive hook"
echo "#!/bin/bash
read oldrev newrev ref
echo \"Adding a build \$newrev to the queue...\"
echo \"\${ref#refs/heads/}\" >> $pipe
if [ \$? == 0 ]; then
    echo \"OK\"
fi
" > ${name}.git/hooks/post-receive
run_command chmod +x ${name}.git/hooks/post-receive

set +e
while [[ true ]]; do
    read branchname < $pipe
    trigger $branchname
done

