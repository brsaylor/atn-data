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

# Find the index of the class attribute
# (Weka requires the index; can't just give the name)
ATTRIBUTES=`head -n 1 $TEST_FILE | sed -e 's/,/ /g'`
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
        -T $TEST_FILE \
        -l $MODEL_FILE \
        > $OUTPUT_FILE
