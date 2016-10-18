#!/bin/bash

eval $(atn-settings.py)

# Args: <timesteps> <node config input file>

# Uncomment to enable assertions
#JVM_ARGS="-enableassertions"

# Get absolute path to node config file
WORKING_DIR=`pwd`
cd `dirname $2`
NODECONFIG_FILE=`pwd`/`basename $2`
cd $WORKING_DIR

cd $WOB_SERVER_HOME
java $JVM_ARGS \
    -cp 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*' \
    atn.ATNEngineBatchRunner $1 $NODECONFIG_FILE $3
