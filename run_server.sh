#!/bin/bash

set -e

interrupt() {
    echo "Shutting down server..."
    kill $pid > /dev/null
    rm .lock
}

trap interrupt SIGINT SIGHUP SIGKILL

name=$1
branch=$2
building_script=$(readlink -f $3)

mkdir -p workspace
cd workspace

if [ -e .lock ]; then
    echo "Server already running!" && exit 1
fi

touch .lock

../runner.sh $name $branch $building_script &
pid=$!
git init --bare ${name}.git
echo "#!/bin/bash
echo \"Triggering a server...\"
kill -10 $pid
if [ \$? == 0 ]; then
    echo \"Build triggered.\"
fi
" > ${name}.git/hooks/post-receive
chmod +x ${name}.git/hooks/post-receive

wait $pid

