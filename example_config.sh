#!/bin/bash

name="test"

server="localhost"
server_path="/home/$USER/server"

workers=(
    "ut localhost /home/$USER/test1 $PWD/example_building_script.sh"
    "mt localhost /home/$USER/test2 $PWD/example_building_script.sh"
)

