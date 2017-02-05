#!/bin/bash

name="test"

server="localhost"
server_path="/home/$USER/server"

workers=(
    "localhost /home/$USER/test1 $PWD/examples/build.sh"
    "localhost /home/$USER/test2 $PWD/examples/ut.sh"
)

jobs=(
    "build $PWD/examples/build.sh"
    "ut $PWD/examples/ut.sh"
)

