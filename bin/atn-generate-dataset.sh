#!/bin/bash

# This script automates the workflow starting with generating nodeconfigs and
# ending with a labeled feature file.

eval $(atn-settings.py)

if [ $# -lt 2 ]; then
    echo "Usage: ./atn-generate-dataset.sh <set#> <timesteps>"
    echo "Assumes set# is a valid set# for nodeconfig_generator.py"
    exit 1
fi

LOGDIR=$WOB_SERVER_HOME/src/log/atn

# Clear the log directory
rm $LOGDIR/*

SET=$1
TIMESTEPS=$2

SETDIR=$DATA_HOME/set$SET
mkdir $SETDIR
NODECONFIG_FILE=$SETDIR/nodeconfigs.set$SET.txt

atn-generate-node-configs.py $SET > $NODECONFIG_FILE
atn-engine-batch-runner.sh $TIMESTEPS $NODECONFIG_FILE
mkdir $SETDIR/biomass-data
mv $LOGDIR/*.csv $SETDIR/biomass-data/
echo "Compressing data..."
gzip $SETDIR/biomass-data/*.csv
echo "Creating feature file..."
atn-generate-summary-file.py $SET features.set$SET.csv $SETDIR/biomass-data/*.csv.gz
echo "Assigning labels..."
atn-assign-labels.py features.set$SET.csv features.set$SET.labeled.csv
