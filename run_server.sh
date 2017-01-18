#!/bin/bash

set -e

name=$1
building_script=$(readlink -f $2)

./runner.sh $name $building_script &
echo "Started runner with PID $!"

