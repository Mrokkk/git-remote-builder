#!/bin/bash

name="test"

server="localhost"
server_path="/home/$USER/server"

workers=(
    "localhost /home/$USER/test1 $PWD/example_building_script.sh"
    "localhost /home/$USER/test2 $PWD/example_building_script.sh"
)

jobs=(
    "build $PWD/examples/build.sh"
    "ut $PWD/examples/ut.sh"
)

