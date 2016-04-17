#!/bin/bash

# Args: <timesteps> <node config input file>

cd ../WoB_Server_ATNEngine
java -cp 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*' atn.ATNEngineBatchRunner $1 ../atn-data/$2 $3
