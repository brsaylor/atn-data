#!/bin/bash

# This script automates the workflow starting with generating nodeconfigs and
# ending with a labelled feature file.

if [ $# -lt 2 ]; then
    echo "Usage: ./atn-generate-dataset.sh <set#> <timesteps>"
    echo "Assumes set# is a valid set# for nodeconfig_generator.py"
    exit 1
fi

LOGDIR=../WoB_Server_ATNEngine/src/log/atn

SET=$1
TIMESTEPS=$2

SETDIR=../data/set$SET
mkdir $SETDIR
NODECONFIG_FILE=$SETDIR/nodeconfigs.set$SET.txt

python nodeconfig_generator.py $SET > $NODECONFIG_FILE
bash ATNEngineBatchRunner.sh $TIMESTEPS $NODECONFIG_FILE
mkdir $SETDIR/biomass-data
mv $LOGDIR/*.csv $SETDIR/biomass-data/
echo "Compressing data..."
gzip $SETDIR/biomass-data/*.csv
echo "Creating feature file..."
python create_feature_file.py $SET features.set$SET.csv $SETDIR/biomass-data/*.csv.gz
echo "Assigning labels..."
python assign_labels.py features.set$SET.csv features.set$SET.labelled.csv
