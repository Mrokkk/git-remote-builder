#!/bin/bash

source utils.sh

name=$1
building_script=$2
sleep_pid=
build_number=0

interrupt() {
    info "Shutting down server..."
    kill $sleep_pid > /dev/null
    rm .lock
}

trigger() {
    kill -9 $sleep_pid
    branch=$(cat branchname)
    echo
    info "$name/$branch build #$build_number @ `LANG=C date`"
    info "Output is written also to file: $PWD/log.$build_number"
    old_pwd=$PWD
    set -e
    if [ ! -e $name ]; then
        git clone $name.git $name
    fi
    cd $name
    git fetch origin $branch 2> /dev/null
    git checkout origin/$branch 2> /dev/null
    git submodule update --init --recursive 2> /dev/null
    set +e
    unbuffer $building_script 2>&1 | tee $old_pwd/log.$build_number
    if [ "$PIPESTATUS" == "0" ]; then
        info "Build #$build_number \e[1;32mPASSED\e[0m"
    else
        info "Build #$build_number \e[1;31mFAILED\e[0m"
    fi
    cd $old_pwd
    build_number=$((build_number+1))
}

trap interrupt SIGINT SIGTERM SIGHUP
trap trigger SIGUSR1

mkdir -p $name-workspace
cd $name-workspace

if [ -e .lock ]; then
    die "Server already running!"
fi

touch .lock

git init --bare ${name}.git

echo "#!/bin/bash
read oldrev newrev ref
echo \"Triggering a server...\"
echo \"\${ref#refs/heads/}\" > ../branchname
kill -10 $$
if [ \$? == 0 ]; then
    echo \"Build triggered.\"
fi
" > ${name}.git/hooks/post-receive
chmod +x ${name}.git/hooks/post-receive

info "Created post-receive hook"

info "To use it: git remote add remote ssh://$USER@$HOSTNAME:$PWD/$name.git"

while [[ true ]]; do
    sleep infinity &
    sleep_pid=$!
    wait $sleep_pid
done

