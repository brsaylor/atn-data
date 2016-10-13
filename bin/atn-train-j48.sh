#!/bin/bash

# Trains Weka's J48 decision tree on the given feature file.

eval $(atn-settings.py)

CLASS_ATTRIBUTE=$DEFAULT_CLASS_ATTRIBUTE

### END CONFIGURATION OPTIONS

if [ $# -lt 3 ]; then
    echo "Usage: ./atn-train-j48.sh <training-file> <output-file> <model-file>"
    exit 1
fi

TRAINING_FILE=$1
OUTPUT_FILE=$2
MODEL_FILE=$3

# Find the index of the class attribute
# (Weka requires the index; can't just give the name)
ATTRIBUTES=`head -n 1 $TRAINING_FILE | sed -e 's/,/ /g'`
CLASS_INDEX=1
CLASS_ATTRIBUTE_FOUND=false
for ATTRIBUTE in $ATTRIBUTES; do
    if [ $ATTRIBUTE == $CLASS_ATTRIBUTE ]; then
        CLASS_ATTRIBUTE_FOUND=true
        break
    fi
    CLASS_INDEX=$((CLASS_INDEX + 1))
done
if [ $CLASS_ATTRIBUTE_FOUND == false ]; then
    echo "Error: Could not find class attribute $CLASS_ATTRIBUTE"
    exit 1
fi

java -cp $WEKA_JAR_PATH \
    weka.classifiers.meta.FilteredClassifier \
        -F "weka.filters.unsupervised.attribute.RemoveByName -E ^(X|K|$CLASS_ATTRIBUTE).*$ -V" \
        -W weka.classifiers.trees.J48 -c $CLASS_INDEX \
        -t $TRAINING_FILE \
        -d $MODEL_FILE \
        > $OUTPUT_FILE
