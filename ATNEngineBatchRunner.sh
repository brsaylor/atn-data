#!/bin/bash

# Args: <timesteps> <node config input file>

# Uncomment to enable assertions
#JVM_ARGS="-enableassertions"

cd ../WoB_Server_ATNEngine
java $JVM_ARGS \
    -cp 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*' \
    atn.ATNEngineBatchRunner $1 ../atn-data/$2 $3
