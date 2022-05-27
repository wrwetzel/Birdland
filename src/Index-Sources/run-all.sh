#!/bin/bash

export PYTHONPATH=../../birdland
for x in *
do
    if [[ -d $x ]]
    then
    (
        echo $x
        cd $x
        do-*.py
    )
    fi
done
