#!/bin/bash

# Test a trained Weka J48 decision tree on the given test set

eval $(atn-settings.py)

CLASS_ATTRIBUTE=$DEFAULT_CLASS_ATTRIBUTE

### END CONFIGURATION OPTIONS

if [ $# -lt 3 ]; then
    echo "Usage: ./atn-test-j48.sh <test-file> <output-file> <model-file>"
    exit 1
fi

TEST_FILE=$1
OUTPUT_FILE=$2
MODEL_FILE=$3

java -cp $WEKA_JAR_PATH \
    weka.classifiers.meta.FilteredClassifier \
        -T $TEST_FILE \
        -l $MODEL_FILE \
        > $OUTPUT_FILE
